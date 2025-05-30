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
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from moviepy.editor import ImageClip

# 导入布局相关的数据类型
from layout_types import LyricRect, LyricStyle
from layout_engine import LayoutElement

# ============================================================================
# 基础数据结构
# ============================================================================

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

    @abstractmethod
    def generate_clips(self, timeline: 'LyricTimeline',
                      generator: Any, duration: float) -> List[ImageClip]:
        """生成歌词视频片段"""
        pass

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

        return LyricRect(
            x=0,
            y=y_pos - total_height // 2,
            width=video_width,
            height=total_height
        )

    def generate_clips(self, timeline: 'LyricTimeline',
                      generator: Any, duration: float) -> List[ImageClip]:
        """生成简单淡入淡出片段

        Args:
            timeline: 歌词时间轴对象
            generator: 视频生成器对象
            duration: 视频总时长限制

        Returns:
            生成的视频片段列表，所有片段都严格遵守时长限制
        """
        clips = []
        # 使用新接口：获取预处理后的歌词数据（字符串数组）
        processed_lyrics = timeline.get_processed_lyrics(duration)
        rect = self.calculate_required_rect(timeline, generator.width, generator.height)

        for i, (start_time, lines) in enumerate(processed_lyrics):
            # 计算结束时间，确保不超过总时长限制
            if i < len(processed_lyrics) - 1:
                end_time = min(processed_lyrics[i + 1][0], duration)
            else:
                end_time = duration

            # 确保开始时间在时长限制内
            if start_time >= duration:
                print(f"   跳过歌词（开始时间超出限制 {start_time:.2f}s >= {duration:.2f}s）: '{lines}'")
                continue

            lyric_duration = end_time - start_time
            if lyric_duration <= 0.01:
                print(f"   跳过歌词（时长过短 {lyric_duration:.2f}s）: '{lines}'")
                continue

            # 最终验证：确保片段不会超出时长限制
            if start_time + lyric_duration > duration:
                lyric_duration = duration - start_time
                print(f"   调整歌词时长以符合限制: '{lines}' -> {lyric_duration:.2f}s")

            # 重新组合为文本（保持与渲染器的接口兼容）
            text = '\n'.join(lines)

            # 传递字体大小到生成器
            clip = generator.create_lyric_clip_with_animation(
                text, start_time, lyric_duration,
                is_highlighted=self.is_highlighted,
                y_position=rect.y + rect.height // 2,
                animation=timeline.style.animation_style,
                font_size=timeline.style.font_size
            )
            clips.append(clip)

        return clips

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
        center_y = video_height // 2

        return LyricRect(
            x=0,
            y=center_y - total_height // 2,
            width=video_width,
            height=total_height
        )

    def generate_clips(self, timeline: 'LyricTimeline',
                      generator: Any, duration: float) -> List[ImageClip]:
        """生成增强预览片段

        这里封装了原有enhanced_generator.py中的增强模式逻辑

        Args:
            timeline: 歌词时间轴对象
            generator: 视频生成器对象
            duration: 视频总时长限制

        Returns:
            生成的视频片段列表，包括当前歌词和预览歌词，所有片段都严格遵守时长限制
        """
        clips = []
        # 使用新接口：获取预处理后的歌词数据（字符串数组）
        processed_lyrics = timeline.get_processed_lyrics(duration)
        center_y = generator.height // 2

        for i, (start_time, lines) in enumerate(processed_lyrics):
            # 计算结束时间，确保不超过总时长限制
            if i < len(processed_lyrics) - 1:
                end_time = min(processed_lyrics[i + 1][0], duration)
            else:
                end_time = duration

            # 确保开始时间在时长限制内
            if start_time >= duration:
                print(f"   跳过主歌词（开始时间超出限制 {start_time:.2f}s >= {duration:.2f}s）: '{lines}'")
                continue

            lyric_duration = end_time - start_time
            if lyric_duration <= 0.01:
                print(f"   跳过主歌词（时长过短 {lyric_duration:.2f}s）: '{lines}'")
                continue

            # 最终验证：确保片段不会超出时长限制
            if start_time + lyric_duration > duration:
                lyric_duration = duration - start_time
                print(f"   调整主歌词时长以符合限制: '{lines}' -> {lyric_duration:.2f}s")

            # 重新组合为文本（保持与渲染器的接口兼容）
            text = '\n'.join(lines)

            # 当前歌词（高亮）- 传递字体大小到生成器
            current_clip = generator.create_lyric_clip_with_animation(
                text, start_time, lyric_duration,
                is_highlighted=True,
                y_position=center_y + self.current_y_offset,
                animation=timeline.style.animation_style,
                font_size=timeline.style.font_size
            )
            clips.append(current_clip)

            # 下一句预览（非高亮）- 对应原来的next_clip
            if i < len(processed_lyrics) - 1:
                next_lines = processed_lyrics[i + 1][1]
                next_text = '\n'.join(next_lines)  # 重新组合下一句
                # 预览歌词也需要遵守时长限制
                if start_time + lyric_duration <= duration:
                    # 预览歌词使用稍小的字体
                    preview_font_size = max(10, timeline.style.font_size - 20)
                    preview_clip = generator.create_lyric_clip_with_animation(
                        next_text, start_time, lyric_duration,
                        is_highlighted=False,
                        y_position=center_y + self.preview_y_offset,
                        animation='fade',  # 预览总是使用fade动画
                        font_size=preview_font_size
                    )
                    clips.append(preview_clip)

        return clips



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

    def generate_clips(self, generator: Any, duration: float) -> List[ImageClip]:
        """生成视频片段"""
        if not self._strategy:
            raise ValueError("显示策略未设置")
        return self._strategy.generate_clips(self, generator, duration)

    @property
    def max_lines(self) -> int:
        """获取最大行数（公共只读属性）"""
        return self._max_lines

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

# ============================================================================
# 便捷函数和工厂方法
# ============================================================================

def create_enhanced_timeline(lyrics_data: List[Tuple[float, str]],
                           language: str = "chinese",
                           element_id: Optional[str] = None,
                           priority: int = 5) -> LyricTimeline:
    """创建增强预览模式的时间轴（便捷函数）"""
    style = LyricStyle(
        font_size=80,
        highlight_color='#FFD700',
        glow_enabled=True,
        animation_style='fade'
    )
    return LyricTimeline(
        lyrics_data=lyrics_data,
        language=language,
        style=style,
        display_mode=LyricDisplayMode.ENHANCED_PREVIEW,
        element_id=element_id or f"enhanced_{language}",
        priority=priority,
        is_flexible=True
    )

def create_simple_timeline(lyrics_data: List[Tuple[float, str]],
                         language: str = "english",
                         is_highlighted: bool = False,
                         element_id: Optional[str] = None,
                         priority: int = 10) -> LyricTimeline:
    """创建简单淡入淡出模式的时间轴（便捷函数）"""
    timeline = LyricTimeline(
        lyrics_data=lyrics_data,
        language=language,
        display_mode=LyricDisplayMode.SIMPLE_FADE,
        element_id=element_id or f"simple_{language}",
        priority=priority,
        is_flexible=True
    )
    timeline.set_display_mode(
        LyricDisplayMode.SIMPLE_FADE,
        is_highlighted=is_highlighted
    )
    return timeline

def create_bilingual_timelines(main_lyrics: List[Tuple[float, str]],
                             aux_lyrics: List[Tuple[float, str]],
                             main_language: str = "chinese",
                             aux_language: str = "english",
                             video_height: int = 720) -> Tuple[LyricTimeline, LyricTimeline]:
    """创建双语时间轴对（便捷函数）

    重构后的版本：
    - main_timeline使用ENHANCED_PREVIEW模式，优先级更高
    - aux_timeline使用SIMPLE_FADE模式，优先级较低，并设置合适的y位置避免重叠
    """
    # 主时间轴使用增强预览模式，优先级高
    main_timeline = LyricTimeline(
        lyrics_data=main_lyrics,
        language=main_language,
        style=LyricStyle(font_size=80, highlight_color='#FFD700'),
        display_mode=LyricDisplayMode.ENHANCED_PREVIEW,
        element_id=f"main_{main_language}",
        priority=1,  # 高优先级
        is_flexible=False  # 主歌词位置固定
    )

    # 副时间轴使用简单模式，显示在下方，优先级低
    aux_timeline = LyricTimeline(
        lyrics_data=aux_lyrics,
        language=aux_language,
        style=LyricStyle(font_size=60, font_color='white'),
        display_mode=LyricDisplayMode.SIMPLE_FADE,
        element_id=f"aux_{aux_language}",
        priority=10,  # 低优先级
        is_flexible=True  # 副歌词位置可调整
    )
    # 设置副歌词显示在下方，避免与主歌词重叠
    aux_timeline.set_display_mode(
        LyricDisplayMode.SIMPLE_FADE,
        y_position=video_height // 2 + 100,  # 显示在中心下方
        is_highlighted=False
    )

    return main_timeline, aux_timeline

# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 示例数据
    test_lyrics = [
        (0.0, "第一句歌词"),
        (3.0, "第二句歌词"),
        (6.0, "第三句歌词"),
        (9.0, "第四句歌词")
    ]

    print("🎵 LyricTimeline OOP重构演示")
    print("=" * 50)

    # 创建增强预览模式时间轴
    enhanced_timeline = create_enhanced_timeline(test_lyrics, "chinese")
    print("✅ 增强预览模式时间轴创建成功")
    print(f"📊 时间轴信息: {enhanced_timeline.get_info()}")

    # 创建简单模式时间轴
    simple_timeline = create_simple_timeline(test_lyrics, "english")
    print("\n✅ 简单模式时间轴创建成功")
    print(f"📊 时间轴信息: {simple_timeline.get_info()}")

    # 计算所需区域
    video_width, video_height = 1280, 720
    enhanced_rect = enhanced_timeline.calculate_required_rect(video_width, video_height)
    simple_rect = simple_timeline.calculate_required_rect(video_width, video_height)

    print(f"\n📐 增强模式所需区域: {enhanced_rect}")
    print(f"📐 简单模式所需区域: {simple_rect}")

    # 检查区域重叠
    if enhanced_rect.overlaps_with(simple_rect):
        print("⚠️  警告: 两个时间轴的显示区域重叠!")
    else:
        print("✅ 两个时间轴的显示区域不重叠，可以同时使用")

    # 动态切换显示模式示例
    print("\n🔄 动态切换显示模式演示:")
    enhanced_timeline.set_display_mode(
        LyricDisplayMode.ENHANCED_PREVIEW,
        current_y_offset=-60,
        preview_y_offset=100
    )
    print("✅ 已切换增强模式参数")

    print("\n🎉 LyricTimeline OOP重构演示完成！")
    print("💡 现在可以在enhanced_generator.py中集成这些类了")