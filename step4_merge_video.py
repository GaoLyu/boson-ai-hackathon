import os
import subprocess
from pathlib import Path

# =================== 路径配置 ===================
VIDEO_INPUT = "/Users/fiona/boson-ai-hackathon/sleep.mp4"                 # 原始视频（有中文字幕）
NEW_AUDIO = "/Users/fiona/boson-ai-hackathon/generated_audio/final_with_bgm.wav"  # 新音频（英文+背景）
OUTPUT_VIDEO = "/Users/fiona/boson-ai-hackathon/generated_audio/final_video.mp4"  # 输出视频路径

# =================== 函数定义 ===================
def merge_video_audio(video_path, audio_path, output_path):
    """使用 ffmpeg 将视频画面与新音频合并"""
    print("=" * 80)
    print("🎬 Step 4: 合并视频与新音频")
    print("=" * 80)

    # 路径检查
    if not os.path.exists(video_path):
        print(f"❌ 找不到视频文件: {video_path}")
        return False
    if not os.path.exists(audio_path):
        print(f"❌ 找不到音频文件: {audio_path}")
        return False

    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)

    # 检查 ffmpeg 是否安装
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("❌ 未检测到 ffmpeg，请先安装：brew install ffmpeg")
        return False

    # 先获取音频时长
    def get_duration(file):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0

    video_dur = get_duration(video_path)
    audio_dur = get_duration(audio_path)
    print(f"🎞 视频时长: {video_dur:.1f}s")
    print(f"🎧 音频时长: {audio_dur:.1f}s")

    # 自动对齐：让音频和视频取最短时长
    shorter = min(video_dur, audio_dur)
    temp_audio = Path(output_path).with_name("temp_trimmed_audio.wav")

    if abs(video_dur - audio_dur) > 0.2:
        print(f"⚙️ 对齐音频长度 → 截取到 {shorter:.1f}s")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(shorter),
            "-c", "copy",
            str(temp_audio)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_path = str(temp_audio)

    # 合并视频画面 + 新音频
    print("🎥 正在合并，请稍候...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",   # 使用视频流
        "-map", "1:a:0",   # 使用新音频流
        "-c:v", "copy",    # 不重新编码视频
        "-c:a", "aac",     # 转为标准AAC音频
        "-shortest",       # 按最短流结束
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 清理临时音频
    if temp_audio.exists():
        temp_audio.unlink()

    # 验证输出
    if os.path.exists(output_path):
        print(f"✅ 合并完成：{output_path}")
        return True
    else:
        print("❌ 合并失败，请检查 ffmpeg 是否可用。")
        return False


# =================== 主程序 ===================
if __name__ == "__main__":
    success = merge_video_audio(VIDEO_INPUT, NEW_AUDIO, OUTPUT_VIDEO)
    print("=" * 80)
    if success:
        print("🎉 Step 4 完成：最终视频已生成！")
        print("   ▶ 你可以用 Finder 打开并播放：")
        print(f"   {OUTPUT_VIDEO}")
    else:
        print("⚠️ Step 4 未成功。请检查路径或 ffmpeg 安装。")
