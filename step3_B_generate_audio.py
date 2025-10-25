import json
import os
import base64
import subprocess
import time
from pathlib import Path
from openai import OpenAI

# =================== 配置 ===================
API_BASE = "https://hackathon.boson.ai/v1"
API_KEY = os.getenv(
    "BOSON_API_KEY",
    "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH"
)

INPUT_JSON = "translated_with_timestamps.json"
OUTPUT_DIR = "generated_audio"
FINAL_OUTPUT = "final_english_audio.wav"

client = OpenAI(api_key=API_KEY, base_url=API_BASE)


# =================== 工具函数 ===================
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def get_audio_duration(audio_path):
    """获取音频时长"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0


# =================== 主逻辑 ===================
def generate_female_voice(text_en, output_path, max_retries=10):
    """使用固定女性声线（通过 prompt 控制）生成语音"""
    import tempfile
    if not text_en.strip():
        return False

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            # 请求模型生成音频
            response = client.chat.completions.create(
                model="higgs-audio-generation-Hackathon",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an English text-to-speech (TTS) model. "
                            "Always use the same clear, warm female American English voice. "
                            "Speak naturally, fluently, and consistently across all generations. "
                            "Do not include any background noise, effects, or non-speech sounds."
                        )
                    },
                    {"role": "user", "content": text_en.strip()}
                ],
                modalities=["text", "audio"],
                max_completion_tokens=2048,
                temperature=0.4,
                top_p=0.9,
                stream=False
            )

            # 提取音频数据
            audio_b64 = getattr(response.choices[0].message.audio, "data", None)
            if not audio_b64:
                print(f"⚠️ 无音频响应（第 {attempt} 次），5 秒后重试...")
                time.sleep(5)
                continue

            tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            with open(tmp_output, "wb") as f:
                f.write(base64.b64decode(audio_b64))

            duration = get_audio_duration(tmp_output)
            print(f"  🎧 原始生成: {duration:.1f}s")

            # 过滤异常长度
            if duration > 20 or duration < 1:
                print(f"  ⚠️ 异常音频长度 ({duration:.1f}s)，重新生成...")
                os.remove(tmp_output)
                time.sleep(5)
                continue

            os.rename(tmp_output, output_path)
            print(f"  ✅ 保存到: {output_path} ({duration:.1f}s)")
            return True

        except Exception as e:
            err = str(e)
            print(f"⚠️ 第 {attempt} 次失败: {err[:100]}")
            if "504" in err or "timeout" in err.lower():
                print("   ⏳ 检测到超时，5 秒后重试...")
                time.sleep(5)
            elif "Service Unavailable" in err or "InternalServerError" in err:
                print("   ⚙️ 服务器繁忙，10 秒后重试...")
                time.sleep(10)
            else:
                print("   ❌ 未知错误，停止。")
                return False

    print(f"❌ 已重试 {max_retries} 次仍失败，跳过此句。")
    return False


# =================== 主程序 ===================
def main():
    print("=" * 80)
    print("🎤 Step 3B: 生成英文语音（统一女性声线）")
    print("=" * 80)

    ensure_dir(OUTPUT_DIR)

    if not os.path.exists(INPUT_JSON):
        print(f"❌ 找不到输入文件: {INPUT_JSON}")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    sentences = data[0].get("sentence_info", [])
    print(f"✅ 加载 {len(sentences)} 个句子\n")

    stats = {"success": 0, "failed": 0}

    for i, sent in enumerate(sentences, 1):
        text_en = sent.get("text_en", "").strip()
        if not text_en:
            continue

        short = text_en if len(text_en) <= 60 else text_en[:57] + "..."
        print(f"[{i:02d}] 生成: {short}")

        output_path = os.path.join(OUTPUT_DIR, f"english_{i:02d}.wav")
        ok = generate_female_voice(text_en, output_path)
        if ok:
            stats["success"] += 1
        else:
            stats["failed"] += 1

        time.sleep(0.5)

    print("\n" + "=" * 80)
    print("📊 生成统计")
    print(f"✅ 成功: {stats['success']}")
    print(f"❌ 失败: {stats['failed']}")
    print("=" * 80)
    print("\n🎉 Step 3B 完成：英文音频生成完成（统一女性声线 + Native English）！")


if __name__ == "__main__":
    main()
