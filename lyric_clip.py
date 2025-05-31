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
# LyricRect导入已移除 - 布局信息现在通过LyricContent传递
from lyric_content import LyricContent, LyricContentFactory, RenderContext
from font_cache import FontCache, detect_text_language

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
            background: 背景图片数组 (height, width, 3) - RGB格式。 TODO:AI 稍后会升级到类似.lrc文件那样的BackgroundTimeline,内部是时间控制的图片序列，在加载时就预计算好尺寸和缩放。
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

        # TODO:AI 优化这部分的缩放逻辑，使用OpenCV的cv2.resize()函数，指定INTER_LANCZOS4插值方式。
        # 使用PIL进行高质量缩放
        from PIL import Image
        bg_image = Image.fromarray(background)

        # 计算缩放比例，保持宽高比
        scale_w = target_width / bg_width
        scale_h = target_height / bg_height
        scale = min(scale_w, scale_h)  # 使用较小的缩放比例以确保图片完全适应

        # 计算缩放后的尺寸
        new_width = int(bg_width * scale)
        new_height = int(bg_height * scale)

        # 缩放图片
        try:
            bg_image = bg_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            # 较旧的PIL版本回退
            bg_image = bg_image.resize((new_width, new_height))

        # 创建目标尺寸的黑色背景
        result = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # 计算居中位置
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2

        # 将缩放后的图片放置到居中位置
        bg_array = np.array(bg_image)
        result[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = bg_array

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
            # TODO:AI 当background升级到BackgroundTimeline时，这里需要改为使用background.reset_frame(self.frame_buffer,t)，在reset_frame内部使用opencv的alpha blending来实现背景序列间的平滑过渡。
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
            # self._render_timeline_at_time(self.frame_buffer, timeline, t, context)

        return self.frame_buffer_view

    # TODO:AI 此函数已被timeline.render替代，可以剥洋葱一样的逐步删除无任何引用的相关实现。
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
        # 计算实际可用的文本宽度（考虑布局区域限制）
        max_text_width = content.position.width

        # 计算文本的实际尺寸，考虑宽度限制
        text_size = self._calculate_constrained_text_size(
            content.text, font, max_text_width
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

    def _calculate_constrained_text_size(self, text: str, font, max_width: int) -> Tuple[int, int]:
        """计算受宽度限制的文本尺寸

        Args:
            text: 文本内容
            font: 字体对象
            max_width: 最大宽度限制

        Returns:
            文本尺寸 (width, height)
        """
        lines = text.split('\n')
        total_width = 0
        total_height = 0
        line_height = int(font.size * 1.2)  # 行高为字体大小的1.2倍

        for line in lines:
            if line.strip():  # 跳过空行
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                # 如果单行超过最大宽度，需要进行换行处理
                if line_width > max_width:
                    # 简单的字符级换行（可以后续优化为词级换行）
                    wrapped_lines = self._wrap_text_to_width(line, font, max_width)
                    for wrapped_line in wrapped_lines:
                        bbox = font.getbbox(wrapped_line)
                        wrapped_width = bbox[2] - bbox[0]
                        total_width = max(total_width, wrapped_width)
                        total_height += line_height
                else:
                    total_width = max(total_width, line_width)
                    total_height += line_height
            else:
                total_height += line_height

        # 确保不超过最大宽度
        total_width = min(total_width, max_width)

        return (total_width, total_height)

    def _wrap_text_to_width(self, text: str, font, max_width: int) -> List[str]:
        """将文本按宽度换行

        Args:
            text: 文本内容
            font: 字体对象
            max_width: 最大宽度

        Returns:
            换行后的文本列表
        """
        if not text.strip():
            return [text]

        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines

    def _draw_text_with_effects(self, draw, content: LyricContent,
                              font, text_size: Tuple[int, int]):
        """绘制带效果的文本

        Args:
            draw: PIL绘制对象
            content: 歌词内容
            font: 字体对象
            text_size: 文本尺寸
        """
        # 处理文本换行
        max_width = content.position.width
        processed_lines = []

        for line in content.text.split('\n'):
            if not line.strip():
                processed_lines.append('')
                continue

            # 检查是否需要换行
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]

            if line_width > max_width:
                # 需要换行
                wrapped_lines = self._wrap_text_to_width(line, font, max_width)
                processed_lines.extend(wrapped_lines)
            else:
                processed_lines.append(line)

        # 绘制处理后的文本行
        y_offset = 0
        line_height = int(font.size * 1.2)

        for line in processed_lines:
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
