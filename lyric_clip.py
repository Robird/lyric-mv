"""
LyricClip - 歌词视频片段容器

使用单一VideoClip容器管理所有歌词时间轴，
通过frame_function统一渲染，避免多ImageClip合成开销
"""

import numpy as np
from typing import List, Tuple, Optional
from moviepy import VideoClip
from PIL import Image, ImageDraw

from lyric_timeline import LyricTimeline
from layout_engine import LayoutEngine
from layout_types import LyricRect
from lyric_content import LyricContent, LyricContentFactory, RenderContext
from font_cache import FontCache, TextMetricsCache, detect_text_language


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
                 fps: float = 30):
        """初始化LyricClip
        
        Args:
            timelines: 歌词时间轴列表
            layout_engine: 布局引擎
            size: 视频尺寸 (width, height)
            duration: 视频时长
            fps: 帧率
        """
        self.timelines = timelines
        self.layout_engine = layout_engine
        self.video_size = size
        self.fps = fps
        
        # 预计算布局
        self.layout_result = layout_engine.calculate_layout(size[0], size[1])
        
        # 创建时间轴到布局位置的映射
        self._timeline_positions = {}
        for timeline in timelines:
            if timeline.element_id in self.layout_result.element_positions:
                self._timeline_positions[timeline.element_id] = self.layout_result.element_positions[timeline.element_id]
        
        # 初始化VideoClip，使用frame_function
        super().__init__(
            frame_function=self._render_frame,
            duration=duration,
            has_constant_size=True
        )
        self.size = size
        self.fps = fps
    
    def _render_frame(self, t: float) -> np.ndarray:
        """核心渲染方法：在时间t渲染完整的歌词帧
        
        Args:
            t: 当前时间
            
        Returns:
            渲染的帧数据 (height, width, 3)
        """
        # 创建空白画布 (透明背景)
        frame = np.zeros((self.video_size[1], self.video_size[0], 4), dtype=np.uint8)
        
        # 创建渲染上下文
        context = RenderContext(
            current_time=t,
            video_size=self.video_size,
            fps=self.fps,
            frame_number=int(t * self.fps)
        )
        
        # 遍历所有时间轴，渲染当前时间的歌词
        for timeline in self.timelines:
            self._render_timeline_at_time(frame, timeline, t, context)
        
        # 转换为RGB格式（MoviePy期望的格式）
        rgb_frame = frame[:, :, :3]  # 去掉alpha通道
        return rgb_frame
    
    def _render_timeline_at_time(self, frame: np.ndarray, 
                               timeline: LyricTimeline, 
                               t: float, 
                               context: RenderContext):
        """渲染指定时间轴在当前时间的内容
        
        Args:
            frame: 目标帧数组
            timeline: 歌词时间轴
            t: 当前时间
            context: 渲染上下文
        """
        # 获取时间轴的布局位置
        if timeline.element_id not in self._timeline_positions:
            return
        
        layout_rect = self._timeline_positions[timeline.element_id]
        
        # 创建歌词内容
        content = LyricContentFactory.create_from_timeline(timeline, t, layout_rect)
        if not content:
            return
        
        # 渲染歌词内容到帧上
        self._render_lyric_on_frame(frame, content, context)
    
    def _render_lyric_on_frame(self, frame: np.ndarray, 
                             content: LyricContent, 
                             context: RenderContext):
        """直接在帧上渲染歌词文本
        
        Args:
            frame: 目标帧数组
            content: 歌词内容
            context: 渲染上下文
        """
        # 检测文本语言
        language = detect_text_language(content.text)
        
        # 获取字体
        font = FontCache.get_font(
            font_path=None,  # 使用默认字体
            size=content.style.font_size,
            language=language
        )
        
        # 创建PIL图像用于文本渲染
        # 注意：这里仍然使用PIL，但只创建必要的临时图像
        text_img = self._create_text_image(content, font, language)
        if text_img is None:
            return
        
        # 将文本图像合成到主帧上
        self._composite_text_image(frame, text_img, content)
    
    def _create_text_image(self, content: LyricContent, 
                          font, language: str) -> Optional[np.ndarray]:
        """创建文本图像
        
        Args:
            content: 歌词内容
            font: 字体对象
            language: 语言类型
            
        Returns:
            文本图像数组或None
        """
        # 获取文本尺寸
        text_size = TextMetricsCache.get_text_size(
            content.text, None, content.style.font_size, language
        )
        
        if text_size[0] <= 0 or text_size[1] <= 0:
            return None
        
        # 创建文本图像
        img = Image.new('RGBA', text_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 渲染文本
        self._draw_text_with_effects(draw, content, font, text_size)
        
        # 转换为numpy数组
        return np.array(img)
    
    def _draw_text_with_effects(self, draw: ImageDraw.Draw, 
                              content: LyricContent, 
                              font, text_size: Tuple[int, int]):
        """绘制带效果的文本
        
        Args:
            draw: PIL绘制对象
            content: 歌词内容
            font: 字体对象
            text_size: 文本尺寸
        """
        lines = content.text.split('\n')
        y_offset = 0
        line_height = content.style.font_size + int(content.style.font_size * 0.2)
        
        for line in lines:
            if not line.strip():
                y_offset += line_height
                continue
            
            # 计算行的水平居中位置
            line_bbox = font.getbbox(line)
            line_width = line_bbox[2] - line_bbox[0]
            x_pos = (text_size[0] - line_width) // 2
            
            # 应用动画效果（透明度）
            alpha = int(255 * content.animation_progress)
            
            # 绘制阴影
            shadow_color = (0, 0, 0, min(200, alpha))
            draw.text((x_pos + 2, y_offset + 2), line, fill=shadow_color, font=font)
            
            # 绘制主文本
            if content.is_highlighted:
                # 高亮颜色（金色）
                main_color = (255, 215, 0, alpha)
            else:
                # 普通颜色（白色）
                main_color = (255, 255, 255, alpha)
            
            draw.text((x_pos, y_offset), line, fill=main_color, font=font)
            
            y_offset += line_height
    
    def _composite_text_image(self, frame: np.ndarray, 
                            text_img: np.ndarray, 
                            content: LyricContent):
        """将文本图像合成到主帧上
        
        Args:
            frame: 目标帧数组
            text_img: 文本图像数组
            content: 歌词内容
        """
        # 计算文本在帧中的位置
        text_height, text_width = text_img.shape[:2]
        
        # 使用布局位置
        x = content.position.x + (content.position.width - text_width) // 2
        y = content.position.y + (content.position.height - text_height) // 2
        
        # 确保位置在帧范围内
        x = max(0, min(x, frame.shape[1] - text_width))
        y = max(0, min(y, frame.shape[0] - text_height))
        
        # 执行alpha合成
        if text_img.shape[2] == 4:  # RGBA
            self._alpha_composite(frame, text_img, x, y)
        else:  # RGB
            frame[y:y+text_height, x:x+text_width, :3] = text_img
    
    def _alpha_composite(self, background: np.ndarray, 
                        foreground: np.ndarray, 
                        x: int, y: int):
        """执行alpha合成
        
        Args:
            background: 背景图像
            foreground: 前景图像（带alpha通道）
            x, y: 前景图像在背景中的位置
        """
        fg_height, fg_width = foreground.shape[:2]
        
        # 确保不超出边界
        end_y = min(y + fg_height, background.shape[0])
        end_x = min(x + fg_width, background.shape[1])
        actual_height = end_y - y
        actual_width = end_x - x
        
        if actual_height <= 0 or actual_width <= 0:
            return
        
        # 获取区域
        bg_region = background[y:end_y, x:end_x]
        fg_region = foreground[:actual_height, :actual_width]
        
        # 提取alpha通道
        alpha = fg_region[:, :, 3:4].astype(np.float32) / 255.0
        
        # 执行合成
        bg_region[:, :, :3] = (
            bg_region[:, :, :3].astype(np.float32) * (1 - alpha) +
            fg_region[:, :, :3].astype(np.float32) * alpha
        ).astype(np.uint8)


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
