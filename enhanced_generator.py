"""
精武英雄歌词视频生成器 - 增强版（重构修复终版）
支持背景图片、发光效果和双语模式
"""

import os
import re
from typing import List, Tuple, Optional, Union
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import traceback
from pathlib import Path
from lrc_mv_config import LrcMvConfig, load_lrc_mv_config

# 导入LyricTimeline相关类
try:
    from lyric_timeline import (
        LyricTimeline,
        LyricDisplayMode,
        LyricStyle,
        LyricRect,
        create_enhanced_timeline,
        create_simple_timeline,
        create_bilingual_timelines
    )
    LYRIC_TIMELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  LyricTimeline模块导入失败: {e}")
    print("   将使用传统模式，部分新功能不可用")
    LYRIC_TIMELINE_AVAILABLE = False
    # 定义占位符类型以避免类型错误
    LyricTimeline = None
    LyricDisplayMode = None
    LyricStyle = None
    LyricRect = None

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

    def parse_lrc_file(self, lrc_path: str) -> List[Tuple[float, str]]:
        """解析LRC歌词文件"""
        lyrics = []
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
                if text:
                    lyrics.append((timestamp, text))
        return sorted(lyrics, key=lambda x: x[0])

    # ============================================================================
    # LyricTimeline集成方法
    # ============================================================================

    def _convert_to_timeline(self, lyrics_data: List[Tuple[float, str]],
                            language: str, display_mode: str,
                            animation_style: str = 'fade') -> 'LyricTimeline':
        """将旧格式的歌词数据转换为LyricTimeline对象

        Args:
            lyrics_data: 歌词数据列表
            language: 语言标识
            display_mode: 显示模式字符串
            animation_style: 动画样式

        Returns:
            LyricTimeline对象
        """
        if not LYRIC_TIMELINE_AVAILABLE:
            raise RuntimeError("LyricTimeline模块不可用，无法进行转换")

        # 创建样式配置
        style = LyricStyle(
            font_size=self.default_font_size,
            font_color=self.default_font_color,
            highlight_color=self.highlight_color,
            shadow_color=self.shadow_color,
            glow_enabled=(language in ['chinese', 'main']),
            animation_style=animation_style
        )

        # 根据显示模式字符串转换为枚举
        if display_mode == "enhanced_preview":
            mode = LyricDisplayMode.ENHANCED_PREVIEW
        elif display_mode == "bilingual_sync":
            mode = LyricDisplayMode.BILINGUAL_SYNC
        else:
            mode = LyricDisplayMode.SIMPLE_FADE

        timeline = LyricTimeline(
            lyrics_data=lyrics_data,
            language=language,
            style=style,
            display_mode=mode
        )

        # 根据模式设置策略参数
        if mode == LyricDisplayMode.ENHANCED_PREVIEW:
            timeline.set_display_mode(
                LyricDisplayMode.ENHANCED_PREVIEW,
                current_y_offset=-50,
                preview_y_offset=80
            )
        elif mode == LyricDisplayMode.BILINGUAL_SYNC:
            if language in ['chinese', 'main']:
                timeline.set_display_mode(
                    LyricDisplayMode.BILINGUAL_SYNC,
                    main_y_offset=-80,
                    aux_y_offset=60
                )
            else:
                timeline.set_display_mode(
                    LyricDisplayMode.BILINGUAL_SYNC,
                    main_y_offset=-80,
                    aux_y_offset=60
                )

        return timeline

    def create_enhanced_video_timeline(self, lyrics_data: List[Tuple[float, str]],
                                     language: str = "chinese") -> 'LyricTimeline':
        """快速创建增强模式时间轴"""
        if not LYRIC_TIMELINE_AVAILABLE:
            raise RuntimeError("LyricTimeline模块不可用")

        return self._convert_to_timeline(
            lyrics_data, language, "enhanced_preview", "fade"
        )

    def create_simple_video_timeline(self, lyrics_data: List[Tuple[float, str]],
                                   language: str = "english") -> 'LyricTimeline':
        """快速创建简单模式时间轴"""
        if not LYRIC_TIMELINE_AVAILABLE:
            raise RuntimeError("LyricTimeline模块不可用")

        return self._convert_to_timeline(
            lyrics_data, language, "simple_fade", "fade"
        )

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

    def create_enhanced_text_image(self, text: str, font_size: int, color: str,
                                 width: int, height: int, y_position: int,
                                 glow: bool = False) -> np.ndarray:
        """创建增强文字图像，支持发光效果"""
        scale = 2
        scaled_width = width * scale
        scaled_height = height * scale
        scaled_font_size = font_size * scale

        img = Image.new('RGBA', (scaled_width, scaled_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
            if has_chinese:
                font = ImageFont.truetype("simsun.ttc", scaled_font_size)
            else:
                try:
                    font = ImageFont.truetype("arial.ttf", scaled_font_size)
                except OSError:
                    try:
                        font = ImageFont.truetype("calibri.ttf", scaled_font_size)
                    except OSError:
                        font = ImageFont.load_default()
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (scaled_width - text_width) // 2
        y = y_position * scale - text_height // 2

        if glow and color == '#FFD700':
            for offset in range(8, 0, -1):
                for dx in range(-offset, offset + 1):
                    for dy in range(-offset, offset + 1):
                        if dx * dx + dy * dy <= offset * offset:
                            alpha = max(0, 120 - offset * 15)
                            glow_rgba = (255, 215, 0, alpha)
                            draw.text((x + dx, y + dy), text, fill=glow_rgba, font=font)

        shadow_color_val = (0, 0, 0, 200)
        draw.text((x + 3 * scale, y + 3 * scale), text, fill=shadow_color_val, font=font)

        main_color = (255, 215, 0, 255) if color == '#FFD700' else (255, 255, 255, 255)
        draw.text((x, y), text, fill=main_color, font=font)

        # PIL版本兼容性处理
        try:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        except AttributeError:
            # 较旧的PIL版本回退
            img = img.resize((width, height))

        return np.array(img)

    def create_lyric_clip_with_animation(self, text: str, start_time: float, duration: float,
                                       is_highlighted: bool = False, y_position: Optional[int] = None,
                                       animation: str = 'fade') -> ImageClip:
        """创建带动画效果的歌词片段"""
        if y_position is None:
            y_position = self.height // 2

        font_size = self.default_font_size if is_highlighted else self.default_font_size - 20
        color = self.highlight_color if is_highlighted else self.default_font_color

        text_img_array = self.create_enhanced_text_image(
            text, font_size, color, self.width, self.height, y_position,
            glow=is_highlighted
        )

        clip = ImageClip(text_img_array, duration=duration)
        clip = clip.set_start(start_time)
          # 简化动画效果以避免渲染问题
        if animation == 'fade':
            if duration > 0.6:
                clip = clip.crossfadein(0.3).crossfadeout(0.3)
        elif animation == 'slide':
            clip = clip.set_position(lambda t: (-self.width + int(t * self.width / 0.5), 'center') if t < 0.5 else ('center', 'center'))
        # 暂时禁用zoom动画以避免PIL兼容性问题
        # elif animation == 'zoom':
        #     if is_highlighted:
        #         clip = clip.resize(lambda t: 0.8 + 0.2 * min(t / 0.3, 1))

        return clip

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

    def _generate_lyric_clips(
        self,
        lyrics_list: List[Tuple[float, str]],
        total_video_duration: float,
        y_position: int,
        is_highlighted: bool,
        animation_style: str = 'fade'
    ) -> List[ImageClip]:
        """(Helper) 为单个语言的歌词列表生成视频片段列表。"""
        clips = []
        for i, (start_time, text) in enumerate(lyrics_list):
            if i < len(lyrics_list) - 1:
                end_time = lyrics_list[i + 1][0]
            else:
                end_time = total_video_duration

            lyric_duration = end_time - start_time
            if lyric_duration <= 0.01:
                print(f"   跳过歌词（时长过短 {lyric_duration:.2f}s）: '{text}'")
                continue

            lyric_clip = self.create_lyric_clip_with_animation(
                text, start_time, lyric_duration,
                is_highlighted=is_highlighted,
                y_position=y_position,
                animation=animation_style
            )
            clips.append(lyric_clip)
        return clips

    def _finalize_and_export_video(
        self,
        all_clips: List[ImageClip],
        audio_clip: AudioFileClip,
        output_path: str,
        temp_audio_file_suffix: str = "generic",
        ffmpeg_params_custom: Optional[List[str]] = None
    ):
        """(Helper) 合成所有片段并导出视频。"""
        print("合成视频...")
        final_video = CompositeVideoClip(all_clips)
        final_video = final_video.set_audio(audio_clip)
        final_video = final_video.set_fps(self.fps)

        temp_audio_filename = f'temp-audio-{temp_audio_file_suffix}-{hash(output_path) % 10000}.m4a'

        actual_ffmpeg_params = ffmpeg_params_custom if ffmpeg_params_custom is not None else ['-crf', '18']

        print(f"导出视频到: {output_path}")
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=temp_audio_filename,
            remove_temp=True,
            verbose=False,
            logger=None,
            preset='medium',
            ffmpeg_params=actual_ffmpeg_params        )
    # --- END PRIVATE HELPER METHODS ---


    def generate_bilingual_video(self,
                               main_lyrics: Union[List[Tuple[float, str]], 'LyricTimeline', None] = None,
                               aux_lyrics: Union[List[Tuple[float, str]], 'LyricTimeline', None] = None,
                               audio_path: str = "", output_path: str = "",
                               background_image: Optional[str] = None,
                               animation_style: str = 'fade',
                               t_max_sec: float = float('inf'),
                               # 新的LyricTimeline参数
                               main_timeline: Union['LyricTimeline', None] = None,
                               aux_timeline: Union['LyricTimeline', None] = None) -> bool:
        """生成双语版本视频或增强版视频 (OOP重构版)

        支持两种调用方式：
        1. 传入LyricTimeline对象（推荐）: main_timeline, aux_timeline
        2. 传入List[Tuple[float, str]]（向后兼容）: main_lyrics, aux_lyrics

        当使用timeline参数时，会优先使用timeline；否则使用传统的lyrics参数
        """

        # 参数处理和转换逻辑
        if main_timeline is not None or aux_timeline is not None:
            # 使用新的LyricTimeline接口
            if not LYRIC_TIMELINE_AVAILABLE:
                raise RuntimeError("LyricTimeline模块不可用，无法使用timeline参数")
            return self._generate_video_with_timelines(
                main_timeline, aux_timeline, audio_path, output_path,
                background_image, t_max_sec
            )

        # 向后兼容：使用传统的lyrics参数
        if main_lyrics is None:
            raise ValueError("必须提供main_lyrics或main_timeline参数")

        # 确定生成模式
        is_bilingual_mode = aux_lyrics is not None
        mode_name = "双语版" if is_bilingual_mode else "增强版"

        try:
            print(f"开始生成{mode_name}: {output_path}")

            print("加载音频...")
            audio = AudioFileClip(audio_path)
            original_duration = audio.duration
            duration = min(original_duration, t_max_sec)

            # 如果需要裁剪音频
            if t_max_sec < original_duration:
                audio = audio.subclip(0, t_max_sec)
                print(f"   音频已裁剪: {original_duration:.1f}s -> {duration:.1f}s")
            else:
                print(f"   音频时长: {duration:.1f} 秒")

            # 过滤歌词，只保留在时间范围内的
            filtered_main_lyrics = [(t, text) for t, text in main_lyrics if t < duration]
            print(f"   使用主歌词行数: {len(filtered_main_lyrics)}/{len(main_lyrics)}")

            if is_bilingual_mode:
                filtered_aux_lyrics = [(t, text) for t, text in aux_lyrics if t < duration]
                print(f"   使用副歌词行数: {len(filtered_aux_lyrics)}/{len(aux_lyrics)}")
            else:
                filtered_aux_lyrics = None

            print("创建背景...")
            background_clip = self._create_video_background(duration, background_image)

            all_video_clips = [background_clip]

            if is_bilingual_mode:
                # 双语模式：使用helper方法处理两种语言
                print("处理主歌词...")
                main_clips_list = self._generate_lyric_clips(
                    lyrics_list=filtered_main_lyrics,
                    total_video_duration=duration,
                    y_position=self.height // 2 - 80,
                    is_highlighted=True,
                    animation_style=animation_style
                )
                all_video_clips.extend(main_clips_list)

                print("处理副歌词...")
                aux_clips_list = self._generate_lyric_clips(
                    lyrics_list=filtered_aux_lyrics,  # type: ignore  # We know it's not None in bilingual mode
                    total_video_duration=duration,
                    y_position=self.height // 2 + 60,
                    is_highlighted=False,
                    animation_style='fade'  # 副歌词总是使用fade动画
                )
                all_video_clips.extend(aux_clips_list)

                num_lyric_clips = len(main_clips_list) + len(aux_clips_list)
                temp_suffix = "bilingual"
            else:
                # 增强模式：当前歌词+下一句预览
                print("创建歌词片段...")
                lyric_clips_generated = 0
                for i, (start_time, text) in enumerate(filtered_main_lyrics):
                    if i < len(filtered_main_lyrics) - 1:
                        end_time = filtered_main_lyrics[i + 1][0]
                    else:
                        end_time = duration

                    lyric_duration = end_time - start_time
                    if lyric_duration <= 0.01:
                        print(f"   跳过主歌词（时长过短 {lyric_duration:.2f}s）: '{text}'")
                        continue

                    # 当前歌词（高亮）
                    current_clip = self.create_lyric_clip_with_animation(
                        text, start_time, lyric_duration,
                        is_highlighted=True,
                        y_position=self.height // 2 - 50,
                        animation=animation_style
                    )
                    all_video_clips.append(current_clip)
                    lyric_clips_generated += 1

                    # 下一句预览（非高亮）
                    if i < len(filtered_main_lyrics) - 1:
                        next_text = filtered_main_lyrics[i + 1][1]
                        next_clip = self.create_lyric_clip_with_animation(
                            next_text, start_time, lyric_duration,
                            is_highlighted=False,
                            y_position=self.height // 2 + 80,
                            animation='fade'
                        )
                        all_video_clips.append(next_clip)
                        lyric_clips_generated += 1

                num_lyric_clips = lyric_clips_generated
                temp_suffix = "enhanced"

            print(f"   创建了 {num_lyric_clips} 个歌词片段 (总共 {len(all_video_clips)} 个视频片段包括背景)")

            self._finalize_and_export_video(
                all_clips=all_video_clips,
                audio_clip=audio,
                output_path=output_path,
                temp_audio_file_suffix=temp_suffix
            )

            print(f"{mode_name}视频生成成功！")
            return True

        except Exception as e:
            print(f"{mode_name}生成失败: {e}")
            traceback.print_exc()
            return False

    def _generate_video_with_timelines(self,
                                     main_timeline: 'LyricTimeline',
                                     aux_timeline: Optional['LyricTimeline'] = None,
                                     audio_path: str = "",
                                     output_path: str = "",
                                     background_image: Optional[str] = None,
                                     t_max_sec: float = float('inf')) -> bool:
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
                audio = audio.subclip(0, t_max_sec)
                print(f"   音频已裁剪: {original_duration:.1f}s -> {duration:.1f}s")
            else:
                print(f"   音频时长: {duration:.1f} 秒")

            # 显示时间轴信息
            print(f"主时间轴信息: {main_timeline.get_info()}")
            if aux_timeline:
                print(f"副时间轴信息: {aux_timeline.get_info()}")

            # 计算布局信息
            main_rect = main_timeline.calculate_required_rect(self.width, self.height)
            print(f"主时间轴所需区域: {main_rect}")

            if aux_timeline:
                aux_rect = aux_timeline.calculate_required_rect(self.width, self.height)
                print(f"副时间轴所需区域: {aux_rect}")

                if main_rect.overlaps_with(aux_rect):
                    print("警告: 时间轴显示区域重叠，可能需要调整布局")

            # 背景处理（保持原有逻辑）
            print("创建背景...")
            background_clip = self._create_video_background(duration, background_image)
            all_video_clips = [background_clip]

            # 使用LyricTimeline生成片段
            print("生成歌词片段...")
            main_clips = main_timeline.generate_clips(self, duration)
            all_video_clips.extend(main_clips)

            num_lyric_clips = len(main_clips)

            if aux_timeline:
                aux_clips = aux_timeline.generate_clips(self, duration)
                all_video_clips.extend(aux_clips)
                num_lyric_clips += len(aux_clips)

            print(f"   创建了 {num_lyric_clips} 个歌词片段 (总共 {len(all_video_clips)} 个视频片段包括背景)")

            # 最终合成（保持原有逻辑）
            temp_suffix = "bilingual" if is_bilingual_mode else "enhanced"
            self._finalize_and_export_video(
                all_clips=all_video_clips,
                audio_clip=audio,
                output_path=output_path,
                temp_audio_file_suffix=temp_suffix
            )

            print(f"{mode_name}视频生成成功！")
            return True

        except Exception as e:
            print(f"{mode_name}生成失败: {e}")
            traceback.print_exc()
            return False

def demo_enhanced_features(config_path: Path, t_max_sec: float = float('inf')):
    """使用配置文件生成歌词视频 (OOP重构版)"""
    print("精武英雄歌词视频生成器 - OOP重构版")
    print("=" * 50)

    # 检查LyricTimeline可用性
    if LYRIC_TIMELINE_AVAILABLE:
        print("LyricTimeline模块可用，将使用新的OOP接口")
    else:
        print("LyricTimeline模块不可用，将使用传统接口")

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

    if LYRIC_TIMELINE_AVAILABLE:
        # 使用新的LyricTimeline接口
        print("使用LyricTimeline OOP接口")

        # 创建主时间轴
        main_lrc_path = config.get_main_lrc_path()
        main_timeline = LyricTimeline.from_lrc_file(
            str(main_lrc_path),
            language="chinese",
            display_mode=LyricDisplayMode.ENHANCED_PREVIEW if not config.aux_lrc
                        else LyricDisplayMode.BILINGUAL_SYNC
        )

        aux_timeline = None
        if config.aux_lrc:
            # 创建副时间轴
            aux_lrc_path = config.get_aux_lrc_path()
            aux_timeline = LyricTimeline.from_lrc_file(
                str(aux_lrc_path),
                language="english",
                display_mode=LyricDisplayMode.BILINGUAL_SYNC
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
            t_max_sec=t_max_sec
        )

    else:
        # 使用传统接口（向后兼容）
        print("使用传统接口（向后兼容）")

        # 解析主歌词文件
        main_lrc_path = config.get_main_lrc_path()
        main_lyrics = generator.parse_lrc_file(str(main_lrc_path))

        # 应用时间限制
        if t_max_sec < float('inf'):
            main_lyrics = [(t, text) for t, text in main_lyrics if t < t_max_sec]
            print(f"使用歌词（前{t_max_sec:.1f}秒，共{len(main_lyrics)}行）")
        else:
            print(f"使用完整歌词（共{len(main_lyrics)}行）")

        # 根据配置决定生成类型
        if config.aux_lrc:
            # 生成双语版本
            print("\n生成双语版本...")
            aux_lrc_path = config.get_aux_lrc_path()
            aux_lyrics = generator.parse_lrc_file(str(aux_lrc_path))

            # 应用时间限制
            aux_lyrics = [(t, text) for t, text in aux_lyrics if t < t_max_sec]
            success = generator.generate_bilingual_video(
                main_lyrics=main_lyrics,
                aux_lyrics=aux_lyrics,
                audio_path=str(audio_path),
                output_path=str(output_path),
                background_image=str(background_path),
                t_max_sec=t_max_sec
            )
        else:
            # 生成单语增强版本
            print("\n生成增强版本...")
            success = generator.generate_bilingual_video(
                main_lyrics=main_lyrics,
                aux_lyrics=None,  # 增强模式：不提供副歌词
                audio_path=str(audio_path),
                output_path=str(output_path),
                background_image=str(background_path),
                animation_style="fade",
                t_max_sec=t_max_sec
            )

    if success:
        print(f"\n视频生成成功！")
        print(f"输出文件: {output_path}")
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.1f} MB")
    else:
        print(f"\n视频生成失败！")

    return success

if __name__ == "__main__":
    demo_enhanced_features(Path(r"精武英雄\lrc-mv.yaml"), t_max_sec=60.0)
