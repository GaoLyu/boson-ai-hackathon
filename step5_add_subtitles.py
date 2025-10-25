import json
import os
import subprocess
from pathlib import Path
from datetime import timedelta

# =================== 路径配置 ===================
INPUT_JSON = "translated_with_timestamps.json"
VIDEO_INPUT = "/Users/fiona/boson-ai-hackathon/generated_audio/final_video.mp4"
OUTPUT_SRT = "/Users/fiona/boson-ai-hackathon/generated_audio/final_subtitles.srt"
OUTPUT_VIDEO = "/Users/fiona/boson-ai-hackathon/generated_audio/final_video_stylish.mp4"


# =================== 工具函数 ===================
def sec_to_timestamp(seconds):
    """将浮点秒转换为 SRT 格式 00:00:00,000"""
    td = timedelta(seconds=seconds)
    return str(td)[:-3].replace('.', ',').rjust(12, "0")


def ensure_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


# =================== 生成 SRT ===================
def generate_srt(json_path, srt_path):
    print("=" * 80)
    print("📝 Step 5A: 生成 SRT 字幕文件")
    print("=" * 80)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sentences = data[0].get("sentence_info", [])
    if not sentences:
        print("❌ 未找到字幕内容。")
        return False

    ensure_dir(srt_path)
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, sent in enumerate(sentences, 1):
            start = float(sent.get("start", 0))
            end = float(sent.get("end", start + 1))
            text_en = sent.get("text_en", "").strip()
            if not text_en:
                continue

            f.write(f"{i}\n")
            f.write(f"{sec_to_timestamp(start)} --> {sec_to_timestamp(end)}\n")
            f.write(f"{text_en}\n\n")

    print(f"✅ 已生成字幕文件: {srt_path}")
    return True


# =================== 合成视频 + 模糊底条字幕 ===================
def burn_subtitles_with_blurred_bar(video_path, srt_path, output_path):
    print("=" * 80)
    print("🎬 Step 5B: 合成模糊底条 + 黑边英文字幕")
    print("=" * 80)

    ensure_dir(output_path)

    # === 字幕样式 ===
    subtitle_style = (
        "FontName=Arial,"
        "FontSize=26,"                     # 稍大，方便阅读
        "PrimaryColour=&HFFFFFF&,"         # 白色文字
        "BackColour=&H00000000&,"          # 无底色（我们自己做模糊条）
        "OutlineColour=&H00000000&,"       # 黑色描边
        "BorderStyle=1,"                   # 透明背景 + 描边
        "Outline=2,"                       # 黑边厚度（1~3可调）
        "Shadow=0,"                        # 不加阴影
        "Alignment=2"                      # 底部居中
    )

    # === 视频滤镜 ===
    # 1️⃣ 分出一份模糊版本；
    # 2️⃣ 模糊底部25%；
    # 3️⃣ 混合成柔和底条；
    # 4️⃣ 叠加字幕。
    vf_filter = (
        "[0:v]split[v][vblur];"
        "[vblur]crop=iw:ih*0.25:0:ih*0.75,boxblur=20:1,format=rgba,colorchannelmixer=aa=0.7[blurred];"
        "[v][blurred]overlay=0:H-h*0.25,"
        f"subtitles='{srt_path}':force_style='{subtitle_style}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf_filter,
        "-c:a", "copy",
        output_path
    ]

    print("🎥 正在生成带模糊底条 + 黑边字幕的视频，请稍候...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"✅ 已生成最终视频: {output_path}")
    else:
        print("❌ 合成失败，请检查 ffmpeg 输出：")
        print(result.stderr[-600:])



# =================== 主程序 ===================
if __name__ == "__main__":
    if generate_srt(INPUT_JSON, OUTPUT_SRT):
        burn_subtitles_with_blurred_bar(VIDEO_INPUT, OUTPUT_SRT, OUTPUT_VIDEO)

    print("=" * 80)
    print("🎉 Step 5 完成：已生成带柔和模糊底条 + 英文字幕的视频！")
