import json
import os
import subprocess
import numpy as np
import soundfile as sf
from pathlib import Path

# =================== 配置 ===================
INPUT_JSON = "translated_with_timestamps.json"
INPUT_DIR = "generated_audio"
ALIGNED_DIR = os.path.join(INPUT_DIR, "aligned")
BGM_PATH = "/Users/fiona/boson-ai-hackathon/generated_audio/accompaniment.wav"
FINAL_SPEECH = os.path.join(INPUT_DIR, "speech_full.wav")
FINAL_MIXED = os.path.join(INPUT_DIR, "final_with_bgm.wav")

SAMPLE_RATE = 24000
CHANNELS = 1

# =================== 工具函数 ===================
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def get_audio_duration(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def change_audio_speed(input_file, output_file, speed):
    """使用 ffmpeg 改变播放速度"""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_file, "-filter:a", f"atempo={speed}", output_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except:
        return False

def pad_silence(input_file, output_file, pad_seconds):
    """在音频后补静音"""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_file, "-af", f"apad=pad_dur={pad_seconds}", output_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except:
        return False

def align_audio_to_duration(input_file, target_duration, output_file):
    """调整每段音频时长以对齐"""
    actual = get_audio_duration(input_file)
    if actual <= 0:
        print("⚠️ 空音频，跳过。")
        return False

    ratio = target_duration / actual
    if 0.9 <= ratio <= 1.1:
        os.rename(input_file, output_file)
        print(f"  ✅ 匹配: {actual:.2f}s ≈ {target_duration:.2f}s")
        return True

    if ratio > 1.1 and ratio < 2.0:
        speed = 1.0 / ratio
        print(f"  🕐 放慢 {speed:.2f}x → {target_duration:.2f}s")
        change_audio_speed(input_file, output_file, speed)
        return True
    elif ratio < 0.9 and ratio > 0.5:
        speed = 1.0 / ratio
        print(f"  ⏩ 加速 {speed:.2f}x → {target_duration:.2f}s")
        change_audio_speed(input_file, output_file, speed)
        return True
    elif ratio >= 2.0:
        pad_silence(input_file, output_file, target_duration - actual)
        return True
    else:
        os.rename(input_file, output_file)
        return True

def assemble_full_audio(sentences, aligned_dir, output_path):
    """将对齐后的所有语音按时间拼接成完整轨"""
    total_duration = sentences[-1]["end"]
    total_samples = int(total_duration * SAMPLE_RATE)
    full_wave = np.zeros(total_samples, dtype=np.float32)

    print(f"\n🎬 拼接语音轨，总时长 {total_duration:.2f}s")

    for i, sent in enumerate(sentences, 1):
        start = sent.get("start", 0)
        end = sent.get("end", 0)
        target_dur = end - start
        path = os.path.join(aligned_dir, f"aligned_{i:02d}.wav")
        if not os.path.exists(path):
            print(f"  ⚠️ 缺失 {path}，跳过。")
            continue

        # 读取音频并插入正确位置
        data, sr = sf.read(path)
        if sr != SAMPLE_RATE:
            print(f"  ⚠️ 采样率不符: {sr}，跳过。")
            continue

        start_idx = int(start * SAMPLE_RATE)
        end_idx = min(start_idx + len(data), len(full_wave))
        full_wave[start_idx:end_idx] += data[:end_idx - start_idx]

    # 写出完整语音轨
    sf.write(output_path, full_wave, SAMPLE_RATE)
    print(f"✅ 已生成完整语音轨: {output_path}")

def mix_with_bgm(speech, bgm, output_path, volume=0.2):
    """混合语音与环境音"""
    if not os.path.exists(bgm):
        print(f"⚠️ 未找到背景音: {bgm}")
        return False
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", speech,
                "-i", bgm,
                "-filter_complex",
                f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=longest",
                output_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"✅ 已混合语音与背景音: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 混音失败: {e}")
        return False

# =================== 主程序 ===================
def main():
    print("=" * 80)
    print("🎯 Step 3C: 对齐 + 拼接 + 背景混合")
    print("=" * 80)

    ensure_dir(ALIGNED_DIR)

    if not os.path.exists(INPUT_JSON):
        print(f"❌ 找不到 {INPUT_JSON}")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    sentences = data[0].get("sentence_info", [])
    print(f"✅ 加载 {len(sentences)} 段语音\n")

    # Step 1: 对齐每一段
    for i, sent in enumerate(sentences, 1):
        src = os.path.join(INPUT_DIR, f"english_{i:02d}.wav")
        dst = os.path.join(ALIGNED_DIR, f"aligned_{i:02d}.wav")
        if not os.path.exists(src):
            print(f"[{i:02d}] ❌ 缺失 {src}")
            continue
        dur = sent.get("duration", 0)
        print(f"[{i:02d}] 对齐: {Path(src).name} → {dur:.2f}s")
        align_audio_to_duration(src, dur, dst)

    # Step 2: 拼接语音轨
    assemble_full_audio(sentences, ALIGNED_DIR, FINAL_SPEECH)

    # Step 3: 混合背景音
    if os.path.exists(BGM_PATH):
        mix_with_bgm(FINAL_SPEECH, BGM_PATH, FINAL_MIXED, volume=0.18)
    else:
        print(f"⚠️ 未找到环境音: {BGM_PATH}")

    print("\n🎉 全流程完成！")
    print(f"🗣️ 语音轨: {FINAL_SPEECH}")
    print(f"🌿 混音结果: {FINAL_MIXED}")
    print("=" * 80)

if __name__ == "__main__":
    main()
