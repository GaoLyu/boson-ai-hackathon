import subprocess
import os
from pathlib import Path
import sys
import shutil

# ========= 配置 =========
OUTPUT_DIR = "generated_audio"

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def separate_audio_with_demucs(input_audio, output_dir=OUTPUT_DIR):
    """
    使用 Demucs 分离人声与背景音乐。
    生成: vocals.wav, no_vocals.wav
    """
    ensure_dir(output_dir)
    audio_name = Path(input_audio).stem

    print("=" * 80)
    print("🎧 Step 3A: 使用 Demucs 进行人声分离")
    print("=" * 80)

    # 检查 demucs 是否安装
    try:
        subprocess.run(["demucs", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("❌ 未检测到 Demucs，请先运行以下命令安装：")
        print("    pip install demucs ffmpeg-python")
        return None, None

    print(f"🎵 输入音频: {input_audio}")
    print(f"🎯 输出目录: {output_dir}\n")

    # 执行分离
    try:
        subprocess.run(
            ["demucs", "-n", "htdemucs", "--two-stems=vocals", input_audio],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ 分离失败: {e}")
        return None, None

    # 构建输出路径 (兼容 Mac 上的标准 demucs 目录结构)
    separated_root = Path("separated") / "htdemucs" / audio_name
    vocals = separated_root / "vocals.wav"
    bgm = separated_root / "no_vocals.wav"

    # 检查结果
    if not vocals.exists():
        print(f"❌ 未找到人声轨文件: {vocals}")
        print("📁 可尝试查看实际路径: separated/htdemucs/<文件名>/vocals.wav")
        return None, None

    # 拷贝结果到统一输出目录
    final_vocals = Path(output_dir) / "vocals.wav"
    final_bgm = Path(output_dir) / "accompaniment.wav"

    shutil.copy(vocals, final_vocals)
    if bgm.exists():
        shutil.copy(bgm, final_bgm)

    print(f"✅ 人声轨已保存到: {final_vocals}")
    if bgm.exists():
        print(f"✅ 背景轨已保存到: {final_bgm}")

    print("\n🎉 人声分离完成！")
    print("=" * 80)

    return str(final_vocals), str(final_bgm)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ 用法: python step3_A_separate_audio.py <input_audio>")
        print("例如: python step3_A_separate_audio.py sleep.mp3")
        sys.exit(1)

    input_audio = sys.argv[1]
    if not os.path.exists(input_audio):
        print(f"❌ 找不到输入文件: {input_audio}")
        sys.exit(1)

    separate_audio_with_demucs(input_audio)
