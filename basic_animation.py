from typing import Dict, Any

# ============================================================================
# 基础数据结构和常量
# ============================================================================

# 动画配置常量
ANIMATION_VERTICAL_OFFSET = 40  # 纵向动画偏移量（像素）

# ============================================================================
# 动画系统实现 - BasicAnimation类
# ============================================================================

class BasicAnimation:
    """基础动画类 - 参数化建模替代字符串枚举
    
    使用OOP方法定义动画效果，支持：
    - 参数化的y偏移量配置
    - 动画进度计算
    - 属性字典的in-place修改
    """
    
    def __init__(self, y_offset_0: float, y_offset_1: float, alpha_0: float = 0.0, alpha_1: float = 1.0):
        """初始化动画参数
        
        Args:
            y_offset_0: 起始Y偏移量（animation_progress=0时的偏移）
            y_offset_1: 结束Y偏移量（animation_progress=1时的偏移）
            alpha_0: 起始透明度（animation_progress=0时的alpha）
            alpha_1: 结束透明度（animation_progress=1时的alpha）
        """
        self.y_offset_0 = y_offset_0
        self.y_offset_1 = y_offset_1
        self.alpha_0 = alpha_0
        self.alpha_1 = alpha_1
    
    def get_y_offset(self, progress: float) -> float:
        """根据动画进度计算Y偏移量
        
        Args:
            progress: 动画进度 (0.0-1.0)
            
        Returns:
            当前的Y偏移量
        """
        progress = max(0.0, min(1.0, progress))  # 确保在有效范围内
        return self.y_offset_0 + (self.y_offset_1 - self.y_offset_0) * progress
    
    def get_alpha(self, progress: float) -> float:
        """根据动画进度计算alpha值
        
        Args:
            progress: 动画进度 (0.0-1.0)
            
        Returns:
            当前的alpha值
        """
        progress = max(0.0, min(1.0, progress))  # 确保在有效范围内
        return self.alpha_0 + (self.alpha_1 - self.alpha_0) * progress
    
    def effect(self, properties: Dict[str, Any], progress: float) -> None:
        """应用动画效果到属性字典（in-place修改）
        
        Args:
            properties: 歌词属性字典，将被直接修改
        """
        properties['y_offset'] = self.get_y_offset(progress)
        properties['alpha'] = self.get_alpha(progress)

# 动画预设 - 避免运行时对象创建
class AnimationPresets:
    """动画预设集合 - 预定义常用的动画配置"""
    
    # 淡入动画：从下方30像素淡入到稳定位置
    FADE_IN = BasicAnimation(
        y_offset_0=ANIMATION_VERTICAL_OFFSET,   # 从下方30像素开始
        y_offset_1=0.0,                         # 移动到稳定位置
        alpha_0=0.0,                           # 从完全透明开始
        alpha_1=1.0                            # 渐变到完全不透明
    )
    
    # 淡出动画：从稳定位置继续向上移动30像素
    FADE_OUT = BasicAnimation(
        y_offset_0=0.0,                         # 从稳定位置开始
        y_offset_1=-ANIMATION_VERTICAL_OFFSET,  # 继续向上移动30像素
        alpha_0=1.0,                           # 从完全不透明开始
        alpha_1=0.0                            # 渐变到完全透明
    )
    
    # 稳定显示：无移动，完全不透明
    STABLE = BasicAnimation(
        y_offset_0=0.0,                        # 稳定位置
        y_offset_1=0.0,                        # 稳定位置
        alpha_0=1.0,                          # 完全不透明
        alpha_1=1.0                           # 完全不透明
    )