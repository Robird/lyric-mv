"""
Layout Engine - 布局引擎模块

提供多时间轴的2D空间自动布局功能，包括：
- LayoutElement: 布局元素抽象接口
- LayoutStrategy: 布局策略抽象基类
- VerticalStackStrategy: 垂直堆叠布局策略
- LayoutEngine: 布局引擎核心类
- LayoutResult: 布局计算结果

这个模块从lyric_timeline.py中拆分出来，专门负责布局相关功能。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# 导入布局相关的数据类型
from layout_types import LyricRect


# ============================================================================
# 布局元素抽象接口
# ============================================================================

class LayoutElement(ABC):
    """布局元素抽象基类

    定义了所有可以参与布局的视觉元素必须实现的接口
    """

    @abstractmethod
    def calculate_required_rect(self, video_width: int, video_height: int) -> LyricRect:
        """计算所需的显示区域"""
        pass

    @abstractmethod
    def generate_clips(self, generator: Any, duration: float) -> List[Any]:
        """生成视频片段"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """布局优先级（数字越小优先级越高）"""
        pass

    @property
    @abstractmethod
    def is_flexible(self) -> bool:
        """是否可调整位置（用于自动布局）"""
        pass

    @property
    @abstractmethod
    def element_id(self) -> str:
        """元素唯一标识"""
        pass


# ============================================================================
# 布局结果数据结构
# ============================================================================

@dataclass
class LayoutResult:
    """布局计算结果"""
    element_positions: Dict[str, LyricRect]  # 元素ID -> 位置
    has_conflicts: bool = False
    conflict_info: Optional[List[str]] = None

    def __post_init__(self):
        if self.conflict_info is None:
            self.conflict_info = []


# ============================================================================
# 布局策略抽象基类和实现
# ============================================================================

class LayoutStrategy(ABC):
    """布局策略抽象基类"""

    @abstractmethod
    def arrange_elements(self, elements: List[LayoutElement],
                        video_width: int, video_height: int) -> LayoutResult:
        """安排元素布局"""
        pass


class VerticalStackStrategy(LayoutStrategy):
    """垂直堆叠布局策略

    按优先级从上到下垂直排列元素，自动避免重叠
    """

    def __init__(self, spacing: int = 20, start_y: Optional[int] = None):
        """
        Args:
            spacing: 元素间距
            start_y: 起始Y位置，None表示居中开始
        """
        self.spacing = spacing
        self.start_y = start_y

    def arrange_elements(self, elements: List[LayoutElement],
                        video_width: int, video_height: int) -> LayoutResult:
        """垂直堆叠排列元素"""
        if not elements:
            return LayoutResult({})

        # 按优先级排序
        sorted_elements = sorted(elements, key=lambda e: e.priority)

        # 计算每个元素的原始尺寸
        element_rects = {}
        for element in sorted_elements:
            rect = element.calculate_required_rect(video_width, video_height)
            element_rects[element.element_id] = rect

        # 计算总高度
        total_height = sum(rect.height for rect in element_rects.values())
        total_height += self.spacing * (len(elements) - 1)

        # 确定起始位置
        if self.start_y is not None:
            current_y = self.start_y
        else:
            current_y = (video_height - total_height) // 2

        # 重新分配位置
        result_positions = {}
        for element in sorted_elements:
            rect = element_rects[element.element_id]
            new_rect = LyricRect(
                x=rect.x,  # 保持原始X位置
                y=current_y,
                width=rect.width,
                height=rect.height
            )
            result_positions[element.element_id] = new_rect
            current_y += rect.height + self.spacing

        return LayoutResult(result_positions)


# ============================================================================
# 布局引擎核心类
# ============================================================================

class LayoutEngine:
    """布局引擎 - 管理多个timeline的2D空间分配"""

    def __init__(self, strategy: LayoutStrategy):
        self.strategy = strategy
        self.elements: List[LayoutElement] = []

    def add_element(self, element: LayoutElement):
        """添加布局元素"""
        # 检查是否已存在相同ID的元素
        existing_ids = [e.element_id for e in self.elements]
        if element.element_id in existing_ids:
            raise ValueError(f"元素ID '{element.element_id}' 已存在")

        self.elements.append(element)

    def clear_elements(self):
        """清空所有元素"""
        self.elements.clear()

    def calculate_layout(self, video_width: int, video_height: int) -> LayoutResult:
        """计算最优布局"""
        return self.strategy.arrange_elements(self.elements, video_width, video_height)

    def detect_conflicts(self, video_width: int, video_height: int) -> List[str]:
        """检测布局冲突

        注意：这里检测的是元素原始区域的冲突，而不是布局后的区域
        """
        if len(self.elements) < 2:
            return []

        conflicts = []

        # 计算每个元素的原始区域（不经过布局调整）
        element_rects = {}
        for element in self.elements:
            rect = element.calculate_required_rect(video_width, video_height)
            element_rects[element.element_id] = rect

        # 检查两两重叠
        element_ids = list(element_rects.keys())
        for i in range(len(element_ids)):
            for j in range(i + 1, len(element_ids)):
                id1, id2 = element_ids[i], element_ids[j]
                rect1 = element_rects[id1]
                rect2 = element_rects[id2]

                if rect1.overlaps_with(rect2):
                    conflicts.append(f"元素 '{id1}' 与 '{id2}' 重叠")

        return conflicts


# ============================================================================
# 模块信息
# ============================================================================

__all__ = [
    'LayoutElement',
    'LayoutResult',
    'LayoutStrategy',
    'VerticalStackStrategy',
    'LayoutEngine'
]

__version__ = '1.0.0'
__author__ = 'Augment Agent'
__description__ = 'Layout Engine for multi-timeline 2D space management'
