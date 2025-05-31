#!/usr/bin/env python3
"""
调试动画逻辑的脚本
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lyric_timeline import LyricTimeline

def debug_animation():
    """调试动画逻辑"""
    print("🔍 调试动画逻辑...")

    # 创建测试歌词数据，时间间隔较短以测试重叠
    lyrics_data = [
        (0.0, "第一句歌词"),
        (2.5, "第二句歌词"),  # 与第一句有重叠
        (5.0, "第三句歌词")
    ]

    timeline = LyricTimeline(lyrics_data, "chinese")

    # 测试各个时间点
    test_times = [2.0, 2.2, 2.5, 2.8, 3.0]
    animation_duration = 0.3

    for t in test_times:
        print(f"\n时间 {t}s:")

        # 手动检查每句歌词的状态
        for i, (start_time, text) in enumerate(lyrics_data):
            duration = timeline._calculate_lyric_duration(i)
            fade_in_start = start_time - animation_duration
            fade_out_end = start_time + duration

            print(f"  歌词{i}: '{text}'")
            print(f"    开始时间: {start_time}, 持续时间: {duration}")
            print(f"    淡入开始: {fade_in_start}, 淡出结束: {fade_out_end}")
            print(f"    是否在范围内: {fade_in_start <= t < fade_out_end}")

            if fade_in_start <= t < fade_out_end:
                progress = timeline._calculate_animation_progress(t, start_time, duration, animation_duration)
                print(f"    动画进度: {progress:.3f}")

                # 详细调试淡入计算
                if t < start_time:
                    fade_in_progress = (t - fade_in_start) / animation_duration
                    print(f"    淡入计算: ({t} - {fade_in_start}) / {animation_duration} = {fade_in_progress:.3f}")

        # 获取活动歌词
        active_lyrics = timeline.get_content_at_time(t, animation_duration=animation_duration)
        print(f"  活动歌词数量: {len(active_lyrics)}")
        for lyric in active_lyrics:
            print(f"    - '{lyric['text']}': 进度={lyric['animation_progress']:.3f}")

if __name__ == "__main__":
    debug_animation()
