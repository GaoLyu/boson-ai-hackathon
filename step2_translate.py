import json
import os
import re
from openai import OpenAI
import time

# ===== 配置区域 =====
API_BASE = "https://hackathon.boson.ai/v1"
API_KEY = "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH"
# 推荐使用 Claude 或 GPT-4 进行翻译（比 Qwen 更稳定）
# 如果只有 Qwen，使用 non-thinking 版本
MODEL_NAME = "Qwen3-32B-non-thinking-Hackathon"

INPUT_JSON = "transcription_with_timestamps.json"
OUTPUT_JSON = "translated_with_timestamps.json"

# ===== 初始化 =====
client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# ===== 超简单的清理函数 =====
def extract_english(text: str) -> str:
    """
    暴力提取纯英文内容
    """
    # 1. 移除所有 XML 标签
    text = re.sub(r'<[^>]*>.*?</[^>]*>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]*>', '', text)
    
    # 2. 删除所有中文字符
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    
    # 3. 删除多余符号
    text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
    
    # 4. 清理空格
    text = ' '.join(text.split())
    
    # 5. 移除首尾标点
    text = text.strip('.,;:!?\'"- ')
    
    return text.strip()

# ===== 极简 Prompt（分两步） =====
def translate_step1_literal(text: str) -> str:
    """
    第一步：直译（不管时长）
    """
    prompt = f"""Translate this Chinese sentence to English. Keep it natural and simple.

Chinese: {text}

English translation (one sentence):"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a translator. Output only the English translation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 低温度，更稳定
            max_tokens=100
        )
        
        raw = response.choices[0].message.content.strip()
        clean = extract_english(raw)
        return clean if clean else text
    
    except Exception as e:
        print(f"      翻译失败: {e}")
        return text

def translate_step2_adjust_length(literal_translation: str, target_words: int) -> str:
    """
    第二步：调整长度（如果需要）
    """
    current_words = len(literal_translation.split())
    
    # 如果长度已经合适，直接返回
    if abs(current_words - target_words) <= 2:
        return literal_translation
    
    # 如果太长，压缩
    if current_words > target_words + 2:
        prompt = f"""Make this sentence shorter while keeping the same meaning.

Original ({current_words} words): {literal_translation}
Target: {target_words} words

Shorter version:"""
    
    # 如果太短，扩展
    else:
        prompt = f"""Make this sentence slightly longer while keeping the same meaning. Add natural details.

Original ({current_words} words): {literal_translation}
Target: {target_words} words

Longer version:"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an editor. Output only the adjusted sentence."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        raw = response.choices[0].message.content.strip()
        clean = extract_english(raw)
        
        # 验证调整是否成功
        adjusted_words = len(clean.split())
        if abs(adjusted_words - target_words) < abs(current_words - target_words):
            return clean
        else:
            return literal_translation  # 调整失败，返回原翻译
    
    except Exception as e:
        print(f"      长度调整失败: {e}")
        return literal_translation

# ===== 两步翻译流程 =====
def translate_sentence(text_zh: str, duration: float) -> dict:
    """
    两步翻译：先直译，再调整长度
    """
    target_words = max(int(duration * 2.5), 3)  # 英文约 2.5 词/秒
    
    print(f"      目标: {target_words} 词")
    
    # Step 1: 直译
    print(f"      Step 1: 直译...")
    translation = translate_step1_literal(text_zh)
    
    if not translation or translation == text_zh:
        return {
            "translation": f"[FAILED: {text_zh}]",
            "word_count": 0,
            "estimated_duration": duration,
            "duration_ratio": 1.0,
            "success": False
        }
    
    word_count = len(translation.split())
    print(f"      直译结果: {word_count} 词 - {translation}")
    
    # Step 2: 调整长度（如果需要）
    if abs(word_count - target_words) > 2:
        print(f"      Step 2: 调整长度 ({word_count} → {target_words})...")
        time.sleep(0.3)  # 避免 API 限流
        translation = translate_step2_adjust_length(translation, target_words)
        word_count = len(translation.split())
        print(f"      调整后: {word_count} 词 - {translation}")
    else:
        print(f"      长度合适，跳过调整")
    
    # 计算时长
    estimated_duration = word_count / 2.5
    duration_ratio = estimated_duration / duration if duration > 0 else 1.0
    
    return {
        "translation": translation,
        "word_count": word_count,
        "estimated_duration": round(estimated_duration, 2),
        "duration_ratio": round(duration_ratio, 2),
        "success": True
    }

# ===== 主函数 =====
def main():
    print("="*70)
    print("🎬 两步翻译流程（更稳定）")
    print("="*70)
    
    # 读取
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = data[0]
    sentences = result.get("sentence_info", [])
    
    print(f"\n✅ 共 {len(sentences)} 个句子")
    print(f"🤖 模型: {MODEL_NAME}\n")
    
    # 统计
    stats = {"total": 0, "success": 0, "failed": 0, "good_duration": 0}
    translated = []
    
    # 翻译
    for i, sent in enumerate(sentences, 1):
        text_zh = sent.get("text", "").strip()
        start = sent.get("start", 0)
        end = sent.get("end", 0)
        duration = end - start
        
        if not text_zh or duration <= 0:
            continue
        
        print(f"\n[{i}/{len(sentences)}] {duration:.2f}秒")
        print(f"   🇨🇳 {text_zh}")
        
        # 两步翻译
        res = translate_sentence(text_zh, duration)
        
        text_en = res["translation"]
        word_count = res["word_count"]
        est_dur = res["estimated_duration"]
        ratio = res["duration_ratio"]
        success = res["success"]
        
        # 统计
        stats["total"] += 1
        if success:
            stats["success"] += 1
            if abs(ratio - 1.0) <= 0.3:
                stats["good_duration"] += 1
                icon = "✅"
            elif ratio > 1.3:
                icon = "⚠️ 长"
            else:
                icon = "⚠️ 短"
        else:
            stats["failed"] += 1
            icon = "❌"
        
        translated.append({
            "start": start,
            "end": end,
            "duration": round(duration, 2),
            "text_zh": text_zh,
            "text_en": text_en,
            "word_count": word_count,
            "estimated_duration": est_dur,
            "duration_ratio": ratio
        })
        
        print(f"   {icon} 🇬🇧 {text_en}")
        print(f"   📊 {word_count} 词 → {est_dur:.1f}秒 ({ratio:.2f}x)")
        
        time.sleep(0.5)  # 避免 API 限流
    
    # 保存
    output = [{
        "key": result.get("key", "unknown"),
        "sentence_info": translated,
        "metadata": {
            "total": stats["total"],
            "successful": stats["success"],
            "failed": stats["failed"],
            "good_duration": stats["good_duration"],
            "model": MODEL_NAME
        }
    }]
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 总结
    print("\n" + "="*70)
    print("✅ 完成")
    print(f"\n📊 统计:")
    print(f"   成功: {stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.0f}%)")
    print(f"   失败: {stats['failed']}")
    print(f"   时长合适: {stats['good_duration']} ({stats['good_duration']/stats['total']*100:.0f}%)")
    
    # 失败列表
    failed = [s for s in translated if "[FAILED:" in s["text_en"]]
    if failed:
        print(f"\n⚠️  需要手动处理 ({len(failed)} 句):")
        for s in failed:
            print(f"   - [{s['start']:.1f}s] {s['text_zh']}")
    
    print(f"\n💾 已保存到: {OUTPUT_JSON}")
    print("="*70)

if __name__ == "__main__":
    if API_KEY == "your-api-key-here":
        print("⚠️  请配置 API")
    else:
        main()