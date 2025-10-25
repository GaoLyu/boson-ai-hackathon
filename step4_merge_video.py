import subprocess
import os
import json
from pathlib import Path

# ===== 配置 =====
ORIGINAL_VIDEO = "sleep.mp4"           # 原视频文件
ENGLISH_AUDIO = "final_english_audio.wav"  # 生成的英文音频
OUTPUT_VIDEO = "sleep_english.mp4"     # 最终输出视频

# 可选配置
TRANSLATED_JSON = "translated_with_timestamps.json"  # 翻译JSON（用于生成字幕）
ENGLISH_SUBTITLES = "english_subtitles.srt"         # 生成的英文字幕

def check_file(path, description):
    """检查文件是否存在"""
    if os.path.exists(path):
        size = os.path.getsize(path) / (1024*1024)
        print(f"  ✅ {description}: {path} ({size:.2f} MB)")
        return True
    else:
        print(f"  ❌ {description}: {path} (未找到)")
        return False

def get_duration(media_path):
    """获取媒体文件时长"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", media_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def replace_audio(video_path, audio_path, output_path, sync_mode="first"):
    """
    替换视频音频
    
    参数:
        sync_mode: 
            - "first": 以较短的为准（推荐）
            - "video": 以视频长度为准
            - "audio": 以音频长度为准
    """
    print("\n🎬 替换视频音频...")
    
    # 检查时长
    video_duration = get_duration(video_path)
    audio_duration = get_duration(audio_path)
    
    print(f"  📹 视频时长: {video_duration:.1f}秒")
    print(f"  🎵 音频时长: {audio_duration:.1f}秒")
    
    # 时长差异检查
    diff = abs(video_duration - audio_duration)
    if diff > 1.0:
        print(f"  ⚠️  时长差异: {diff:.1f}秒")
    else:
        print(f"  ✅ 时长匹配良好")
    
    try:
        # 先检查音频文件是否有效
        check_result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", 
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
             audio_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        audio_codec = check_result.stdout.strip()
        print(f"  🔊 音频编码: {audio_codec}")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,    # 输入：原视频
            "-i", audio_path,    # 输入：新音频
            "-c:v", "copy",      # 视频流：复制（不重新编码，快速）
            "-c:a", "aac",       # 音频流：编码为AAC（通用格式）
            "-b:a", "192k",      # 音频比特率
            "-ar", "44100",      # 音频采样率（标准）
            "-ac", "2",          # 声道数：立体声
            "-map", "0:v:0",     # 使用第一个文件的视频流
            "-map", "1:a:0",     # 使用第二个文件的音频流
        ]
        
        # 根据同步模式添加参数
        if sync_mode == "first":
            cmd.append("-shortest")  # 以较短的为准
        
        cmd.append(output_path)
        
        print(f"  🔄 处理中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ 成功: {output_path}")
            
            # 验证输出文件是否有音频
            verify_result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
                 output_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            
            if verify_result.stdout.strip():
                print(f"  ✅ 音频流验证通过")
                return True
            else:
                print(f"  ⚠️  警告：输出文件可能没有音频流")
                return True  # 继续，但警告
        else:
            print(f"  ❌ 失败:")
            print(f"     {result.stderr[-400:]}")  # 显示更多错误信息
            return False
    
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def format_srt_time(seconds):
    """格式化SRT时间戳 (00:00:01,000)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def create_srt_subtitles(json_path, output_srt):
    """从翻译JSON生成SRT字幕文件"""
    print("\n📝 生成SRT字幕...")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sentences = data[0].get("sentence_info", [])
        
        with open(output_srt, 'w', encoding='utf-8') as f:
            subtitle_index = 1
            
            for sent in sentences:
                text_en = sent.get("text_en", "")
                start = sent.get("start", 0)
                end = sent.get("end", 0)
                
                # 跳过失败的句子
                if "[FAILED:" in text_en or not text_en:
                    continue
                
                # 写入字幕
                f.write(f"{subtitle_index}\n")
                f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
                f.write(f"{text_en}\n\n")
                
                subtitle_index += 1
        
        print(f"  ✅ 字幕生成: {output_srt} ({subtitle_index-1} 条)")
        return True
    
    except Exception as e:
        print(f"  ❌ 生成失败: {e}")
        return False

def burn_subtitles(video_path, subtitle_path, output_path, style="default"):
    """
    将字幕烧录到视频中
    
    参数:
        style: 字幕样式
            - "default": 默认样式
            - "custom": 自定义样式（黄色，底部，阴影）
    """
    print("\n🔥 烧录字幕到视频...")
    
    try:
        # 转义路径（Windows兼容）
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        
        if style == "custom":
            # 自定义样式
            subtitles_filter = f"subtitles={subtitle_path_escaped}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,Outline=2,Shadow=1,MarginV=30'"
        else:
            # 默认样式
            subtitles_filter = f"subtitles={subtitle_path_escaped}"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", subtitles_filter,
            "-c:a", "copy",  # 音频不变
            output_path
        ]
        
        print(f"  🔄 处理中（这可能需要几分钟）...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ 成功: {output_path}")
            return True
        else:
            print(f"  ❌ 失败: {result.stderr[:200]}")
            return False
    
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def add_soft_subtitles(video_path, subtitle_path, output_path):
    """
    添加软字幕（可在播放器中开关）
    """
    print("\n📎 添加软字幕...")
    
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", subtitle_path,
            "-c", "copy",
            "-c:s", "mov_text",  # 字幕编码格式
            "-metadata:s:s:0", "language=eng",
            output_path
        ]
        
        print(f"  🔄 处理中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ 成功: {output_path}")
            return True
        else:
            print(f"  ⚠️  软字幕失败，某些容器格式不支持")
            return False
    
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def compare_files(original, new):
    """比较文件大小"""
    if os.path.exists(original) and os.path.exists(new):
        original_size = os.path.getsize(original) / (1024*1024)
        new_size = os.path.getsize(new) / (1024*1024)
        
        print(f"\n📦 文件大小对比:")
        print(f"  原视频: {original_size:.2f} MB")
        print(f"  新视频: {new_size:.2f} MB")
        
        if new_size > original_size * 1.5:
            print(f"  ⚠️  新视频较大 (+{(new_size-original_size):.2f} MB)")
        elif new_size < original_size * 0.5:
            print(f"  ⚠️  新视频较小 (-{(original_size-new_size):.2f} MB)")
        else:
            print(f"  ✅ 大小合理")

def main():
    print("="*80)
    print("🎬 Step 4: 视频合成 - 替换音频")
    print("="*80)
    
    # 检查必需文件
    print("\n📋 检查输入文件:")
    
    has_video = check_file(ORIGINAL_VIDEO, "原视频")
    has_audio = check_file(ENGLISH_AUDIO, "英文音频")
    
    if not has_video or not has_audio:
        print("\n❌ 缺少必需文件，无法继续")
        return
    
    # 步骤1: 生成字幕（可选）
    print("\n" + "="*80)
    print("📝 步骤 1: 字幕生成")
    print("="*80)
    
    has_subtitles = False
    
    if os.path.exists(TRANSLATED_JSON):
        create_subs = input("\n生成英文字幕? (y/n) [y]: ").strip().lower() or "y"
        
        if create_subs == "y":
            if create_srt_subtitles(TRANSLATED_JSON, ENGLISH_SUBTITLES):
                has_subtitles = True
    else:
        print(f"  ⚠️  未找到翻译文件: {TRANSLATED_JSON}")
        print(f"  ℹ️  跳过字幕生成")
    
    # 步骤2: 替换音频
    print("\n" + "="*80)
    print("🎵 步骤 2: 替换音频")
    print("="*80)
    
    # 如果需要字幕，先创建临时视频
    if has_subtitles:
        temp_video = "temp_with_audio.mp4"
        
        if not replace_audio(ORIGINAL_VIDEO, ENGLISH_AUDIO, temp_video):
            print("\n❌ 音频替换失败")
            return
        
        # 步骤3: 添加字幕
        print("\n" + "="*80)
        print("📝 步骤 3: 添加字幕")
        print("="*80)
        
        print("\n字幕类型:")
        print("  1. 硬字幕（烧录到视频，永久显示）")
        print("  2. 软字幕（可在播放器中开关）")
        print("  3. 不添加字幕")
        
        sub_choice = input("\n选择 (1/2/3) [1]: ").strip() or "1"
        
        if sub_choice == "1":
            # 硬字幕
            style = input("\n使用自定义样式? (y/n) [n]: ").strip().lower()
            style_mode = "custom" if style == "y" else "default"
            
            if burn_subtitles(temp_video, ENGLISH_SUBTITLES, OUTPUT_VIDEO, style_mode):
                os.remove(temp_video)
            else:
                print("  ⚠️  字幕烧录失败，使用无字幕版本")
                os.rename(temp_video, OUTPUT_VIDEO)
        
        elif sub_choice == "2":
            # 软字幕
            if not add_soft_subtitles(temp_video, ENGLISH_SUBTITLES, OUTPUT_VIDEO):
                print("  ⚠️  软字幕失败，使用无字幕版本")
                os.rename(temp_video, OUTPUT_VIDEO)
            else:
                os.remove(temp_video)
        
        else:
            # 不添加字幕
            os.rename(temp_video, OUTPUT_VIDEO)
    
    else:
        # 没有字幕，直接替换音频
        if not replace_audio(ORIGINAL_VIDEO, ENGLISH_AUDIO, OUTPUT_VIDEO):
            print("\n❌ 视频生成失败")
            return
    
    # 完成
    print("\n" + "="*80)
    print("✅ 视频处理完成！")
    print("="*80)
    
    if os.path.exists(OUTPUT_VIDEO):
        # 文件信息
        output_duration = get_duration(OUTPUT_VIDEO)
        
        print(f"\n📹 输出视频: {OUTPUT_VIDEO}")
        print(f"⏱️  视频时长: {output_duration:.1f}秒")
        
        if has_subtitles and os.path.exists(ENGLISH_SUBTITLES):
            print(f"📝 字幕文件: {ENGLISH_SUBTITLES}")
        
        # 大小对比
        compare_files(ORIGINAL_VIDEO, OUTPUT_VIDEO)
        
        # 播放提示
        print(f"\n▶️  播放视频:")
        print(f"   ffplay {OUTPUT_VIDEO}")
        print(f"\n或用任何视频播放器打开")
        
        # 质量检查建议
        print(f"\n💡 质量检查建议:")
        print(f"   1. 检查音频是否与画面同步")
        print(f"   2. 检查音量是否合适")
        print(f"   3. 检查字幕是否准确（如果有）")
        
    print("\n" + "="*80)
    print("🎉 全部完成！")
    print("="*80)

if __name__ == "__main__":
    # 检查ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("❌ 需要安装 ffmpeg: https://ffmpeg.org/download.html")
        exit(1)
    
    main()