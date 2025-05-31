"""
LyricContent数据类定义

定义歌词内容的数据结构，用于LyricClip渲染系统
"""

from dataclasses import dataclass
from typing import Optional
from layout_types import LyricStyle, LyricRect


@dataclass
class LyricContent:
    """歌词内容数据类

    封装单个歌词片段在特定时间点的所有渲染信息
    """
    text: str                    # 歌词文本内容
    start_time: float           # 开始时间
    duration: float             # 持续时间
    style: LyricStyle          # 样式配置
    position: LyricRect        # 位置和尺寸
    animation_progress: float   # 动画进度 (0.0-1.0)
    is_highlighted: bool       # 是否高亮显示

    @property
    def end_time(self) -> float:
        """结束时间"""
        return self.start_time + self.duration

    def is_active_at_time(self, t: float) -> bool:
        """检查在指定时间是否活跃"""
        return self.start_time <= t < self.end_time

    def get_relative_time(self, t: float) -> float:
        """获取相对于开始时间的时间偏移"""
        return max(0.0, t - self.start_time)

    def calculate_animation_progress(self, t: float, animation_duration: float = 0.3) -> float:
        """计算动画进度

        Args:
            t: 当前时间
            animation_duration: 动画持续时间

        Returns:
            动画进度 (0.0-1.0)
        """
        if not self.is_active_at_time(t):
            return 0.0

        relative_time = self.get_relative_time(t)

        # 淡入动画
        if relative_time <= animation_duration:
            return relative_time / animation_duration

        # 淡出动画
        fade_out_start = self.duration - animation_duration
        if relative_time >= fade_out_start:
            fade_out_progress = (relative_time - fade_out_start) / animation_duration
            return 1.0 - fade_out_progress

        # 完全显示
        return 1.0


@dataclass
class RenderContext:
    """渲染上下文

    包含渲染过程中需要的全局信息
    """
    current_time: float         # 当前渲染时间
    video_size: tuple          # 视频尺寸 (width, height)
    fps: float                 # 帧率
    frame_number: int          # 当前帧号

    def get_frame_time(self) -> float:
        """获取当前帧对应的时间"""
        return self.frame_number / self.fps


class LyricContentFactory:
    """歌词内容工厂类

    负责从LyricTimeline创建LyricContent对象
    """

    @staticmethod
    def create_from_timeline(timeline, t: float, layout_rect: LyricRect) -> Optional[LyricContent]:
        """从时间轴创建歌词内容

        Args:
            timeline: LyricTimeline对象
            t: 当前时间
            layout_rect: 布局位置

        Returns:
            LyricContent对象或None
        """
        # 查找当前时间的歌词
        active_lyric = None

        for i, (start_time, text) in enumerate(timeline.lyrics_data):
            # 使用正确的持续时间计算逻辑（与旧实现一致）
            duration = LyricContentFactory.calculate_lyric_duration(timeline, i)

            if start_time <= t < start_time + duration:
                active_lyric = (start_time, text, duration)
                break

        if not active_lyric:
            return None

        start_time, text, duration = active_lyric

        # 创建LyricContent对象
        content = LyricContent(
            text=text,
            start_time=start_time,
            duration=duration,
            style=timeline.style,
            position=layout_rect,
            animation_progress=0.0,  # 将在渲染时计算
            is_highlighted=timeline._strategy.is_highlighted if hasattr(timeline._strategy, 'is_highlighted') else True
        )

        # 计算动画进度
        content.animation_progress = content.calculate_animation_progress(t)

        return content

    @staticmethod
    def calculate_lyric_duration(timeline, lyric_index: int) -> float:
        """计算歌词持续时间

        Args:
            timeline: LyricTimeline对象
            lyric_index: 歌词索引

        Returns:
            持续时间（秒）
        """
        lyrics_data = timeline.lyrics_data

        if lyric_index >= len(lyrics_data):
            return 3.0  # 默认持续时间

        current_time = lyrics_data[lyric_index][0]

        # 如果有下一句歌词，使用下一句的开始时间
        if lyric_index + 1 < len(lyrics_data):
            next_time = lyrics_data[lyric_index + 1][0]
            return next_time - current_time

        # 最后一句歌词，使用默认持续时间
        return 3.0
