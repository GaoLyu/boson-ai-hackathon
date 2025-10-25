import json
import re
from openai import OpenAI
import time

# ===== 配置 =====
API_BASE = "https://hackathon.boson.ai/v1"
API_KEY = "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH"
MODEL_NAME = "Qwen3-32B-non-thinking-Hackathon"

INPUT_JSON = "transcription_with_timestamps.json"
OUTPUT_JSON = "translated_with_timestamps.json"

# ===== 目标语言配置 =====
SOURCE_LANG = "Chinese"
TARGET_LANG = "English"

client = OpenAI(api_key=API_KEY, base_url=API_BASE)


# =============================================================
# 工具函数
# =============================================================
def clean_text(text: str) -> str:
    """清理翻译文本"""
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)  # 移除中文
    text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
    text = ' '.join(text.split())
    return text.strip()


# =============================================================
# 第一步：分析视频内容风格
# =============================================================
def analyze_content_style(sentences: list) -> dict:
    print("\n" + "=" * 80)
    print("🔍 分析视频内容风格...")
    print("=" * 80)

    # 抽样几句分析风格
    sample_texts = [s.get("text", "").strip() for s in sentences[:5]]
    sample_texts += [s.get("text", "").strip() for s in sentences[-2:]]
    sample = "\n".join([f"{i+1}. {t}" for i, t in enumerate(sample_texts) if t])

    prompt = f"""Analyze this video transcript sample and identify:

SAMPLE TEXT:
{sample}

Provide a brief analysis (2-3 sentences):
1. Content type (e.g. comedy, educational, narrative, etc.)
2. Tone and style (formal, casual, humorous, etc.)
3. Any special traits (wordplay, technical terms, etc.)

Keep it concise:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a content analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        analysis = response.choices[0].message.content.strip()
        print(f"\n📊 内容分析:\n{analysis}\n")
        return {"analysis": analysis}
    except Exception as e:
        print(f"⚠️ 分析失败: {e}")
        return {"analysis": "General video content."}


# =============================================================
# 第二步：整段翻译（保留时间戳）
# =============================================================
def translate_full_script(sentences: list, style_info: dict) -> list:
    print("\n" + "=" * 80)
    print(f"📝 翻译全文 ({SOURCE_LANG} → {TARGET_LANG})")
    print("=" * 80)

    full_script = []
    for i, s in enumerate(sentences):
        text = s.get("text", "").strip()
        if text:
            full_script.append(f"{i+1}. {text}")
    script_text = "\n".join(full_script)

    style_context = style_info.get("analysis", "")

    prompt = f"""You are translating a video transcript from {SOURCE_LANG} to {TARGET_LANG}.

CONTENT ANALYSIS:
{style_context}

FULL TRANSCRIPT:
{script_text}

TRANSLATION REQUIREMENTS:
1. Translate naturally and fluently as if it were originally in {TARGET_LANG}.
2. Keep the same tone, humor, and emotional style.
3. Output numbered sentences exactly as in the input (1., 2., 3., ...).
4. Only return the translated lines — do not repeat the Chinese.

Begin translation:"""

    try:
        print("\n🤖 正在翻译中...")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a professional translator for video subtitles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000
        )

        translation = response.choices[0].message.content.strip()
        lines = []
        for line in translation.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 去掉序号（支持 1. / 1) / 1、等）
            line = re.sub(r"^\d+[\.\)、]\s*", "", line)
            line = clean_text(line)
            if line and len(line) > 1:
                lines.append(line)

        print(f"✅ 成功翻译 {len(lines)} 句\n")
        print("翻译预览:")
        print("-" * 80)
        for i in range(min(5, len(lines))):
            print(f"{i+1}. {lines[i]}")
        if len(lines) > 5:
            print(f"... (还有 {len(lines)-5} 句)")
        print("-" * 80)

        return lines
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return []


# =============================================================
# 第三步：长度微调（并打印前后对比）
# =============================================================
def adjust_by_length(sentences: list, translations: list) -> list:
    print("\n" + "=" * 80)
    print("✏️  调整英文长度（保持与中文接近，差距≤3词）")
    print("=" * 80)

    adjusted = []
    for i, sent in enumerate(sentences):
        if i >= len(translations):
            continue

        text_zh = sent.get("text", "")
        text_en = translations[i]

        target_words = max(3, len(text_zh) // 3)
        current_words = len(text_en.split())

        # 输出原始翻译
        print(f"\n[{i+1}] 原文: {text_zh}")
        print(f"     初译: {text_en}")
        print(f"     词数: {current_words}, 目标: {target_words}")

        if abs(current_words - target_words) <= 3:
            adjusted_text = text_en
            print("     ✅ 无需调整")
        else:
            print("     🔧 调整中...")
            try:
                prompt = f"""Adjust this English sentence so that its length (word count) is close to {target_words} words.
Keep the same meaning, tone, and fluency.
Sentence: "{text_en}"
Output only the adjusted sentence."""
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a fluent English editor."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=100
                )
                adjusted_text = clean_text(response.choices[0].message.content.strip())
                if not adjusted_text:
                    adjusted_text = text_en
                print(f"     ✅ 调整后: {adjusted_text}")
            except Exception as e:
                print(f"     ⚠️ 调整失败: {e}")
                adjusted_text = text_en

            time.sleep(0.4)

        adjusted.append(adjusted_text)

    return adjusted


# =============================================================
# 主流程
# =============================================================
def main():
    print("=" * 80)
    print("🎬 Step 2: 中文 → 英文翻译（保留时间戳结构 + 对比输出）")
    print("=" * 80)

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}")
        return

    result = data[0]
    sentences = result.get("sentence_info", [])
    print(f"✅ 加载 {len(sentences)} 个句子")

    # 1️⃣ 内容风格分析
    style_info = analyze_content_style(sentences)

    # 2️⃣ 翻译
    translations = translate_full_script(sentences, style_info)
    if not translations:
        print("❌ 翻译失败")
        return

    # 3️⃣ 长度微调 + 输出对比
    adjusted = adjust_by_length(sentences, translations)

    # 4️⃣ 构建输出：保留 start/end/duration
    translated = []
    for i, s in enumerate(sentences):
        translated.append({
            "start": s.get("start", 0),
            "end": s.get("end", 0),
            "duration": round(s.get("end", 0) - s.get("start", 0), 2),
            "text_zh": s.get("text", ""),
            "text_en": adjusted[i] if i < len(adjusted) else ""
        })

    output = [{
        "key": result.get("key", "unknown"),
        "sentence_info": translated,
        "metadata": {
            "source_language": SOURCE_LANG,
            "target_language": TARGET_LANG,
            "model": MODEL_NAME,
            "method": "length_adjust_no_timestamp_with_diff"
        }
    }]

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n💾 翻译完成，结果已保存至:", OUTPUT_JSON)
    print("=" * 80)


if __name__ == "__main__":
    main()
