"""
歌词MV配置加载器
从YAML文件加载生成歌词MV的基础数据，进行文件存在性和信息完整性检查
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LrcInfo:
    """歌词文件信息"""
    path: str
    lang: str
    font_size: Optional[int] = None  # 可选的字体大小配置

    def __post_init__(self):
        """验证歌词信息"""
        if not self.path:
            raise ValueError("歌词文件路径不能为空")
        if not self.lang:
            raise ValueError("歌词语言不能为空")
        if self.font_size is not None and self.font_size <= 0:
            raise ValueError(f"字体大小必须大于0，当前值: {self.font_size}")


@dataclass
class LrcMvConfig:
    """歌词MV配置类"""
    # 必需字段
    audio: str
    main_lrc: LrcInfo
    background: str
    width: int
    height: int
    output: str

    # 可选字段
    aux_lrc: Optional[LrcInfo] = None

    # 内部字段（用于存储配置文件路径）
    _config_dir: Optional[Path] = None

    def __post_init__(self):
        """配置加载后的验证"""
        self._validate_required_fields()
        self._validate_dimensions()

    def _validate_required_fields(self):
        """验证必需字段"""
        if not self.audio:
            raise ValueError("音频文件路径不能为空")
        if not self.background:
            raise ValueError("背景图片路径不能为空")
        if not self.output:
            raise ValueError("输出文件路径不能为空")

    def _validate_dimensions(self):
        """验证视频尺寸"""
        if self.width <= 0:
            raise ValueError(f"视频宽度必须大于0，当前值: {self.width}")
        if self.height <= 0:
            raise ValueError(f"视频高度必须大于0，当前值: {self.height}")

    def get_absolute_path(self, relative_path: str) -> Path:
        """将相对路径转换为绝对路径"""
        if self._config_dir is None:
            raise RuntimeError("配置目录未设置")
        return self._config_dir / relative_path

    def get_audio_path(self) -> Path:
        """获取音频文件的绝对路径"""
        return self.get_absolute_path(self.audio)

    def get_main_lrc_path(self) -> Path:
        """获取主歌词文件的绝对路径"""
        return self.get_absolute_path(self.main_lrc.path)

    def get_aux_lrc_path(self) -> Optional[Path]:
        """获取副歌词文件的绝对路径"""
        if self.aux_lrc is None:
            return None
        return self.get_absolute_path(self.aux_lrc.path)

    def get_background_path(self) -> Path:
        """获取背景图片的绝对路径"""
        return self.get_absolute_path(self.background)

    def get_output_path(self) -> Path:
        """获取输出文件的绝对路径"""
        return self.get_absolute_path(self.output)

    def check_file_existence(self) -> Dict[str, bool]:
        """检查所有文件是否存在"""
        results = {}

        # 检查音频文件
        audio_path = self.get_audio_path()
        results['audio'] = audio_path.exists()

        # 检查主歌词文件
        main_lrc_path = self.get_main_lrc_path()
        results['main_lrc'] = main_lrc_path.exists()

        # 检查副歌词文件（如果存在）
        if self.aux_lrc is not None:
            aux_lrc_path = self.get_aux_lrc_path()
            results['aux_lrc'] = aux_lrc_path.exists()

        # 检查背景图片
        background_path = self.get_background_path()
        results['background'] = background_path.exists()

        return results

    def validate_files(self, raise_on_missing: bool = True) -> bool:
        """验证所有必需文件是否存在"""
        file_status = self.check_file_existence()
        missing_files = []

        for file_type, exists in file_status.items():
            if not exists:
                missing_files.append(file_type)

        if missing_files:
            error_msg = f"以下文件不存在: {', '.join(missing_files)}"
            if raise_on_missing:
                raise FileNotFoundError(error_msg)
            else:
                print(f"⚠️  {error_msg}")
                return False

        return True

    def print_summary(self):
        """打印配置摘要"""
        print("📋 歌词MV配置摘要:")
        print(f"   音频文件: {self.audio}")
        print(f"   主歌词: {self.main_lrc.path} ({self.main_lrc.lang})")
        if self.aux_lrc:
            print(f"   副歌词: {self.aux_lrc.path} ({self.aux_lrc.lang})")
        print(f"   背景图片: {self.background}")
        print(f"   视频尺寸: {self.width}x{self.height}")
        print(f"   输出文件: {self.output}")

        # 文件存在性检查
        print("\n📁 文件检查:")
        file_status = self.check_file_existence()
        for file_type, exists in file_status.items():
            status_icon = "✅" if exists else "❌"
            print(f"   {status_icon} {file_type}")


def load_lrc_mv_config(yaml_path: str) -> LrcMvConfig:
    """
    从YAML文件加载歌词MV配置

    Args:
        yaml_path: YAML配置文件的路径

    Returns:
        LrcMvConfig: 加载的配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML解析错误
        ValueError: 配置数据无效
    """
    yaml_file = Path(yaml_path)

    # 检查配置文件是否存在
    if not yaml_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {yaml_path}")

    # 读取并解析YAML文件
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析错误: {e}")

    if not isinstance(data, dict):
        raise ValueError("YAML文件格式错误：根元素必须是字典")

    # 验证必需字段
    required_fields = ['audio', 'main-lrc', 'background', 'width', 'height', 'output']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"缺少必需字段: {', '.join(missing_fields)}")

    # 解析主歌词信息
    main_lrc_data = data['main-lrc']
    if not isinstance(main_lrc_data, dict):
        raise ValueError("main-lrc 必须是字典格式")
    if 'path' not in main_lrc_data or 'lang' not in main_lrc_data:
        raise ValueError("main-lrc 必须包含 path 和 lang 字段")

    main_lrc = LrcInfo(
        path=main_lrc_data['path'],
        lang=main_lrc_data['lang'],
        font_size=main_lrc_data.get('font_size')  # 可选的字体大小
    )

    # 解析副歌词信息（可选）
    aux_lrc = None
    if 'aux-lrc' in data:
        aux_lrc_data = data['aux-lrc']
        if not isinstance(aux_lrc_data, dict):
            raise ValueError("aux-lrc 必须是字典格式")
        if 'path' not in aux_lrc_data or 'lang' not in aux_lrc_data:
            raise ValueError("aux-lrc 必须包含 path 和 lang 字段")

        aux_lrc = LrcInfo(
            path=aux_lrc_data['path'],
            lang=aux_lrc_data['lang'],
            font_size=aux_lrc_data.get('font_size')  # 可选的字体大小
        )

    # 验证数值字段
    try:
        width = int(data['width'])
        height = int(data['height'])
    except (ValueError, TypeError) as e:
        raise ValueError(f"宽度和高度必须是整数: {e}")

    # 创建配置对象
    config = LrcMvConfig(
        audio=str(data['audio']),
        main_lrc=main_lrc,
        aux_lrc=aux_lrc,
        background=str(data['background']),
        width=width,
        height=height,
        output=str(data['output']),
        _config_dir=yaml_file.parent
    )

    return config


def demo_config_loader():
    """演示配置加载器的使用"""
    print("🎬 歌词MV配置加载器演示")
    print("=" * 50)

    # 示例配置文件路径
    config_path = r"精武英雄\lrc-mv.yaml"

    try:
        # 加载配置
        print(f"📂 加载配置文件: {config_path}")
        config = load_lrc_mv_config(config_path)

        # 打印配置摘要
        config.print_summary()

        # 验证文件存在性
        print("\n🔍 验证文件存在性...")
        try:
            config.validate_files()
            print("✅ 所有必需文件都存在")
        except FileNotFoundError as e:
            print(f"❌ {e}")

        # 显示绝对路径
        print("\n📍 绝对路径:")
        print(f"   音频: {config.get_audio_path()}")
        print(f"   主歌词: {config.get_main_lrc_path()}")
        if config.aux_lrc:
            print(f"   副歌词: {config.get_aux_lrc_path()}")
        print(f"   背景: {config.get_background_path()}")
        print(f"   输出: {config.get_output_path()}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")


if __name__ == "__main__":
    demo_config_loader()
