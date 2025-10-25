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

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def clean_text(text: str) -> str:
    """清理文本"""
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
    text = ' '.join(text.split())
    return text.strip()

# ===== 第一步：完整翻译全文 =====
def translate_full_script(sentences: list) -> list:
    """
    一次性翻译整个脚本，保证连贯性
    """
    print("\n" + "="*80)
    print("📝 第一步：整体翻译全文（保证连贯性）")
    print("="*80)
    
    # 构建完整脚本
    full_script = []
    for i, s in enumerate(sentences):
        text = s.get("text", "").strip()
        if text:
            full_script.append(f"{i+1}. {text}")
    
    script_text = "\n".join(full_script)
    
    prompt = f"""You are translating a humorous Chinese video about robots learning to sleep like humans.

FULL CHINESE SCRIPT:
{script_text}

CONTEXT: 
- This is satirical comedy from a robot's perspective
- Robots are observing humans and hilariously misunderstanding their behavior
- They think humans sleep during the day, work at night
- They refer to human belly buttons as "oil ports" (because they think humans are robots)
- The tone is deadpan - robots describe absurd things as if they're normal

TRANSLATION TASK:
Translate the ENTIRE script to natural, conversational English. Keep:
- The deadpan humor
- Natural flow between sentences
- Cultural jokes adapted for English speakers
- Each line should be engaging and funny

Output format: 
1. [English translation]
2. [English translation]
...

Translate now (output ONLY the numbered translations):"""

    try:
        print("\n🤖 正在翻译全文...")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a professional comedy translator. Output only the translation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=800
        )
        
        translation = response.choices[0].message.content.strip()
        
        # 解析翻译结果
        lines = []
        for line in translation.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 移除序号
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            line = clean_text(line)
            if line and len(line) > 2:
                lines.append(line)
        
        print(f"✅ 成功翻译 {len(lines)} 句\n")
        
        # 显示翻译结果
        print("翻译预览:")
        print("-" * 80)
        for i, line in enumerate(lines[:5], 1):
            print(f"{i}. {line}")
        if len(lines) > 5:
            print("...")
        print("-" * 80)
        
        return lines
    
    except Exception as e:
        print(f"❌ 全文翻译失败: {e}")
        return []

# ===== 第二步：调整每句长度 =====
def adjust_for_timing(translation: str, target_words: int, context: str) -> str:
    """
    调整单句长度以匹配时长
    """
    current_words = len(translation.split())
    
    # 如果长度已经接近，直接返回
    if abs(current_words - target_words) <= 2:
        return translation
    
    if current_words > target_words + 2:
        # 需要缩短
        prompt = f"""Make this sentence shorter while keeping the humor.

Original ({current_words} words): {translation}
Target: around {target_words} words
Context: {context}

Output the shortened version only:"""
    else:
        # 需要扩展
        prompt = f"""Make this sentence a bit longer with natural details.

Original ({current_words} words): {translation}
Target: around {target_words} words
Context: {context}

Output the longer version only:"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an editor. Output only the adjusted sentence."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=100
        )
        
        adjusted = clean_text(response.choices[0].message.content.strip())
        adjusted_words = len(adjusted.split())
        
        # 检查调整是否有效
        if adjusted and abs(adjusted_words - target_words) < abs(current_words - target_words):
            return adjusted
        return translation
    
    except Exception as e:
        return translation

# ===== 第三步：匹配时间戳和微调 =====
def match_and_adjust(sentences: list, translations: list) -> list:
    """
    将翻译匹配到时间戳，并微调长度
    """
    print("\n" + "="*80)
    print("⏱️  第二步：匹配时间戳并调整长度")
    print("="*80)
    
    results = []
    stats = {"good": 0, "adjusted": 0, "failed": 0}
    
    # 确保数量匹配
    min_len = min(len(sentences), len(translations))
    
    for i in range(min_len):
        sent = sentences[i]
        translation = translations[i] if i < len(translations) else "[MISSING]"
        
        text_zh = sent.get("text", "").strip()
        start = sent.get("start", 0)
        end = sent.get("end", 0)
        duration = end - start
        
        if not text_zh or duration <= 0:
            continue
        
        target_words = max(int(duration * 2.5), 3)
        current_words = len(translation.split())
        
        print(f"\n[{i+1}/{min_len}] {duration:.2f}秒 → 目标 {target_words} 词")
        print(f"  🇨🇳 {text_zh}")
        print(f"  🇬🇧 {translation} ({current_words} 词)")
        
        # 判断是否需要调整
        if abs(current_words - target_words) <= 2:
            final_translation = translation
            print(f"  ✅ 长度合适")
            stats["good"] += 1
        else:
            print(f"  🔧 调整中 ({current_words} → {target_words} 词)...")
            final_translation = adjust_for_timing(
                translation, 
                target_words, 
                "Humorous robot narration about human sleep"
            )
            final_words = len(final_translation.split())
            print(f"  ✅ 调整后: {final_translation} ({final_words} 词)")
            stats["adjusted"] += 1
            time.sleep(0.3)
        
        # 计算最终指标
        word_count = len(final_translation.split())
        est_duration = word_count / 2.5
        duration_ratio = est_duration / duration if duration > 0 else 1.0
        
        results.append({
            "start": start,
            "end": end,
            "duration": round(duration, 2),
            "text_zh": text_zh,
            "text_en": final_translation,
            "word_count": word_count,
            "estimated_duration": round(est_duration, 2),
            "duration_ratio": round(duration_ratio, 2)
        })
    
    print(f"\n✅ 处理完成: {stats['good']} 句合适, {stats['adjusted']} 句已调整")
    return results, stats

# ===== 主流程 =====
def main():
    print("="*80)
    print("🎬 两步翻译法：先整体翻译，再按时间戳微调")
    print("="*80)
    
    # 读取数据
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = data[0]
    sentences = result.get("sentence_info", [])
    
    print(f"\n✅ 加载 {len(sentences)} 个句子")
    print(f"🤖 模型: {MODEL_NAME}\n")
    
    # 第一步：整体翻译
    translations = translate_full_script(sentences)
    
    if not translations:
        print("❌ 翻译失败，终止")
        return
    
    # 第二步：匹配并调整
    translated, stats = match_and_adjust(sentences, translations)
    
    # 保存结果
    output = [{
        "key": result.get("key", "unknown"),
        "sentence_info": translated,
        "metadata": {
            "total": len(translated),
            "successful": len(translated),
            "failed": 0,
            "good_timing": stats["good"],
            "adjusted": stats["adjusted"],
            "model": MODEL_NAME,
            "method": "full_script_first_then_adjust"
        }
    }]
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 总结
    print("\n" + "="*80)
    print("📊 最终统计")
    print("="*80)
    print(f"总句数: {len(translated)}")
    print(f"长度合适: {stats['good']} ({stats['good']/len(translated)*100:.1f}%)")
    print(f"已调整: {stats['adjusted']} ({stats['adjusted']/len(translated)*100:.1f}%)")
    
    # 检查问题句子
    problematic = [
        s for s in translated 
        if s["duration_ratio"] > 1.3 or s["duration_ratio"] < 0.7
    ]
    
    if problematic:
        print(f"\n⚠️  时长偏差较大 ({len(problematic)} 句):")
        for s in problematic[:5]:
            print(f"\n  [{s['start']:.1f}s] 比例 {s['duration_ratio']:.2f}x")
            print(f"    {s['text_en']}")
    
    print(f"\n💾 保存到: {OUTPUT_JSON}")
    print("="*80)

if __name__ == "__main__":
    main()