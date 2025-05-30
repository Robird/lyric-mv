# 精武英雄歌词视频生成器 (Jingwu Hero Lyric Video Generator)

一个基于面向对象设计的高级歌词视频生成工具，采用策略模式架构，支持多语言歌词、智能布局和专业级视频输出。

## 🌟 核心特性

- ✅ **面向对象架构**: 基于LyricTimeline类的现代化设计
- ✅ **策略模式**: 可扩展的显示策略系统
- ✅ **双语支持**: 中英文歌词智能布局，避免重叠
- ✅ **增强预览**: 当前歌词高亮+下一句预览模式
- ✅ **智能布局**: 自动计算显示区域，检测重叠冲突
- ✅ **配置驱动**: YAML配置文件支持，便于批量处理
- ✅ **专业输出**: 支持多种分辨率和编码格式
- ✅ **向后兼容**: 保持旧版接口完全可用

## 📦 环境要求

```bash
# Python 3.8+
# 推荐使用conda环境管理
conda create -n lyrc-mv python=3.12
conda activate lyrc-mv

# 安装核心依赖
pip install moviepy==1.0.3 pillow numpy pyyaml

# 可选：音频处理增强
pip install scipy
```

## 🚀 快速开始

### 现代化OOP接口（推荐）

```python
from enhanced_generator import EnhancedJingwuGenerator
from lyric_timeline import LyricTimeline, LyricDisplayMode

# 创建生成器
generator = EnhancedJingwuGenerator(width=720, height=1280, fps=30)

# 创建歌词时间轴
main_timeline = LyricTimeline.from_lrc_file(
    "chinese.lrc",
    language="chinese",
    display_mode=LyricDisplayMode.ENHANCED_PREVIEW
)

aux_timeline = LyricTimeline.from_lrc_file(
    "english.lrc",
    language="english",
    display_mode=LyricDisplayMode.SIMPLE_FADE
)

# 智能布局检测
main_rect = main_timeline.calculate_required_rect(720, 1280)
aux_rect = aux_timeline.calculate_required_rect(720, 1280)
if main_rect.overlaps_with(aux_rect):
    print("警告: 歌词区域重叠，自动调整布局")

# 生成双语视频
success = generator.generate_bilingual_video(
    main_timeline=main_timeline,
    aux_timeline=aux_timeline,
    audio_path="song.flac",
    output_path="output.mp4",
    background_image="background.jpg"
)
```

### 配置文件驱动（生产环境推荐）

```yaml
# lrc-mv.yaml
audio: "精武英雄 - 甄子丹.flac"
background: "bg_v.png"
output: "精武英雄 - 甄子丹.mp4"
width: 720
height: 1280

main_lrc:
  path: "精武英雄 - 甄子丹.lrc"
  lang: "hans"

aux_lrc:
  path: "Jingwu Hero - Donnie Yen.lrc"
  lang: "en"
```

```python
from enhanced_generator import demo_enhanced_features
from pathlib import Path

# 一键生成专业视频
success = demo_enhanced_features(
    config_path=Path("lrc-mv.yaml"),
    t_max_sec=60.0  # 限制时长用于测试
)
```

### 自定义样式和布局

```python
from lyric_timeline import LyricStyle

# 创建自定义样式
custom_style = LyricStyle(
    font_size=80,
    font_color='white',
    highlight_color='#FFD700',  # 金色高亮
    glow_enabled=True,
    animation_style='fade'
)

# 应用到时间轴
timeline = LyricTimeline(
    lyrics_data=lyrics,
    language="chinese",
    style=custom_style,
    display_mode=LyricDisplayMode.ENHANCED_PREVIEW
)

# 动态调整显示模式
timeline.set_display_mode(
    LyricDisplayMode.ENHANCED_PREVIEW,
    current_y_offset=-60,
    preview_y_offset=100
)
```

## 📄 LRC文件格式

```lrc
[00:00.00]第一句歌词
[00:03.50]第二句歌词
[00:07.20]第三句歌词
[00:11.80]最后一句歌词
```

## 🎨 架构特性

### 显示策略模式
- **SimpleFadeStrategy**: 简单淡入淡出，适合副歌词
- **EnhancedPreviewStrategy**: 当前歌词+下一句预览，适合主歌词
- **可扩展设计**: 支持自定义策略（如卡拉OK模式）

### 智能布局系统
- **自动区域计算**: 每个时间轴自报告所需显示区域
- **重叠检测**: 自动检测多个时间轴的显示冲突
- **独立定位**: 每个时间轴独立管理自己的位置和样式

### 双语支持
- **独立时间轴**: 主副歌词完全解耦，各自管理显示逻辑
- **智能布局**: 自动避免中英文歌词重叠
- **灵活组合**: 支持任意显示模式组合

### 配置系统
- **YAML驱动**: 支持配置文件批量处理
- **类型安全**: 完整的类型注解和验证
- **向后兼容**: 保持旧版接口完全可用

## 📁 项目结构

```
jingwu-hero/
├── enhanced_generator.py      # 核心视频生成器
├── lyric_timeline.py         # 歌词时间轴OOP实现
├── lrc_mv_config.py          # 配置文件处理
├── 精武英雄/                  # 示例项目
│   ├── lrc-mv.yaml           # 配置文件
│   ├── 精武英雄 - 甄子丹.lrc   # 中文歌词
│   ├── Jingwu Hero - Donnie Yen.lrc  # 英文歌词
│   ├── 精武英雄 - 甄子丹.flac  # 音频文件
│   └── bg_v.png              # 背景图片
├── ai_memory/                # 设计文档和记忆
├── local_docs/               # 详细文档
└── README.md                 # 项目说明
```

## 🔧 核心API

### LyricTimeline类（核心）

```python
class LyricTimeline:
    def __init__(self, lyrics_data: List[Tuple[float, str]],
                 language: str = "unknown",
                 style: Optional[LyricStyle] = None,
                 display_mode: LyricDisplayMode = LyricDisplayMode.SIMPLE_FADE):
        """初始化歌词时间轴"""

    @classmethod
    def from_lrc_file(cls, lrc_path: str, language: str = "unknown",
                     display_mode: LyricDisplayMode = LyricDisplayMode.SIMPLE_FADE,
                     style: Optional[LyricStyle] = None) -> 'LyricTimeline':
        """从LRC文件创建时间轴"""

    def set_display_mode(self, mode: LyricDisplayMode, **kwargs):
        """设置显示模式和参数"""

    def calculate_required_rect(self, video_width: int, video_height: int) -> LyricRect:
        """计算所需显示区域"""

    def generate_clips(self, generator: Any, duration: float) -> List[ImageClip]:
        """生成视频片段"""
```

### EnhancedJingwuGenerator类

```python
class EnhancedJingwuGenerator:
    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        """初始化生成器"""

    def generate_bilingual_video(self,
                               main_timeline: 'LyricTimeline',
                               aux_timeline: Optional['LyricTimeline'] = None,
                               audio_path: str = "",
                               output_path: str = "",
                               background_image: Optional[str] = None,
                               t_max_sec: float = float('inf')) -> bool:
        """生成双语视频"""
```

### 主要参数说明

- `main_timeline`: 主歌词时间轴对象
- `aux_timeline`: 副歌词时间轴对象（可选）
- `audio_path`: 音频文件路径
- `output_path`: 输出视频路径
- `background_image`: 背景图片路径
- `t_max_sec`: 最大时长限制

## 🎯 使用示例

### 快速测试

```bash
# 运行核心功能测试
python lyric_timeline.py

# 生成示例视频（60秒测试版）
python enhanced_generator.py
```

### 生产环境使用

```python
# 方式1: 配置文件驱动（推荐）
from enhanced_generator import demo_enhanced_features
from pathlib import Path

success = demo_enhanced_features(
    config_path=Path("精武英雄/lrc-mv.yaml"),
    t_max_sec=float('inf')  # 完整视频
)

# 方式2: 编程接口
from enhanced_generator import EnhancedJingwuGenerator
from lyric_timeline import LyricTimeline, LyricDisplayMode

generator = EnhancedJingwuGenerator(width=720, height=1280)

main_timeline = LyricTimeline.from_lrc_file(
    "chinese.lrc", "chinese", LyricDisplayMode.ENHANCED_PREVIEW
)
aux_timeline = LyricTimeline.from_lrc_file(
    "english.lrc", "english", LyricDisplayMode.SIMPLE_FADE
)

success = generator.generate_bilingual_video(
    main_timeline=main_timeline,
    aux_timeline=aux_timeline,
    audio_path="song.flac",
    output_path="output.mp4"
)
```

### 批量处理

```python
# 批量处理多个项目
projects = [
    "project1/lrc-mv.yaml",
    "project2/lrc-mv.yaml",
    "project3/lrc-mv.yaml"
]

for config_file in projects:
    print(f"处理: {config_file}")
    success = demo_enhanced_features(Path(config_file))
    if success:
        print("✅ 成功")
    else:
        print("❌ 失败")
```

## ⚠️ 注意事项

1. **环境要求**: Python 3.8+，推荐使用conda环境管理
2. **首次使用**: MoviePy会自动下载ffmpeg，请确保网络连接正常
3. **音频格式**: 支持.flac、.mp3、.wav、.m4a等高质量格式
4. **中文支持**: 项目已优化中文字体渲染，无需额外配置
5. **内存使用**: 高分辨率视频生成需要较多内存，建议8GB+
6. **布局重叠**: 系统会自动检测歌词重叠并给出警告

## 🐛 常见问题

**Q: 提示"时间轴显示区域重叠"？**
A: 这是正常的布局检测，可以通过调整`y_position`参数解决。

**Q: 视频生成失败？**
A: 检查配置文件路径、音频文件格式，确保所有文件存在。

**Q: 如何自定义歌词位置？**
A: 使用`timeline.set_display_mode()`方法调整位置参数。

**Q: 支持哪些视频分辨率？**
A: 支持任意分辨率，推荐720x1280（竖屏）或1280x720（横屏）。

## 🚀 架构优势

### 重构前 vs 重构后

| 特性 | 重构前 | 重构后 |
|------|--------|--------|
| 架构模式 | 过程式编程 | 面向对象+策略模式 |
| 歌词管理 | 简单列表 | LyricTimeline类 |
| 布局检测 | 手动计算 | 自动检测+报告 |
| 双语支持 | 耦合逻辑 | 独立时间轴 |
| 可扩展性 | 困难 | 策略模式，易扩展 |
| 代码复杂度 | 高 | 简化约100行 |

### 核心改进

✅ **移除BilingualSyncStrategy**: 消除了语言决定显示模式的不合理设计
✅ **独立时间轴**: main_timeline和aux_timeline彼此独立
✅ **智能布局**: 只在layout层面处理重叠关系
✅ **代码简化**: 移除约100行复杂的耦合代码
✅ **向后兼容**: 保持旧版接口完全可用

## 📈 未来扩展

- [ ] **卡拉OK模式**: 逐字高亮显示策略
- [ ] **3D效果**: 立体文字和动画效果
- [ ] **实时预览**: GUI界面和实时预览功能
- [ ] **模板系统**: 预设样式模板库
- [ ] **性能优化**: 并行渲染和缓存机制
- [ ] **云端处理**: 分布式视频生成服务

## 📚 相关文档

- [详细设计文档](local_docs/README.md)
- [API快速参考](local_docs/quick_reference.md)
- [架构设计说明](local_docs/lyric_timeline_design.md)
- [重构总结报告](ai_memory/lyric_timeline_refactoring_plan.md)

## 📝 许可证

本项目为开源项目，基于MIT许可证，仅供学习和研究使用。

## 🙏 致谢

- **MoviePy**: 强大的视频处理库
- **Pillow**: 图像处理支持
- **PyYAML**: 配置文件解析
- **精武英雄**: 示例音乐作品

## 🎯 快速开始

```bash
# 克隆项目
git clone <repository-url>
cd jingwu-hero

# 设置环境
conda create -n lyrc-mv python=3.12
conda activate lyrc-mv
pip install moviepy pillow numpy pyyaml

# 运行示例
python enhanced_generator.py
```

---

**🎵 开始创建您的专业歌词视频吧！** ✨

> 基于现代化OOP架构，支持双语智能布局的专业歌词视频生成工具
