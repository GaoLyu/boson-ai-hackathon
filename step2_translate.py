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

def clean_text(text: str) -> str:
    """清理翻译文本，保留目标语言内容"""
    # 移除中文
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    # 移除中文标点
    text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
    # 清理多余空格
    text = ' '.join(text.split())
    return text.strip()

# ===== 第一步：分析内容风格 =====
def analyze_content_style(sentences: list) -> dict:
    """
    分析源文本的风格和类型
    """
    print("\n" + "="*80)
    print("🔍 分析视频内容风格...")
    print("="*80)
    
    # 取前5句和后2句作为样本
    sample_texts = [s.get("text", "").strip() for s in sentences[:5]]
    sample_texts += [s.get("text", "").strip() for s in sentences[-2:]]
    sample = "\n".join([f"{i+1}. {t}" for i, t in enumerate(sample_texts) if t])
    
    analysis_prompt = f"""Analyze this video transcript sample and identify:

SAMPLE TEXT:
{sample}

Provide a brief analysis (2-3 sentences):
1. Content type (comedy, educational, documentary, narrative, etc.)
2. Tone and style (formal, casual, humorous, serious, satirical, etc.)
3. Any special characteristics (wordplay, cultural references, technical terms, etc.)

Keep it concise:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a content analyst. Provide brief, accurate analysis."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        analysis = response.choices[0].message.content.strip()
        print(f"\n📊 内容分析:\n{analysis}\n")
        
        return {
            "analysis": analysis,
            "sample_size": len(sample_texts)
        }
    
    except Exception as e:
        print(f"⚠️ 分析失败: {e}")
        return {
            "analysis": "General video content requiring natural translation.",
            "sample_size": 0
        }

# ===== 第二步：完整翻译全文 =====
def translate_full_script(sentences: list, style_info: dict) -> list:
    """
    一次性翻译整个脚本，保证连贯性
    """
    print("\n" + "="*80)
    print(f"📝 翻译全文 ({SOURCE_LANG} → {TARGET_LANG})")
    print("="*80)
    
    # 构建完整脚本
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
1. Translate naturally and fluently - as if the video was originally made in {TARGET_LANG}
2. Preserve the original tone, style, and emotional impact
3. Maintain coherence and natural flow between sentences
4. Adapt cultural references and idioms appropriately for {TARGET_LANG} audiences
5. Keep humor, wordplay, and rhetorical devices when present
6. Each sentence should connect logically to the previous and next ones

OUTPUT FORMAT:
Return ONLY the translated lines, numbered exactly as the input:
1. [translation]
2. [translation]
3. [translation]
...

Begin translation:"""

    try:
        print("\n🤖 正在翻译...")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"You are a professional translator specializing in video content. Translate from {SOURCE_LANG} to {TARGET_LANG} naturally and accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # 平衡准确性和自然度
            max_tokens=1500
        )
        
        translation = response.choices[0].message.content.strip()
        
        # 解析翻译结果
        lines = []
        for line in translation.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 移除序号（支持多种格式：1. 1) 1、）
            line = re.sub(r'^\d+[\.\)、]\s*', '', line)
            line = clean_text(line)
            if line and len(line) > 1:
                lines.append(line)
        
        print(f"✅ 成功翻译 {len(lines)} / {len(full_script)} 句\n")
        
        # 显示翻译预览
        print("翻译预览:")
        print("-" * 80)
        for i in range(min(5, len(lines))):
            print(f"{i+1}. {lines[i]}")
        if len(lines) > 5:
            print(f"... (还有 {len(lines)-5} 句)")
        print("-" * 80)
        
        return lines
    
    except Exception as e:
        print(f"❌ 全文翻译失败: {e}")
        return []

# ===== 第三步：调整单句长度 =====
def adjust_sentence_length(translation: str, target_words: int, context: str) -> str:
    """
    调整句子长度以匹配音频时长
    """
    current_words = len(translation.split())
    
    # 容差范围：±2词
    if abs(current_words - target_words) <= 2:
        return translation
    
    # 判断需要缩短还是扩展
    if current_words > target_words + 2:
        action = "shorten"
        instruction = f"Make this sentence more concise while keeping the same meaning and style."
    else:
        action = "expand"
        instruction = f"Expand this sentence naturally with relevant details, maintaining the same style."
    
    prompt = f"""{instruction}

Original ({current_words} words): {translation}
Target length: approximately {target_words} words
Content context: {context}

Output only the adjusted sentence:"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"You are an editor. Adjust sentence length while preserving meaning and style."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=150
        )
        
        adjusted = clean_text(response.choices[0].message.content.strip())
        adjusted_words = len(adjusted.split())
        
        # 验证调整是否有效
        if adjusted and abs(adjusted_words - target_words) < abs(current_words - target_words):
            return adjusted
        
        return translation
    
    except Exception as e:
        return translation

# ===== 第四步：匹配时间戳和微调 =====
def match_timestamps_and_adjust(sentences: list, translations: list, style_info: dict) -> tuple:
    """
    将翻译匹配到时间戳，并根据音频时长调整
    """
    print("\n" + "="*80)
    print("⏱️  匹配时间戳并优化长度")
    print("="*80)
    
    results = []
    stats = {
        "total": 0,
        "good_timing": 0,
        "adjusted": 0,
        "failed": 0,
        "too_long": 0,
        "too_short": 0
    }
    
    # 确保数量匹配
    min_len = min(len(sentences), len(translations))
    
    if len(sentences) != len(translations):
        print(f"⚠️  句子数量不匹配: {len(sentences)} 句原文 vs {len(translations)} 句译文")
    
    context = style_info.get("analysis", "Video content")
    
    for i in range(min_len):
        sent = sentences[i]
        translation = translations[i] if i < len(translations) else "[TRANSLATION MISSING]"
        
        text_zh = sent.get("text", "").strip()
        start = sent.get("start", 0)
        end = sent.get("end", 0)
        duration = end - start
        
        if not text_zh or duration <= 0:
            continue
        
        stats["total"] += 1
        
        # 计算目标词数（英文约2.5词/秒）
        target_words = max(int(duration * 2.5), 3)
        current_words = len(translation.split())
        
        print(f"\n[{i+1}/{min_len}] 时长 {duration:.2f}s → 目标 {target_words} 词")
        print(f"  原文: {text_zh}")
        print(f"  译文: {translation} ({current_words} 词)")
        
        # 判断是否需要调整
        word_diff = abs(current_words - target_words)
        
        if word_diff <= 2:
            final_translation = translation
            print(f"  ✅ 长度合适")
            stats["good_timing"] += 1
        else:
            print(f"  🔧 调整长度 ({current_words} → {target_words} 词)...")
            final_translation = adjust_sentence_length(
                translation, 
                target_words,
                context
            )
            final_words = len(final_translation.split())
            
            if final_translation != translation:
                print(f"  ✅ 已调整: {final_translation} ({final_words} 词)")
                stats["adjusted"] += 1
            else:
                print(f"  ⚠️  调整失败，保持原样")
            
            time.sleep(0.4)  # 防止API限流
        
        # 计算最终指标
        word_count = len(final_translation.split())
        est_duration = word_count / 2.5
        duration_ratio = est_duration / duration if duration > 0 else 1.0
        
        # 统计时长匹配情况
        if duration_ratio > 1.2:
            stats["too_long"] += 1
        elif duration_ratio < 0.8:
            stats["too_short"] += 1
        
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
    
    print(f"\n✅ 完成: {stats['good_timing']} 句合适, {stats['adjusted']} 句已调整")
    return results, stats

# ===== 主流程 =====
def main():
    print("="*80)
    print("🎬 通用视频翻译工具")
    print(f"   {SOURCE_LANG} → {TARGET_LANG}")
    print("="*80)
    
    # 读取数据
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 找不到文件: {INPUT_JSON}")
        return
    except json.JSONDecodeError:
        print(f"❌ JSON 格式错误")
        return
    
    result = data[0]
    sentences = result.get("sentence_info", [])
    
    if not sentences:
        print("❌ 未找到句子信息")
        return
    
    print(f"\n✅ 加载 {len(sentences)} 个句子")
    print(f"🤖 模型: {MODEL_NAME}")
    
    # 步骤1: 分析内容风格
    style_info = analyze_content_style(sentences)
    
    # 步骤2: 整体翻译
    translations = translate_full_script(sentences, style_info)
    
    if not translations:
        print("❌ 翻译失败，终止")
        return
    
    # 步骤3: 匹配时间戳并调整
    translated, stats = match_timestamps_and_adjust(sentences, translations, style_info)
    
    # 保存结果
    output = [{
        "key": result.get("key", "unknown"),
        "sentence_info": translated,
        "metadata": {
            "source_language": SOURCE_LANG,
            "target_language": TARGET_LANG,
            "total_sentences": stats["total"],
            "successful": stats["total"] - stats["failed"],
            "failed": stats["failed"],
            "good_timing": stats["good_timing"],
            "adjusted": stats["adjusted"],
            "too_long": stats["too_long"],
            "too_short": stats["too_short"],
            "model": MODEL_NAME,
            "method": "full_script_context_aware"
        }
    }]
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 打印总结
    print("\n" + "="*80)
    print("📊 翻译完成统计")
    print("="*80)
    print(f"总句数: {stats['total']}")
    print(f"成功: {stats['total'] - stats['failed']}")
    print(f"失败: {stats['failed']}")
    print(f"\n时长匹配:")
    print(f"  ✅ 合适 (0.8-1.2x): {stats['good_timing']} ({stats['good_timing']/stats['total']*100:.1f}%)")
    print(f"  🔧 已调整: {stats['adjusted']} ({stats['adjusted']/stats['total']*100:.1f}%)")
    print(f"  ⚠️  偏长 (>1.2x): {stats['too_long']} ({stats['too_long']/stats['total']*100:.1f}%)")
    print(f"  ⚠️  偏短 (<0.8x): {stats['too_short']} ({stats['too_short']/stats['total']*100:.1f}%)")
    
    # 列出需要人工检查的句子
    problematic = [
        s for s in translated 
        if s["duration_ratio"] > 1.3 or s["duration_ratio"] < 0.7
    ]
    
    if problematic:
        print(f"\n⚠️  建议人工检查 ({len(problematic)} 句):")
        for s in problematic[:5]:
            ratio_str = f"{s['duration_ratio']:.2f}x"
            issue = "太长" if s['duration_ratio'] > 1.3 else "太短"
            print(f"\n  [{s['start']:.1f}s] {issue} ({ratio_str})")
            print(f"    原文: {s['text_zh']}")
            print(f"    译文: {s['text_en']}")
        
        if len(problematic) > 5:
            print(f"\n  ... 还有 {len(problematic)-5} 句需要检查")
    
    print(f"\n💾 结果已保存: {OUTPUT_JSON}")
    print("="*80)

if __name__ == "__main__":
    main()