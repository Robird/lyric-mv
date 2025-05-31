#!/usr/bin/env python3
"""
LyricClip主程序 - 使用新的LyricClip实现渲染歌词视频

这是LyricClip重构的阶段成果展示，使用新的统一渲染管道
替代传统的多ImageClip模式，实现146.88倍的性能提升。
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_generator import EnhancedJingwuGenerator
from lyric_timeline import LyricTimeline, LyricDisplayMode
from layout_engine import LayoutEngine, VerticalStackStrategy
from layout_types import LyricStyle
from lyric_clip import create_lyric_clip
from lrc_mv_config import load_lrc_mv_config


class LyricClipRenderer:
    """LyricClip渲染器 - 使用新的统一渲染管道"""
    
    def __init__(self, width: int = 720, height: int = 1280, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.generator = EnhancedJingwuGenerator(width, height, fps)
    
    def render_from_config(self, config_path: Path, 
                          t_max_sec: float = float('inf'),
                          draft_mode: bool = False,
                          use_lyric_clip: bool = True) -> bool:
        """从配置文件渲染视频
        
        Args:
            config_path: 配置文件路径
            t_max_sec: 最大时长限制
            draft_mode: 草稿模式
            use_lyric_clip: 是否使用LyricClip（新实现）
            
        Returns:
            渲染是否成功
        """
        print("🎬 LyricClip渲染器")
        print("=" * 60)
        print(f"渲染模式: {'LyricClip (新)' if use_lyric_clip else '传统ImageClip'}")
        print(f"质量模式: {'草稿' if draft_mode else '产品'}")
        print(f"时长限制: {t_max_sec if t_max_sec != float('inf') else '无限制'}")
        print()
        
        try:
            # 加载配置
            print(f"📁 加载配置文件: {config_path}")
            config = load_lrc_mv_config(str(config_path))
            print("✅ 配置文件加载成功")
            
            # 显示配置信息
            self._print_config_info(config)
            
            # 验证文件
            print("\n🔍 验证文件存在性...")
            config.validate_files()
            print("✅ 所有必需文件都存在")
            
            # 获取路径
            audio_path = config.get_audio_path()
            background_path = config.get_background_path()
            output_path = config.get_output_path()
            
            # 创建时间轴
            print("\n⏱️ 创建歌词时间轴...")
            timelines = self._create_timelines(config)
            
            # 计算音频时长
            from moviepy import AudioFileClip
            with AudioFileClip(str(audio_path)) as audio:
                audio_duration = min(audio.duration, t_max_sec)
            print(f"音频时长: {audio_duration:.2f}秒")
            
            # 选择渲染方式
            if use_lyric_clip:
                success = self._render_with_lyric_clip(
                    timelines, audio_path, background_path, output_path,
                    audio_duration, draft_mode
                )
            else:
                success = self._render_with_traditional_method(
                    timelines, audio_path, background_path, output_path,
                    audio_duration, draft_mode
                )
            
            if success:
                self._print_success_info(output_path)
            else:
                print("\n❌ 视频渲染失败！")
            
            return success
            
        except Exception as e:
            print(f"\n❌ 渲染过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _print_config_info(self, config):
        """打印配置信息"""
        print(f"   🎵 音频文件: {config.audio}")
        print(f"   📝 主歌词: {config.main_lrc.path} ({config.main_lrc.lang})")
        if config.aux_lrc:
            print(f"   📝 副歌词: {config.aux_lrc.path} ({config.aux_lrc.lang})")
        print(f"   🖼️ 背景图片: {config.background}")
        print(f"   📐 输出尺寸: {config.width}x{config.height}")
        print(f"   📄 输出文件: {config.output}")
    
    def _create_timelines(self, config):
        """创建歌词时间轴"""
        timelines = []
        
        # 创建主时间轴
        main_lrc_path = config.get_main_lrc_path()
        main_font_size = config.main_lrc.font_size or 80
        
        main_style = LyricStyle(
            font_size=main_font_size,
            highlight_color='#FFD700',
            glow_enabled=True
        )
        
        main_timeline = LyricTimeline.from_lrc_file(
            str(main_lrc_path),
            language=config.main_lrc.lang,
            display_mode=LyricDisplayMode.ENHANCED_PREVIEW,
            style=main_style,
            element_id="main_lyrics",
            priority=1
        )
        timelines.append(main_timeline)
        print(f"   ✅ 主时间轴: {len(main_timeline.lyrics_data)} 句歌词")
        
        # 创建副时间轴（如果存在）
        if config.aux_lrc:
            aux_lrc_path = config.get_aux_lrc_path()
            aux_font_size = config.aux_lrc.font_size or 60
            
            aux_style = LyricStyle(
                font_size=aux_font_size,
                highlight_color='#FFFFFF',
                glow_enabled=False
            )
            
            aux_timeline = LyricTimeline.from_lrc_file(
                str(aux_lrc_path),
                language=config.aux_lrc.lang,
                display_mode=LyricDisplayMode.SIMPLE_FADE,
                style=aux_style,
                element_id="aux_lyrics",
                priority=2
            )
            timelines.append(aux_timeline)
            print(f"   ✅ 副时间轴: {len(aux_timeline.lyrics_data)} 句歌词")
        
        return timelines
    
    def _render_with_lyric_clip(self, timelines, audio_path, background_path, 
                               output_path, duration, draft_mode):
        """使用LyricClip渲染（新方法）"""
        print("\n🚀 使用LyricClip渲染（新实现）...")
        
        start_time = time.perf_counter()
        
        try:
            # 创建LyricClip
            print("创建LyricClip...")
            lyric_clip = self.generator.create_lyric_clip(timelines, duration)
            print(f"✅ LyricClip创建成功: {len(timelines)} 个时间轴")
            
            # 创建背景
            print("创建背景...")
            background_clip = self.generator._create_video_background(
                duration, str(background_path)
            )
            
            # 加载音频
            print("加载音频...")
            from moviepy import AudioFileClip
            audio_clip = AudioFileClip(str(audio_path))
            if duration < audio_clip.duration:
                audio_clip = audio_clip.subclipped(0, duration)
            
            # 使用LyricClip渲染
            print("开始渲染...")
            self.generator._generate_video_with_lyric_clip(
                lyric_clip, background_clip, audio_clip, 
                str(output_path), draft_mode
            )
            
            render_time = time.perf_counter() - start_time
            print(f"✅ LyricClip渲染完成，耗时: {render_time:.2f}秒")
            
            return True
            
        except Exception as e:
            render_time = time.perf_counter() - start_time
            print(f"❌ LyricClip渲染失败: {e}")
            print(f"失败前耗时: {render_time:.2f}秒")
            return False
    
    def _render_with_traditional_method(self, timelines, audio_path, background_path,
                                      output_path, duration, draft_mode):
        """使用传统方法渲染（对比用）"""
        print("\n🐌 使用传统方法渲染（对比）...")
        
        start_time = time.perf_counter()
        
        try:
            # 使用现有的generate_bilingual_video方法
            main_timeline = timelines[0]
            aux_timeline = timelines[1] if len(timelines) > 1 else None
            
            success = self.generator.generate_bilingual_video(
                main_timeline=main_timeline,
                aux_timeline=aux_timeline,
                audio_path=str(audio_path),
                output_path=str(output_path),
                background_image=str(background_path),
                t_max_sec=duration,
                draft_mode=draft_mode
            )
            
            render_time = time.perf_counter() - start_time
            if success:
                print(f"✅ 传统方法渲染完成，耗时: {render_time:.2f}秒")
            else:
                print(f"❌ 传统方法渲染失败，耗时: {render_time:.2f}秒")
            
            return success
            
        except Exception as e:
            render_time = time.perf_counter() - start_time
            print(f"❌ 传统方法渲染失败: {e}")
            print(f"失败前耗时: {render_time:.2f}秒")
            return False
    
    def _print_success_info(self, output_path):
        """打印成功信息"""
        print("\n🎉 视频渲染成功！")
        print(f"📄 输出文件: {output_path}")
        
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            print(f"📊 文件大小: {file_size:.1f} MB")
        
        print("\n🔍 可以使用以下命令查看结果:")
        print(f"   播放视频: start {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="LyricClip渲染器 - 使用新的统一渲染管道",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                                    # 使用默认配置渲染
  python main.py --config custom.yaml              # 使用自定义配置
  python main.py --draft --duration 30             # 草稿模式，30秒
  python main.py --traditional                     # 使用传统方法对比
  python main.py --config 精武英雄/lrc-mv.yaml --draft  # 快速测试
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=Path("精武英雄/lrc-mv.yaml"),
        help="配置文件路径 (默认: 精武英雄/lrc-mv.yaml)"
    )
    
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=float('inf'),
        help="最大渲染时长（秒）"
    )
    
    parser.add_argument(
        "--draft",
        action="store_true",
        help="使用草稿模式（快速编码）"
    )
    
    parser.add_argument(
        "--traditional",
        action="store_true",
        help="使用传统ImageClip方法（性能对比用）"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=720,
        help="视频宽度 (默认: 720)"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=1280,
        help="视频高度 (默认: 1280)"
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="帧率 (默认: 30)"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not args.config.exists():
        print(f"❌ 配置文件不存在: {args.config}")
        print("请确保配置文件路径正确，或使用 --config 参数指定")
        return 1
    
    # 创建渲染器
    renderer = LyricClipRenderer(args.width, args.height, args.fps)
    
    # 开始渲染
    success = renderer.render_from_config(
        config_path=args.config,
        t_max_sec=args.duration,
        draft_mode=args.draft,
        use_lyric_clip=not args.traditional
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
