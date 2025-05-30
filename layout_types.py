"""
Layout Types - 布局相关数据类型

定义布局系统中使用的基础数据类型，避免循环导入问题。
包含：
- LyricRect: 歌词显示区域信息
- 其他布局相关的基础数据类型

这个模块被layout_engine.py和lyric_timeline.py共同使用。
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class LyricRect:
    """歌词显示区域信息
    
    表示歌词在视频中的显示区域，支持重叠检测和位置计算
    """
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        """验证尺寸参数"""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("宽度和高度必须大于0")

    def contains_point(self, x: int, y: int) -> bool:
        """检查点是否在区域内"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def overlaps_with(self, other: 'LyricRect') -> bool:
        """检查是否与另一个区域重叠"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)

    def get_center(self) -> Tuple[int, int]:
        """获取区域中心点"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def get_area(self) -> int:
        """获取区域面积"""
        return self.width * self.height

    def __str__(self) -> str:
        """字符串表示"""
        return f"LyricRect(x={self.x}, y={self.y}, w={self.width}, h={self.height})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return self.__str__()


@dataclass
class LyricStyle:
    """歌词样式配置
    
    封装所有与歌词显示相关的样式参数
    """
    font_size: int = 80
    font_color: str = 'white'
    highlight_color: str = '#FFD700'
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 200)
    glow_enabled: bool = False
    animation_style: str = 'fade'

    def copy(self) -> 'LyricStyle':
        """创建样式副本"""
        return LyricStyle(
            font_size=self.font_size,
            font_color=self.font_color,
            highlight_color=self.highlight_color,
            shadow_color=self.shadow_color,
            glow_enabled=self.glow_enabled,
            animation_style=self.animation_style
        )


# ============================================================================
# 模块信息
# ============================================================================

__all__ = [
    'LyricRect',
    'LyricStyle'
]

__version__ = '1.0.0'
__author__ = 'Augment Agent'
__description__ = 'Layout system data types and structures'
