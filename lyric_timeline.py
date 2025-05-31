"""
LyricTimeline核心类型实现
包含完整的类定义、策略模式实现和使用示例

这个模块实现了歌词时间轴的面向对象设计，支持：
- 多种显示策略（简单淡入淡出、增强预览、双语同步）
- 自报告尺寸机制
- 策略模式的可扩展设计
- 向后兼容的接口
- Layout布局器支持
"""

import re
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
# ImageClip导入已移除 - 新的LyricClip架构不再需要创建ImageClip

# 导入布局相关的数据类型
from layout_types import LyricRect, LyricStyle
from layout_engine import LayoutElement
from lyric_content import RenderContext
from font_cache import FontCache, detect_text_language

# ============================================================================
# 基础数据结构和常量
# ============================================================================

# 动画配置常量
ANIMATION_VERTICAL_OFFSET = 30  # 纵向动画偏移量（像素）
ANIMATION_LAYOUT_PADDING = ANIMATION_VERTICAL_OFFSET   # 布局时预留的动画空间（像素）

class LyricDisplayMode(Enum):
    """歌词显示模式枚举"""
    SIMPLE_FADE = "simple_fade"           # 简单淡入淡出
    ENHANCED_PREVIEW = "enhanced_preview"  # 增强模式：当前+预览
    KARAOKE_STYLE = "karaoke_style"       # 卡拉OK样式（未来扩展）

# LyricRect和LyricStyle现在从layout_types模块导入

# ============================================================================
# Layout布局器接口导入 - 已移动到文件顶部
# ============================================================================

# ============================================================================
# 策略模式实现
# ============================================================================

class LyricDisplayStrategy(ABC):
    """歌词显示策略抽象基类

    定义了所有显示策略必须实现的接口
    """

    @abstractmethod
    def calculate_required_rect(self, timeline: 'LyricTimeline',
                              video_width: int, video_height: int) -> LyricRect:
        """计算所需的显示区域"""
        pass

    # generate_clips方法已移除
    # 新的LyricClip架构不再需要策略类生成ImageClip
    # 所有渲染现在通过LyricClip的统一frame_function处理

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            "strategy_type": self.__class__.__name__,
            "parameters": self.__dict__.copy()
        }

class SimpleFadeStrategy(LyricDisplayStrategy):
    """简单淡入淡出显示策略

    用于单行歌词的简单显示，支持淡入淡出效果
    """

    def __init__(self, y_position: Optional[int] = None, is_highlighted: bool = True):
        self.y_position = y_position
        self.is_highlighted = is_highlighted

    def calculate_required_rect(self, timeline: 'LyricTimeline',
                              video_width: int, video_height: int) -> LyricRect:
        """计算简单显示所需区域，支持多行文本"""
        y_pos = self.y_position or (video_height // 2)
        font_size = timeline.style.font_size

        # 使用预计算的最大行数，避免重复计算
        max_lines = timeline._max_lines

        # 估算文字高度（字体大小 * 1.2 作为行高）
        line_height = int(font_size * 1.2)
        total_height = max_lines * line_height

        # 为动画预留额外空间（上下各预留ANIMATION_LAYOUT_PADDING像素）
        total_height_with_animation = total_height + 2 * ANIMATION_LAYOUT_PADDING

        return LyricRect(
            x=0,
            y=y_pos - total_height_with_animation // 2,
            width=video_width,
            height=total_height_with_animation
        )

    # generate_clips方法已移除
    # SimpleFadeStrategy现在只负责计算布局区域
    # 实际渲染由LyricClip的统一frame_function处理

class EnhancedPreviewStrategy(LyricDisplayStrategy):
    """增强预览模式：当前歌词+下一句预览

    这个策略封装了现有的增强模式逻辑：
    - 当前歌词高亮显示
    - 下一句歌词预览（非高亮）
    - 可配置两行的垂直偏移
    """

    def __init__(self, current_y_offset: int = -50, preview_y_offset: int = 80):
        self.current_y_offset = current_y_offset
        self.preview_y_offset = preview_y_offset

    def calculate_required_rect(self, timeline: 'LyricTimeline',
                              video_width: int, video_height: int) -> LyricRect:
        """计算增强预览所需区域，支持多行文本"""
        font_size = timeline.style.font_size
        line_height = int(font_size * 1.2)

        # 使用预计算的最大行数，避免重复计算
        max_lines = timeline._max_lines

        # 单个歌词块的高度
        single_lyric_height = max_lines * line_height

        # 需要容纳当前歌词和预览歌词，考虑偏移量
        total_height = abs(self.current_y_offset) + abs(self.preview_y_offset) + single_lyric_height * 2
        
        # 为动画预留额外空间（上下各预留ANIMATION_LAYOUT_PADDING像素）
        total_height_with_animation = total_height + 2 * ANIMATION_LAYOUT_PADDING
        
        center_y = video_height // 2

        return LyricRect(
            x=0,
            y=center_y - total_height_with_animation // 2,
            width=video_width,
            height=total_height_with_animation
        )

    # generate_clips方法已移除
    # EnhancedPreviewStrategy现在只负责计算布局区域
    # 增强预览逻辑将在LyricClip中实现



# ============================================================================
# 主要的LyricTimeline类
# ============================================================================

class LyricTimeline(LayoutElement):
    """歌词时间轴类 - 封装歌词数据和显示逻辑

    这是核心类，封装了歌词数据和显示策略，提供统一的接口
    现在实现了LayoutElement接口，可以参与布局引擎的自动布局
    """

    def __init__(self, lyrics_data: List[Tuple[float, str]],
                 language: str = "unknown",
                 style: Optional[LyricStyle] = None,
                 display_mode: LyricDisplayMode = LyricDisplayMode.SIMPLE_FADE,
                 element_id: Optional[str] = None,
                 priority: int = 10,
                 is_flexible: bool = True):
        """初始化歌词时间轴

        Args:
            lyrics_data: 歌词数据列表 [(时间戳, 歌词文本), ...]
            language: 语言标识
            style: 样式配置
            display_mode: 显示模式
            element_id: 元素唯一标识（用于布局引擎）
            priority: 布局优先级（数字越小优先级越高）
            is_flexible: 是否可调整位置（用于自动布局）
        """
        self.lyrics_data = sorted(lyrics_data, key=lambda x: x[0])  # 按时间排序
        self.language = language
        self.style = style or LyricStyle()
        self.display_mode = display_mode
        self._strategy: Optional[LyricDisplayStrategy] = None

        # LayoutElement接口属性
        self._element_id = element_id or f"lyric_timeline_{language}_{id(self)}"
        self._priority = priority
        self._is_flexible = is_flexible

        # 预处理多行文本信息，统一处理，避免策略类重复实现
        self._processed_lyrics = self._preprocess_lyrics()
        self._max_lines = self._calculate_max_lines()

        # 文字图片缓存系统（OpenCV优化）
        self._text_cache = {}  # 缓存预渲染的文字图片
        self._cache_initialized = False

        self._setup_strategy()

    def _preprocess_lyrics(self) -> List[Tuple[float, List[str]]]:
        """预处理歌词数据，将文本转换为清理后的字符串数组

        这是关键的职责分离：
        - 在这里统一处理多行文本的分割和清理
        - 策略类只需要关注显示逻辑，不需要重复实现文本处理

        Returns:
            List[Tuple[float, List[str]]]: [(时间戳, [清理后的行列表]), ...]
        """
        processed = []
        for timestamp, text in self.lyrics_data:
            # 分割并清理空行，统一在这里处理
            lines = text.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            if cleaned_lines:  # 只保留有内容的歌词
                processed.append((timestamp, cleaned_lines))
        return processed

    def _calculate_max_lines(self) -> int:
        """预计算所有歌词中的最大行数，基于预处理后的数据"""
        max_lines = 1
        for _, lines in self._processed_lyrics:
            max_lines = max(max_lines, len(lines))
        return max_lines

    def _setup_strategy(self):
        """根据显示模式设置策略"""
        if self.display_mode == LyricDisplayMode.SIMPLE_FADE:
            self._strategy = SimpleFadeStrategy()
        elif self.display_mode == LyricDisplayMode.ENHANCED_PREVIEW:
            self._strategy = EnhancedPreviewStrategy()
        else:
            raise ValueError(f"不支持的显示模式: {self.display_mode}")

    def set_display_mode(self, mode: LyricDisplayMode, **kwargs):
        """设置显示模式

        Args:
            mode: 显示模式
            **kwargs: 策略特定的参数
        """
        self.display_mode = mode
        if mode == LyricDisplayMode.SIMPLE_FADE:
            self._strategy = SimpleFadeStrategy(**kwargs)
        elif mode == LyricDisplayMode.ENHANCED_PREVIEW:
            self._strategy = EnhancedPreviewStrategy(**kwargs)
        else:
            raise ValueError(f"不支持的显示模式: {mode}")

    def get_filtered_lyrics(self, max_duration: float) -> List[Tuple[float, str]]:
        """获取过滤后的歌词数据（向后兼容接口）

        Args:
            max_duration: 最大时长限制

        Returns:
            过滤后的歌词数据，确保所有歌词的开始时间都在时长限制内
        """
        return [(t, text) for t, text in self.lyrics_data if t < max_duration]

    def calculate_required_rect(self, video_width: int, video_height: int) -> LyricRect:
        """计算所需的显示区域"""
        if not self._strategy:
            raise ValueError("显示策略未设置")
        return self._strategy.calculate_required_rect(self, video_width, video_height)

    # generate_clips方法已移除
    # 新的LyricClip架构不再需要LyricTimeline生成ImageClip
    # 所有渲染现在通过LyricClip的统一frame_function处理

    @property
    def max_lines(self) -> int:
        """获取最大行数（公共只读属性）"""
        return self._max_lines

    def get_content_at_time(self, t: float, max_duration: float = float('inf'),
                           animation_duration: float = 0.3) -> List[Dict[str, Any]]:
        """获取指定时间的歌词内容（支持多条歌词同时显示）

        重构后的版本：
        - 支持淡入淡出时前后歌词同时存在
        - 提前开始淡入动画（从start_time - animation_duration开始）
        - 直接返回包含动画进度的歌词列表

        Args:
            t: 时间点（秒）
            max_duration: 视频最大时长
            animation_duration: 动画持续时间

        Returns:
            歌词内容列表，每个元素包含text, start_time, duration, animation_progress等信息
        """
        active_lyrics = []

        for i, (start_time, text) in enumerate(self.lyrics_data):
            duration = self._calculate_lyric_duration(i, max_duration)

            # 计算有效显示时间范围（包括提前淡入）
            fade_in_start = start_time - animation_duration
            fade_out_end = start_time + duration

            # 检查当前时间是否在显示范围内
            if fade_in_start <= t < fade_out_end:
                # 计算动画进度
                animation_progress = self._calculate_animation_progress(
                    t, start_time, duration, animation_duration
                )

                if animation_progress >= 0:  # 包含动画进度为0的歌词（淡入开始瞬间）
                    active_lyrics.append({
                        'text': text,
                        'start_time': start_time,
                        'duration': duration,
                        'animation_progress': animation_progress,
                        'index': i,
                        'language': self.language,
                        'style': self.style
                    })

        # 按开始时间排序，确保稳定的渲染顺序
        active_lyrics.sort(key=lambda x: x['start_time'])
        return active_lyrics

    def _calculate_animation_progress(self, t: float, start_time: float,
                                    duration: float, animation_duration: float = 0.3) -> float:
        """计算动画进度（重构版本，支持提前淡入）

        Args:
            t: 当前时间
            start_time: 歌词开始时间
            duration: 歌词持续时间
            animation_duration: 动画持续时间

        Returns:
            动画进度 (0.0-1.0)
        """
        # 提前淡入：从start_time - animation_duration开始
        fade_in_start = start_time - animation_duration
        fade_out_end = start_time + duration

        if t < fade_in_start or t >= fade_out_end:
            return 0.0

        # 淡入阶段
        if t < start_time:
            fade_in_progress = (t - fade_in_start) / animation_duration
            return max(0.0, min(1.0, fade_in_progress))

        # 正常显示阶段
        relative_time = t - start_time
        if relative_time <= duration - animation_duration:
            return 1.0

        # 淡出阶段
        fade_out_start = duration - animation_duration
        if relative_time >= fade_out_start:
            fade_out_progress = (relative_time - fade_out_start) / animation_duration
            return max(0.0, 1.0 - fade_out_progress)

        return 1.0

    def _calculate_lyric_duration(self, lyric_index: int, max_duration: float = float('inf')) -> float:
        """计算歌词持续时间

        Args:
            lyric_index: 歌词索引
            max_duration: 视频最大时长，用于限制最后一句歌词的持续时间

        Returns:
            持续时间（秒）
        """
        if lyric_index >= len(self.lyrics_data):
            return 3.0  # 默认持续时间

        current_time = self.lyrics_data[lyric_index][0]

        # 如果有下一句歌词，使用下一句的开始时间
        if lyric_index + 1 < len(self.lyrics_data):
            next_time = self.lyrics_data[lyric_index + 1][0]
            return next_time - current_time

        # 最后一句歌词：持续到视频结束
        if max_duration != float('inf'):
            return max(3.0, max_duration - current_time)  # 至少3秒，最多到视频结束
        else:
            return float('inf')  # 持续到视频结束

    def render(self, frame_buffer: np.ndarray, context: RenderContext):
        """渲染歌词到帧缓冲区（OpenCV优化版本，支持多条歌词同时显示）

        Args:
            frame_buffer: 目标帧缓冲区 (height, width, 3) - RGB格式
            context: 渲染上下文
        """
        # 初始化缓存（如果需要）
        if not self._cache_initialized:
            self._initialize_text_cache(context.video_size)
            self._cache_initialized = True

        # 获取当前时间的所有活动歌词（支持多条歌词同时显示）
        active_lyrics = self.get_content_at_time(context.current_time)
        if not active_lyrics:
            return

        # 遍历所有活动歌词，按顺序渲染
        for lyric in active_lyrics:
            animation_progress = lyric['animation_progress']

            if animation_progress < 0.001:  # 过滤掉几乎不可见的歌词
                continue

            # 获取缓存的文字图片
            cache_key = self._get_cache_key(lyric['text'])
            if cache_key not in self._text_cache:
                # 如果缓存中没有，动态创建
                self._create_text_image_opencv(lyric['text'], cache_key, context.video_size)

            # 使用OpenCV alpha blending渲染到帧缓冲区
            self._render_cached_text_opencv(frame_buffer, cache_key, animation_progress, context)

    def _initialize_text_cache(self, video_size: Tuple[int, int]):
        """初始化文字图片缓存"""
        # 预计算所有歌词的文字图片
        print(f"   初始化文字缓存，共 {len(self.lyrics_data)} 条歌词...")
        for timestamp, text in self.lyrics_data:
            cache_key = self._get_cache_key(text)
            if cache_key not in self._text_cache:
                self._create_text_image_opencv(text, cache_key, video_size)
        print(f"   ✅ 文字缓存初始化完成，缓存 {len(self._text_cache)} 个文字图片")

    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        # 使用文本内容和样式信息生成唯一键
        style_key = f"{self.style.font_size}_{self.style.font_color}_{self.style.highlight_color}"
        return f"{hash(text)}_{hash(style_key)}"

    def _create_text_image_opencv(self, text: str, cache_key: str, video_size: Tuple[int, int]):
        """使用OpenCV创建文字图片并缓存"""
        # 检测文本语言
        language = detect_text_language(text)

        # 获取字体
        font = FontCache.get_font(
            font_path=None,  # 使用默认字体
            size=self.style.font_size,
            language=language
        )

        # 使用PIL创建文字图片（后续可以优化为纯OpenCV）
        from PIL import Image, ImageDraw

        # 计算文字尺寸
        lines = text.split('\n')
        line_height = int(self.style.font_size * 1.2)
        max_width = 0
        total_height = len(lines) * line_height

        for line in lines:
            if line.strip():
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                max_width = max(max_width, line_width)

        if max_width <= 0 or total_height <= 0:
            self._text_cache[cache_key] = None
            return

        # 创建RGBA图像
        img = Image.new('RGBA', (int(max_width), int(total_height)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制文字
        y_offset = 0
        for line in lines:
            if line.strip():
                # 计算居中位置
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                x_pos = (max_width - line_width) // 2

                # 绘制阴影
                draw.text((x_pos + 2, y_offset + 2), line, fill=(0, 0, 0, 200), font=font)

                # 绘制主文字（白色，alpha将在渲染时动态调整）
                draw.text((x_pos, y_offset), line, fill=(255, 255, 255, 255), font=font)

            y_offset += line_height

        # 转换为numpy数组并缓存
        text_array = np.array(img)
        self._text_cache[cache_key] = text_array

    def _render_cached_text_opencv(self, frame_buffer: np.ndarray, cache_key: str,
                                  animation_progress: float, context: RenderContext):
        """使用OpenCV将缓存的文字图片渲染到帧缓冲区"""
        if cache_key not in self._text_cache or self._text_cache[cache_key] is None:
            return

        text_img = self._text_cache[cache_key]

        # 计算渲染位置（传递动画进度用于位移计算）
        render_pos = self._get_render_position(text_img.shape, context, animation_progress)
        if render_pos is None:
            return

        x, y = render_pos

        # 使用OpenCV进行alpha blending
        self._opencv_alpha_blend(frame_buffer, text_img, x, y, animation_progress)

    def _get_render_position(self, text_shape: Tuple[int, int, int], context: RenderContext, 
                            animation_progress: float = 1.0) -> Optional[Tuple[int, int]]:
        """根据显示策略计算渲染位置，支持动画偏移"""
        text_height, text_width = text_shape[:2]
        video_width, video_height = context.video_size
        
        # 计算纵向动画偏移（自下向上运动）
        # 淡入时从下方ANIMATION_VERTICAL_OFFSET像素开始，淡出时向上方移动
        if animation_progress < 1.0:
            # 动画阶段：从下方向上移动
            vertical_offset = int(ANIMATION_VERTICAL_OFFSET * (1.0 - animation_progress))
        else:
            # 完全显示阶段：无偏移
            vertical_offset = 0

        if self.display_mode == LyricDisplayMode.SIMPLE_FADE:
            # 简单模式：使用策略中的y_position
            if self._strategy and isinstance(self._strategy, SimpleFadeStrategy):
                y_pos = self._strategy.y_position
                if y_pos is None:
                    y_pos = video_height // 2
            else:
                y_pos = video_height // 2
            x_pos = (video_width - text_width) // 2
            return (x_pos, y_pos - text_height // 2 + vertical_offset)

        elif self.display_mode == LyricDisplayMode.ENHANCED_PREVIEW:
            # 增强预览模式：使用策略中的current_y_offset
            if self._strategy and isinstance(self._strategy, EnhancedPreviewStrategy):
                current_y_offset = self._strategy.current_y_offset
                if current_y_offset is None:
                    current_y_offset = -50
            else:
                current_y_offset = -50
            center_y = video_height // 2 + current_y_offset
            x_pos = (video_width - text_width) // 2
            return (x_pos, center_y - text_height // 2 + vertical_offset)

        # 默认居中
        return ((video_width - text_width) // 2, (video_height - text_height) // 2 + vertical_offset)

    def _opencv_alpha_blend(self, background: np.ndarray, foreground: np.ndarray,
                           x: int, y: int, alpha_factor: float):
        """使用OpenCV进行alpha混合"""
        if foreground.shape[2] != 4:  # 确保前景有alpha通道
            return

        fg_height, fg_width = foreground.shape[:2]

        # 确保不超出边界
        x = max(0, min(x, background.shape[1] - fg_width))
        y = max(0, min(y, background.shape[0] - fg_height))

        end_y = min(y + fg_height, background.shape[0])
        end_x = min(x + fg_width, background.shape[1])
        actual_height = end_y - y
        actual_width = end_x - x

        if actual_height <= 0 or actual_width <= 0:
            return

        # 获取区域
        bg_region = background[y:end_y, x:end_x]
        fg_region = foreground[:actual_height, :actual_width]

        # 提取alpha通道并应用动画进度
        alpha = fg_region[:, :, 3:4].astype(np.float32) / 255.0 * alpha_factor

        # 执行alpha混合
        bg_region[:, :, :3] = (
            bg_region[:, :, :3].astype(np.float32) * (1 - alpha) +
            fg_region[:, :, :3].astype(np.float32) * alpha
        ).astype(np.uint8)

    def get_processed_lyrics(self, max_duration: float = float('inf')) -> List[Tuple[float, List[str]]]:
        """获取预处理后的歌词数据，供策略类使用

        这是关键的接口：策略类通过这个方法获取已经清理好的字符串数组，
        无需自己实现文本分割和空行清理逻辑

        Args:
            max_duration: 最大时长限制

        Returns:
            List[Tuple[float, List[str]]]: [(时间戳, [清理后的行列表]), ...]
        """
        return [(t, lines) for t, lines in self._processed_lyrics if t < max_duration]

    def get_info(self) -> Dict[str, Any]:
        """获取时间轴信息"""
        return {
            "language": self.language,
            "total_lines": len(self.lyrics_data),
            "max_lines": self._max_lines,
            "duration": self.lyrics_data[-1][0] if self.lyrics_data else 0,
            "display_mode": self.display_mode.value,
            "style": self.style,
            "strategy_info": self._strategy.get_strategy_info() if self._strategy else None,
            "element_id": self._element_id,
            "priority": self._priority,
            "is_flexible": self._is_flexible
        }

    # ============================================================================
    # LayoutElement接口实现
    # ============================================================================

    @property
    def priority(self) -> int:
        """布局优先级（数字越小优先级越高）"""
        return self._priority

    @property
    def is_flexible(self) -> bool:
        """是否可调整位置（用于自动布局）"""
        return self._is_flexible

    @property
    def element_id(self) -> str:
        """元素唯一标识"""
        return self._element_id

    def set_layout_properties(self, priority: Optional[int] = None,
                             is_flexible: Optional[bool] = None,
                             element_id: Optional[str] = None):
        """设置布局属性"""
        if priority is not None:
            self._priority = priority
        if is_flexible is not None:
            self._is_flexible = is_flexible
        if element_id is not None:
            self._element_id = element_id

    @classmethod
    def from_lrc_file(cls, lrc_path: str, language: str = "unknown",
                     display_mode: LyricDisplayMode = LyricDisplayMode.SIMPLE_FADE,
                     style: Optional[LyricStyle] = None,
                     element_id: Optional[str] = None,
                     priority: int = 10,
                     is_flexible: bool = True) -> 'LyricTimeline':
        """从LRC文件创建时间轴"""
        lyrics_data = cls._parse_lrc_file(lrc_path)
        return cls(lyrics_data, language, style, display_mode, element_id, priority, is_flexible)

    @staticmethod
    def _parse_lrc_file(lrc_path: str) -> List[Tuple[float, str]]:
        """解析LRC文件，支持相同时间点的多条记录合并为多行文本

        职责分离重构：
        - 只负责LRC格式解析，保留原始文本
        - 文本清理和预处理统一由_preprocess_lyrics()负责
        """
        lyrics_dict = {}  # 使用字典来收集相同时间点的歌词数组

        with open(lrc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            time_match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
            if time_match:
                minutes = int(time_match.group(1))
                seconds = int(time_match.group(2))
                centiseconds = int(time_match.group(3))
                text = time_match.group(4).strip()
                timestamp = minutes * 60 + seconds + centiseconds / 100

                if text:  # 只处理非空文本
                    if timestamp in lyrics_dict:
                        # 相同时间点的歌词添加到数组
                        lyrics_dict[timestamp].append(text)
                    else:
                        lyrics_dict[timestamp] = [text]

        # 转换为列表，保留原始文本，不进行清理（由_preprocess_lyrics统一处理）
        lyrics = []
        for timestamp, text_lines in lyrics_dict.items():
            # 直接组合为字符串，保留原始内容
            combined_text = '\n'.join(text_lines)
            lyrics.append((timestamp, combined_text))

        return sorted(lyrics, key=lambda x: x[0])