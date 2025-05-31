"""
精武英雄歌词视频生成器 - 增强版（重构修复终版）
支持背景图片、发光效果和双语模式
"""

import os
import time
from typing import List, Optional
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import traceback
from pathlib import Path
from lrc_mv_config import load_lrc_mv_config

# 导入LyricTimeline相关类
from lyric_timeline import LyricTimeline, LyricDisplayMode
from layout_engine import LayoutEngine, VerticalStackStrategy
from lyric_clip import LyricClip, create_lyric_clip

DEFAULT_WIDTH = 720
DEFAULT_HEIGHT = 1280
DEFAULT_FPS = 24

class EnhancedJingwuGenerator:
    """增强版精武英雄歌词视频生成器（重构修复终版）"""

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT, fps: int = DEFAULT_FPS):
        self.width = width
        self.height = height
        self.fps = fps
        self.default_font_size = 80
        self.default_font_color = 'white'
        self.highlight_color = '#FFD700'  # 金色
        self.shadow_color = (0, 0, 0, 200)

        self.theme_colors = {
            'gold': '#FFD700',
            'red': '#DC143C',
            'dark_red': '#8B0000',
            'black': '#000000',
            'white': '#FFFFFF',
            'silver': '#C0C0C0'
        }





    def load_background_image(self, bg_path: str) -> Optional[np.ndarray]:
        """加载并处理背景图片"""
        try:
            img = Image.open(bg_path)
            # PIL版本兼容性处理
            try:
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
            except AttributeError:
                # 较旧的PIL版本回退
                img = img.resize((self.width, self.height))

            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.4)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(0.6)
            img = img.filter(ImageFilter.GaussianBlur(radius=1))
            return np.array(img)
        except Exception as e:
            print(f"⚠️  背景图片加载失败: {e}")
            return None

    def create_gradient_background(self, color1: tuple, color2: tuple) -> np.ndarray:
        """创建渐变背景"""
        gradient = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for y in range(self.height):
            ratio = y / self.height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            gradient[y, :] = [r, g, b]
        return gradient

    # create_enhanced_text_image方法已移除
    # 新的LyricClip架构使用统一的frame_function渲染管道
    # 文本渲染现在通过lyric_clip.py中的LyricClip._render_lyric_on_frame()处理

    # create_lyric_clip_with_animation方法已移除
    # 新的LyricClip架构不再需要为每句歌词创建单独的ImageClip
    # 所有歌词渲染现在通过LyricClip的统一frame_function处理

    def create_lyric_clip(self, timelines: List[LyricTimeline],
                         duration: float) -> LyricClip:
        """创建LyricClip（新方式）

        Args:
            timelines: 歌词时间轴列表
            duration: 视频时长

        Returns:
            LyricClip实例
        """
        # 创建布局引擎
        layout_engine = LayoutEngine(VerticalStackStrategy(spacing=30))

        # 添加所有时间轴
        for timeline in timelines:
            layout_engine.add_element(timeline)

        # 创建LyricClip
        return create_lyric_clip(
            timelines=timelines,
            layout_engine=layout_engine,
            size=(self.width, self.height),
            duration=duration,
            fps=self.fps
        )

    def _generate_video_with_lyric_clip(self, lyric_clip: LyricClip,
                                       background_clip, audio_clip,
                                       output_path: str, draft_mode: bool = False):
        """使用LyricClip的视频生成方法

        Args:
            lyric_clip: LyricClip实例
            background_clip: 背景片段
            audio_clip: 音频片段
            output_path: 输出路径
            draft_mode: 草稿模式
        """
        print("使用LyricClip合成视频...")

        # 合成视频（背景 + LyricClip）
        all_clips = [background_clip, lyric_clip]

        # 使用现有的合成和导出逻辑
        self._finalize_and_export_video(
            all_clips=all_clips,
            audio_clip=audio_clip,
            output_path=output_path,
            temp_audio_file_suffix="lyric_clip",
            draft_mode=draft_mode
        )

    def _apply_layout_to_timeline(self, timeline: 'LyricTimeline', target_rect):
        """将布局结果应用到时间轴

        根据目标矩形调整时间轴的显示策略参数
        """
        from lyric_timeline import LyricDisplayMode

        if timeline.display_mode == LyricDisplayMode.SIMPLE_FADE:
            # 对于简单模式，调整Y位置
            timeline.set_display_mode(
                LyricDisplayMode.SIMPLE_FADE,
                y_position=target_rect.y + target_rect.height // 2,
                is_highlighted=getattr(timeline._strategy, 'is_highlighted', False)
            )
        elif timeline.display_mode == LyricDisplayMode.ENHANCED_PREVIEW:
            # 对于增强预览模式，调整偏移量
            center_y = target_rect.y + target_rect.height // 2
            timeline.set_display_mode(
                LyricDisplayMode.ENHANCED_PREVIEW,
                current_y_offset=center_y - self.height // 2 - 50,
                preview_y_offset=center_y - self.height // 2 + 80
            )

        print(f"  已应用布局到 {timeline.element_id}: Y={target_rect.y}, H={target_rect.height}")

    def _validate_clips_duration(self, clips: List[ImageClip], max_duration: float) -> List[ImageClip]:
        """验证并修正片段时长，确保所有片段都在时长限制内

        Args:
            clips: 待验证的片段列表
            max_duration: 最大时长限制

        Returns:
            验证并修正后的片段列表
        """
        validated_clips = []

        for clip in clips:
            start_time = getattr(clip, 'start', 0)
            duration = getattr(clip, 'duration', 0)

            # 检查片段是否超出时长限制
            if start_time >= max_duration:
                print(f"   移除超出时长限制的片段: start={start_time:.2f}s >= {max_duration:.2f}s")
                continue

            if start_time + duration > max_duration:
                # 裁剪片段以符合时长限制
                new_duration = max_duration - start_time
                if new_duration > 0.01:  # 只保留有意义的片段
                    clip = clip.subclipped(0, new_duration)
                    print(f"   裁剪片段时长: {duration:.2f}s -> {new_duration:.2f}s")
                    validated_clips.append(clip)
                else:
                    print(f"   移除过短的片段: duration={new_duration:.2f}s")
            else:
                validated_clips.append(clip)

        return validated_clips

    # --- BEGIN PRIVATE HELPER METHODS ---
    def _create_video_background(
        self,
        duration: float,
        background_image_path: Optional[str] = None
    ) -> ImageClip:
        """(Helper) 创建视频背景片段（图片或纯黑）。"""
        if background_image_path and os.path.exists(background_image_path):
            bg_array = self.load_background_image(background_image_path)
            if bg_array is not None:
                print(f"   使用背景图片: {background_image_path}")
                return ImageClip(bg_array, duration=duration)
            else:
                print("   背景图片加载失败，使用纯黑背景替代。")
                return ColorClip(size=(self.width, self.height), color=(0,0,0), duration=duration)
        else:
            if background_image_path:
                print(f"   背景图片路径不存在: {background_image_path}。使用纯黑背景。")
            else:
                print("   未使用背景图片，使用纯黑背景。")
            return ColorClip(size=(self.width, self.height), color=(0,0,0), duration=duration)



    def _finalize_and_export_video(
        self,
        all_clips: List[ImageClip],
        audio_clip: AudioFileClip,
        output_path: str,
        temp_audio_file_suffix: str = "generic",
        ffmpeg_params_custom: Optional[List[str]] = None,
        draft_mode: bool = False
    ):
        """(Helper) 合成所有片段并导出视频。

        Args:
            all_clips: 所有视频片段
            audio_clip: 音频片段
            output_path: 输出路径
            temp_audio_file_suffix: 临时音频文件后缀
            ffmpeg_params_custom: 自定义FFmpeg参数
            draft_mode: 草稿模式，使用快速编码设置
        """
        print("合成视频...")
        final_video = CompositeVideoClip(all_clips)
        final_video = final_video.with_audio(audio_clip)
        final_video = final_video.with_fps(self.fps)

        temp_audio_filename = f'temp-audio-{temp_audio_file_suffix}-{hash(output_path) % 10000}.m4a'

        # 根据模式选择编码配置
        if draft_mode:
            print("   🚀 使用草稿质量配置进行快速编码...")
            codec_to_use = 'h264_nvenc'  # 优先使用NVENC硬件编码
            preset_to_use = 'fast'
            actual_ffmpeg_params = ffmpeg_params_custom if ffmpeg_params_custom is not None else ['-cq', '28']
        else:
            print("   🎬 使用产品质量配置进行编码...")
            codec_to_use = 'libx264rgb'
            preset_to_use = 'medium'
            actual_ffmpeg_params = ffmpeg_params_custom if ffmpeg_params_custom is not None else ['-crf', '18']

        print(f"导出视频到: {output_path}")
        print(f"   编码器: {codec_to_use}, 预设: {preset_to_use}, 参数: {actual_ffmpeg_params}")

        # 开始计时
        export_start_time = time.perf_counter()

        try:
            final_video.write_videofile(
                output_path,
                codec=codec_to_use,
                audio_codec='aac',
                temp_audiofile=temp_audio_filename,
                remove_temp=True,
                # verbose=False,
                logger=None,
                preset=preset_to_use,
                ffmpeg_params=actual_ffmpeg_params
            )
        except Exception as e:
            # 草稿模式下NVENC失败时快速回退到软件编码
            if draft_mode and codec_to_use == "h264_nvenc":
                print(f"⚠️  NVENC编码失败 ({e})，回退到软件编码...")
                final_video.write_videofile(
                    output_path,
                    codec='libx264rgb',
                    audio_codec='aac',
                    temp_audiofile=temp_audio_filename,
                    remove_temp=True,
                    # verbose=False,
                    logger=None,
                    preset='ultrafast',
                    ffmpeg_params=['-crf', '28']
                )
            else:
                raise
        finally:
            # 结束计时并显示结果
            export_end_time = time.perf_counter()
            export_duration = export_end_time - export_start_time
            mode_desc = "草稿模式" if draft_mode else "产品模式"
            print(f"✅ 视频导出完成 ({mode_desc}): {export_duration:.2f} 秒")
    # --- END PRIVATE HELPER METHODS ---


    def generate_bilingual_video(self,
                               main_timeline: 'LyricTimeline',
                               aux_timeline: Optional['LyricTimeline'] = None,
                               audio_path: str = "",
                               output_path: str = "",
                               background_image: Optional[str] = None,
                               t_max_sec: float = float('inf'),
                               draft_mode: bool = False) -> bool:
        """生成双语版本视频或增强版视频 (纯OOP版)

        Args:
            main_timeline: 主歌词时间轴
            aux_timeline: 副歌词时间轴（可选，用于双语模式）
            audio_path: 音频文件路径
            output_path: 输出视频路径
            background_image: 背景图片路径（可选）
            t_max_sec: 最大时长限制
            draft_mode: 草稿模式，使用快速编码设置（开发测试用）

        Returns:
            bool: 生成是否成功
        """
        """使用LyricTimeline对象生成视频的核心方法"""

        # 确定生成模式
        is_bilingual_mode = aux_timeline is not None
        mode_name = "双语版" if is_bilingual_mode else "增强版"

        try:
            print(f"开始生成{mode_name}: {output_path}")

            # 音频处理（保持原有逻辑）
            print("加载音频...")
            audio = AudioFileClip(audio_path)
            original_duration = audio.duration
            duration = min(original_duration, t_max_sec)

            if t_max_sec < original_duration:
                audio = audio.subclipped(0, t_max_sec)
                print(f"   音频已裁剪: {original_duration:.1f}s -> {duration:.1f}s")
            else:
                print(f"   音频时长: {duration:.1f} 秒")

            # 显示时间轴信息
            print(f"主时间轴信息: {main_timeline.get_info()}")
            if aux_timeline:
                print(f"副时间轴信息: {aux_timeline.get_info()}")

            # 布局计算和冲突检测 - 统一使用布局引擎
            print("使用布局引擎进行自动布局...")

            # 创建布局引擎作为默认的timeline容器
            layout_engine = LayoutEngine(VerticalStackStrategy(spacing=30))

            # 添加所有时间轴元素
            layout_engine.add_element(main_timeline)
            if aux_timeline:
                layout_engine.add_element(aux_timeline)

            # 检测冲突
            conflicts = layout_engine.detect_conflicts(self.width, self.height)
            if conflicts:
                print("检测到布局冲突:")
                for conflict in conflicts:
                    print(f"  - {conflict}")

                # 计算自动布局
                layout_result = layout_engine.calculate_layout(self.width, self.height)
                print("应用自动布局解决方案:")

                # 应用布局结果到时间轴
                for element_id, rect in layout_result.element_positions.items():
                    print(f"  - {element_id}: {rect}")

                    # 根据element_id找到对应的timeline并更新其策略
                    if element_id == main_timeline.element_id:
                        self._apply_layout_to_timeline(main_timeline, rect)
                    elif aux_timeline and element_id == aux_timeline.element_id:
                        self._apply_layout_to_timeline(aux_timeline, rect)
            else:
                print("✅ 无布局冲突，使用原始布局")

            # 显示所有时间轴的布局信息
            layout_result = layout_engine.calculate_layout(self.width, self.height)
            for element_id, rect in layout_result.element_positions.items():
                print(f"时间轴 {element_id} 布局区域: {rect}")

            # 背景处理（保持原有逻辑）
            print("创建背景...")
            background_clip = self._create_video_background(duration, background_image)

            # 使用新的LyricClip统一渲染管道
            print("创建LyricClip统一渲染容器...")

            # 收集所有时间轴
            timelines = []
            for element in layout_engine.elements:
                timelines.append(element)

            # 创建LyricClip（新方式）
            lyric_clip = self.create_lyric_clip(timelines, duration)
            print(f"   ✅ LyricClip创建成功，包含 {len(timelines)} 个时间轴")

            # 使用LyricClip进行视频合成（新方式）
            self._generate_video_with_lyric_clip(
                lyric_clip=lyric_clip,
                background_clip=background_clip,
                audio_clip=audio,
                output_path=output_path,
                draft_mode=draft_mode
            )

            print(f"{mode_name}视频生成成功！")
            return True

        except Exception as e:
            print(f"{mode_name}生成失败: {e}")
            traceback.print_exc()
            return False

def demo_enhanced_features(config_path: Path, t_max_sec: float = float('inf'), draft_mode: bool = False):
    """使用配置文件生成歌词视频 (纯OOP版)

    Args:
        config_path: 配置文件路径
        t_max_sec: 最大时长限制
        draft_mode: 草稿模式，使用快速编码设置（开发测试用）
    """
    print("精武英雄歌词视频生成器 - 纯OOP版")
    print("=" * 50)

    try:
        # 加载配置文件
        print(f"加载配置文件: {config_path}")
        config = load_lrc_mv_config(str(config_path))
        print("配置文件加载成功")

        # 显示配置信息
        print(f"   音频文件: {config.audio}")
        print(f"   主歌词: {config.main_lrc.path} ({config.main_lrc.lang})")
        if config.aux_lrc:
            print(f"   副歌词: {config.aux_lrc.path} ({config.aux_lrc.lang})")
        print(f"   背景图片: {config.background}")
        print(f"   输出尺寸: {config.width}x{config.height}")
        print(f"   输出文件: {config.output}")

        # 验证文件存在性
        print("\n验证文件存在性...")
        config.validate_files()
        print("所有必需文件都存在")

    except Exception as e:
        print(f"配置加载失败: {e}")
        return False

    # 创建生成器，使用配置文件中的尺寸
    generator = EnhancedJingwuGenerator(width=config.width, height=config.height, fps=DEFAULT_FPS)
    generator.default_font_size = 60
    print("\n开始生成视频...")

    # 获取路径
    audio_path = config.get_audio_path()
    background_path = config.get_background_path()
    output_path = config.get_output_path()

    # 使用LyricTimeline OOP接口
    print("使用LyricTimeline OOP接口")

    # 创建主时间轴 - 总是使用增强预览模式
    main_lrc_path = config.get_main_lrc_path()

    # 从配置中获取字体大小，如果没有指定则使用默认值
    main_font_size = config.main_lrc.font_size or 80
    print(f"主歌词字体大小: {main_font_size}")
    from layout_types import LyricStyle
    main_style = LyricStyle(
        font_size=main_font_size,
        highlight_color='#FFD700',
        glow_enabled=True
    )

    main_timeline = LyricTimeline.from_lrc_file(
        str(main_lrc_path),
        language="chinese",
        display_mode=LyricDisplayMode.ENHANCED_PREVIEW,
        style=main_style
    )

    aux_timeline = None
    if config.aux_lrc:
        # 创建副时间轴 - 使用简单模式，显示在下方
        aux_lrc_path = config.get_aux_lrc_path()

        # 从配置中获取副歌词字体大小，如果没有指定则使用默认值
        aux_font_size = config.aux_lrc.font_size or 60
        print(f"副歌词字体大小: {aux_font_size}")
        aux_style = LyricStyle(
            font_size=aux_font_size,
            font_color='white',
            highlight_color='#FFD700'
        )

        aux_timeline = LyricTimeline.from_lrc_file(
            str(aux_lrc_path),
            language="english",
            display_mode=LyricDisplayMode.SIMPLE_FADE,
            style=aux_style
        )
        # 设置副歌词显示位置，避免与主歌词重叠
        aux_timeline.set_display_mode(
            LyricDisplayMode.SIMPLE_FADE,
            y_position=config.height // 2 + 200,  # 显示在更下方，避免重叠
            is_highlighted=False
        )

    # 显示时间轴信息
    print(f"主时间轴信息: {main_timeline.get_info()}")
    if aux_timeline:
        print(f"副时间轴信息: {aux_timeline.get_info()}")

    # 计算布局信息
    main_rect = main_timeline.calculate_required_rect(config.width, config.height)
    print(f"主时间轴所需区域: {main_rect}")

    if aux_timeline:
        aux_rect = aux_timeline.calculate_required_rect(config.width, config.height)
        print(f"副时间轴所需区域: {aux_rect}")

        if main_rect.overlaps_with(aux_rect):
            print("警告: 时间轴显示区域重叠，可能需要调整布局")

    # 生成视频
    success = generator.generate_bilingual_video(
        main_timeline=main_timeline,
        aux_timeline=aux_timeline,
        audio_path=str(audio_path),
        output_path=str(output_path),
        background_image=str(background_path),
        t_max_sec=t_max_sec,
        draft_mode=draft_mode
    )

    if success:
        print("\n视频生成成功！")
        print(f"输出文件: {output_path}")
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.1f} MB")
    else:
        print("\n视频生成失败！")

    return success

def demo_draft_mode(config_path: Path, t_max_sec: float = float('inf')):
    """草稿模式演示 - 快速生成用于开发测试"""
    print("🚀 草稿模式演示 - 快速编码")
    print("=" * 50)
    print("注意: 草稿模式使用快速编码设置，质量较低但速度更快，适合开发测试使用")
    print()

    return demo_enhanced_features(config_path, t_max_sec, draft_mode=True)

if __name__ == "__main__":
    # 默认使用草稿模式进行快速测试
    # demo_draft_mode(Path(r"精武英雄\lrc-mv.yaml"), t_max_sec=20.0)

    # 如需产品质量，取消注释下面这行
    demo_enhanced_features(Path(r"精武英雄\lrc-mv.yaml"))
