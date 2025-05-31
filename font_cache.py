"""
字体缓存系统

提供高效的字体加载和缓存机制，避免重复的字体对象创建
"""

import os
from typing import Dict, Tuple, Optional
from PIL import ImageFont
import threading


class FontCache:
    """字体缓存管理器
    
    线程安全的字体对象缓存，避免重复加载字体文件
    """
    
    _cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
    _lock = threading.Lock()
    _default_fonts = {
        'chinese': ['simsun.ttc', 'simhei.ttf', 'simkai.ttf'],
        'english': ['arial.ttf', 'calibri.ttf', 'times.ttf'],
        'fallback': None  # PIL默认字体
    }
    
    @classmethod
    def get_font(cls, font_path: Optional[str], size: int, 
                 language: str = 'chinese') -> ImageFont.FreeTypeFont:
        """获取字体对象
        
        Args:
            font_path: 字体文件路径，None表示使用默认字体
            size: 字体大小
            language: 语言类型，用于选择默认字体
            
        Returns:
            字体对象
        """
        # 确定实际的字体路径
        actual_font_path = cls._resolve_font_path(font_path, language)
        cache_key = (actual_font_path or 'default', size)
        
        # 检查缓存
        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]
        
        # 加载字体
        font = cls._load_font(actual_font_path, size)
        
        # 缓存字体
        with cls._lock:
            cls._cache[cache_key] = font
        
        return font
    
    @classmethod
    def _resolve_font_path(cls, font_path: Optional[str], language: str) -> Optional[str]:
        """解析字体路径
        
        Args:
            font_path: 指定的字体路径
            language: 语言类型
            
        Returns:
            实际的字体路径
        """
        if font_path and os.path.exists(font_path):
            return font_path
        
        # 尝试默认字体
        default_fonts = cls._default_fonts.get(language, cls._default_fonts['english'])
        if default_fonts:
            for font_name in default_fonts:
                # 在Windows系统字体目录中查找
                system_font_path = os.path.join('C:', 'Windows', 'Fonts', font_name)
                if os.path.exists(system_font_path):
                    return system_font_path
                
                # 在当前目录查找
                if os.path.exists(font_name):
                    return font_name
        
        return None
    
    @classmethod
    def _load_font(cls, font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
        """加载字体对象
        
        Args:
            font_path: 字体文件路径
            size: 字体大小
            
        Returns:
            字体对象
        """
        try:
            if font_path:
                return ImageFont.truetype(font_path, size)
            else:
                return ImageFont.load_default()
        except (OSError, IOError):
            # 字体加载失败，使用默认字体
            try:
                return ImageFont.load_default()
            except:
                # 如果连默认字体都加载失败，创建一个基础字体
                return ImageFont.load_default()
    
    @classmethod
    def clear_cache(cls):
        """清空字体缓存"""
        with cls._lock:
            cls._cache.clear()
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, int]:
        """获取缓存信息
        
        Returns:
            缓存统计信息
        """
        with cls._lock:
            return {
                'cached_fonts': len(cls._cache),
                'cache_keys': list(cls._cache.keys())
            }


class TextMetricsCache:
    """文本测量结果缓存
    
    缓存文本尺寸测量结果，避免重复计算
    """
    
    _cache: Dict[Tuple[str, str, int], Tuple[int, int]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_text_size(cls, text: str, font_path: Optional[str], 
                     font_size: int, language: str = 'chinese') -> Tuple[int, int]:
        """获取文本尺寸
        
        Args:
            text: 文本内容
            font_path: 字体路径
            font_size: 字体大小
            language: 语言类型
            
        Returns:
            文本尺寸 (width, height)
        """
        # 创建缓存键
        actual_font_path = FontCache._resolve_font_path(font_path, language)
        cache_key = (text, actual_font_path or 'default', font_size)
        
        # 检查缓存
        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]
        
        # 计算文本尺寸
        font = FontCache.get_font(font_path, font_size, language)
        
        # 处理多行文本
        lines = text.split('\n')
        max_width = 0
        total_height = 0
        
        for line in lines:
            if line.strip():  # 跳过空行
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                max_width = max(max_width, line_width)
                total_height += line_height
            else:
                # 空行也要占据一定高度
                total_height += font_size
        
        # 添加行间距
        if len(lines) > 1:
            total_height += (len(lines) - 1) * int(font_size * 0.2)
        
        size = (max_width, total_height)
        
        # 缓存结果
        with cls._lock:
            cls._cache[cache_key] = size
        
        return size
    
    @classmethod
    def clear_cache(cls):
        """清空测量缓存"""
        with cls._lock:
            cls._cache.clear()
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, int]:
        """获取缓存信息"""
        with cls._lock:
            return {
                'cached_measurements': len(cls._cache),
                'cache_keys': list(cls._cache.keys())
            }


def detect_text_language(text: str) -> str:
    """检测文本语言
    
    Args:
        text: 文本内容
        
    Returns:
        语言类型 ('chinese', 'english', 'mixed')
    """
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    total_chars = len([char for char in text if char.isalnum()])
    
    if total_chars == 0:
        return 'english'
    
    chinese_ratio = chinese_chars / total_chars
    
    if chinese_ratio > 0.5:
        return 'chinese'
    elif chinese_ratio > 0:
        return 'mixed'
    else:
        return 'english'
