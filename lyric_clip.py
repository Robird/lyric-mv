"""
LyricClip - 歌词视频片段容器

使用单一VideoClip容器管理所有歌词时间轴，
通过frame_function统一渲染，避免多ImageClip合成开销
"""

import numpy as np
from typing import List, Tuple, Optional
from moviepy import VideoClip

from lyric_timeline import LyricTimeline
from layout_engine import LayoutEngine
from lyric_content import RenderContext

# 预计算和缓存文字图片。在此基础上，使用帧缓冲区和opencv的alpha blending来实现歌词的渲染和合成。
class LyricClip(VideoClip):
    """歌词视频片段容器

    替代当前为每句歌词创建ImageClip的模式，
    使用单一VideoClip容器管理所有歌词时间轴
    """

    def __init__(self,
                 timelines: List[LyricTimeline],
                 layout_engine: LayoutEngine,
                 size: Tuple[int, int],
                 duration: float,
                 fps: float = 24,
                 background: Optional[np.ndarray] = None):
        """初始化LyricClip

        Args:
            timelines: 歌词时间轴列表
            layout_engine: 布局引擎
            size: 视频尺寸 (width, height)
            duration: 视频时长
            fps: 帧率
            background: 背景图片数组 (height, width, 3) - RGB格式。
                       注意：未来可升级为BackgroundTimeline，支持时间控制的图片序列和平滑过渡。
        """
        self.timelines = timelines
        self.layout_engine = layout_engine
        self.video_size = size
        self.fps = fps

        # 处理背景图片：检查尺寸并进行缩放和居中对齐
        self.background = self._prepare_background(background, size)

        # 预计算布局
        self.layout_result = layout_engine.calculate_layout(size[0], size[1])

        # 创建时间轴到布局位置的映射
        self._timeline_positions = {}
        for timeline in timelines:
            if timeline.element_id in self.layout_result.element_positions:
                self._timeline_positions[timeline.element_id] = self.layout_result.element_positions[timeline.element_id]

        # 初始化帧缓冲区（必须在super().__init__之前，因为MoviePy会立即调用get_frame(0)）
        self.frame_buffer = np.ndarray((self.video_size[1], self.video_size[0], 3), dtype=np.uint8)
        # self.frame_buffer_view = self.frame_buffer[:, :, :3] # 目前分析发现帧缓冲并不需要alpha通道
        self.frame_buffer_view = self.frame_buffer

        # 初始化VideoClip，使用frame_function
        super().__init__(
            frame_function=self._render_frame,
            duration=duration,
            has_constant_size=True
        )
        self.size = size
        self.fps = fps

    def _prepare_background(self, background: Optional[np.ndarray],
                          target_size: Tuple[int, int]) -> Optional[np.ndarray]:
        """准备背景图片：检查尺寸并进行缩放和居中对齐

        Args:
            background: 原始背景图片数组 (height, width, 3) - RGB格式
            target_size: 目标尺寸 (width, height)

        Returns:
            处理后的背景图片数组或None
        """
        if background is None:
            return None

        target_width, target_height = target_size
        bg_height, bg_width = background.shape[:2]

        # 如果尺寸已经匹配，直接返回
        if bg_width == target_width and bg_height == target_height:
            return background.copy()

        # 需要缩放和居中对齐
        print(f"   背景图片尺寸调整: {bg_width}x{bg_height} -> {target_width}x{target_height}")

        # 使用OpenCV进行高质量缩放（优化版本）
        import cv2

        # 计算缩放比例，保持宽高比
        scale_w = target_width / bg_width
        scale_h = target_height / bg_height
        scale = min(scale_w, scale_h)  # 使用较小的缩放比例以确保图片完全适应

        # 计算缩放后的尺寸
        new_width = int(bg_width * scale)
        new_height = int(bg_height * scale)

        # 使用OpenCV进行高质量缩放
        try:
            # 使用INTER_LANCZOS4插值方式进行高质量缩放
            resized_bg = cv2.resize(background, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        except AttributeError:
            # 如果INTER_LANCZOS4不可用，回退到INTER_CUBIC
            resized_bg = cv2.resize(background, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # 创建目标尺寸的黑色背景
        result = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # 计算居中位置
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2

        # 将缩放后的图片放置到居中位置
        result[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized_bg

        return result

    def _render_frame(self, t: float) -> np.ndarray:
        """核心渲染方法：在时间t渲染完整的歌词帧

        Args:
            t: 当前时间

        Returns:
            渲染的帧数据 (height, width, 3) - RGB格式
        """
        # 擦除画布
        if self.background is not None:
            # 注意：未来可升级为BackgroundTimeline支持背景序列间的平滑过渡
            self.frame_buffer[:, :] = self.background
        else:
            self.frame_buffer.fill(0)

        # 创建渲染上下文
        context = RenderContext(
            current_time=t,
            video_size=self.video_size,
            fps=self.fps,
            frame_number=int(t * self.fps)
        )

        # 遍历所有时间轴，渲染当前时间的歌词
        for timeline in self.timelines:
            timeline.render(self.frame_buffer, context)

        return self.frame_buffer_view



def create_lyric_clip(timelines: List[LyricTimeline],
                     layout_engine: LayoutEngine,
                     size: Tuple[int, int],
                     duration: float,
                     fps: float = 30) -> LyricClip:
    """创建LyricClip的工厂函数

    Args:
        timelines: 歌词时间轴列表
        layout_engine: 布局引擎
        size: 视频尺寸
        duration: 视频时长
        fps: 帧率

    Returns:
        LyricClip实例
    """
    return LyricClip(timelines, layout_engine, size, duration, fps)
