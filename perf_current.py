#!/usr/bin/env python3
"""
测试当前MoviePy 2.1.2版本的性能瓶颈
"""

import cProfile
import pstats
import io
from pathlib import Path

def profile_current_version():
    """分析当前版本的性能"""
    print("🔍 分析MoviePy 2.1.2性能瓶颈...")
    
    # 创建性能分析器
    profiler = cProfile.Profile()
    
    # 开始分析
    profiler.enable()
    
    try:
        from enhanced_generator import demo_enhanced_features
        config_path = Path("精武英雄/lrc-mv.yaml")
        
        # 运行视频生成
        success = demo_enhanced_features(
            config_path=config_path,
            t_max_sec=60.0
        )
        
        if success:
            print("✅ 视频生成成功")
        else:
            print("❌ 视频生成失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止分析
        profiler.disable()
    
    # 分析结果
    print("\n📊 性能分析结果:")
    print("=" * 60)
    
    # 创建统计对象
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    
    # 按累计时间排序，显示前20个最耗时的函数
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    
    # 获取统计信息
    stats_output = stats_stream.getvalue()
    print(stats_output)
    
    # 查找特定的瓶颈
    print("\n🔍 查找关键瓶颈:")
    print("-" * 40)
    
    # 查找PIL相关的调用
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats('cumulative')
    stats.print_stats('PIL')
    pil_output = stats_stream.getvalue()
    if 'PIL' in pil_output:
        print("PIL相关调用:")
        print(pil_output)
    else:
        print("未发现PIL相关瓶颈")
    
    # 查找compose相关的调用
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats('cumulative')
    stats.print_stats('compose')
    compose_output = stats_stream.getvalue()
    if 'compose' in compose_output:
        print("\nCompose相关调用:")
        print(compose_output)
    else:
        print("未发现compose相关瓶颈")
    
    # 查找get_frame相关的调用
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats('cumulative')
    stats.print_stats('get_frame')
    frame_output = stats_stream.getvalue()
    if 'get_frame' in frame_output:
        print("\nget_frame相关调用:")
        print(frame_output)
    else:
        print("未发现get_frame相关瓶颈")
    
    # 保存详细报告
    with open('current_performance_analysis.txt', 'w', encoding='utf-8') as f:
        f.write("MoviePy 2.1.2 性能分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write("完整统计信息:\n")
        f.write(stats_output)
        f.write("\n\nPIL相关:\n")
        f.write(pil_output)
        f.write("\n\nCompose相关:\n")
        f.write(compose_output)
        f.write("\n\nget_frame相关:\n")
        f.write(frame_output)
    
    print(f"\n📄 详细报告已保存到: current_performance_analysis.txt")

# def compare_with_old_analysis():
#     """对比旧的性能分析"""
#     print("\n🔄 对比分析:")
#     print("-" * 40)
    
#     old_analysis_path = Path("performance_analysis/write_videofile_analysis.txt")
#     if old_analysis_path.exists():
#         print("📄 发现旧的性能分析文件")
#         with open(old_analysis_path, 'r', encoding='utf-8') as f:
#             old_content = f.read()
        
#         if 'blit' in old_content:
#             print("⚠️  旧分析中发现blit瓶颈")
#             # 提取blit相关的行
#             lines = old_content.split('\n')
#             blit_lines = [line for line in lines if 'blit' in line.lower()]
#             for line in blit_lines[:5]:  # 显示前5行
#                 print(f"   {line}")
#         else:
#             print("✅ 旧分析中未发现blit瓶颈")
#     else:
#         print("❌ 未找到旧的性能分析文件")

def main():
    """主函数"""
    print("🚀 MoviePy 2.1.2 性能重新分析")
    print("=" * 60)
    
    # 检查版本
    try:
        import moviepy
        print(f"📦 MoviePy版本: {moviepy.__version__}")
    except:
        print("❌ 无法获取MoviePy版本")
        return
    
    # 运行性能分析
    profile_current_version()
    
    # 对比旧分析
    # compare_with_old_analysis()
    
    print("\n🎯 分析完成！")

if __name__ == "__main__":
    main()
