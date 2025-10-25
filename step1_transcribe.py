from funasr import AutoModel
import os
import json
import re

# ===== Step 1: 配置区域 =====
AUDIO_PATH = "/Users/fiona/boson-ai-hackathon/sleep.mp3"
OUTPUT_FILE = "transcription_with_timestamps.json"

# ===== 加载模型 =====
print("正在加载 FunASR 模型...")
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    alignment_model="fa-zh",  # 尝试简化名称
    disable_update=True
)

# ===== 检查音频文件 =====
assert os.path.exists(AUDIO_PATH), f"❌ 音频文件不存在: {AUDIO_PATH}"
print(f"✅ 音频文件: {AUDIO_PATH}")

# ===== 语音识别 + 时间戳对齐 =====
print("\n开始处理音频...")
res = model.generate(
    input=[AUDIO_PATH],
    batch_size_s=300,
    return_raw_text=False,
    sentence_timestamp=True,
)

print("\n" + "="*60)
print("原始输出预览:")
print("="*60)
print(json.dumps(res, ensure_ascii=False, indent=2)[:500] + "...")

# ===== 处理和保存结果 =====
if isinstance(res, list) and len(res) > 0:
    result = res[0]
    
    # 情况 1: 已经有 sentence_info（最理想）
    if "sentence_info" in result:
        print("\n✅ 成功获取句子级时间戳！")
        
        # 转换时间戳格式（毫秒 -> 秒）
        for sentence in result["sentence_info"]:
            if "start" in sentence:
                sentence["start"] = sentence["start"] / 1000
            if "end" in sentence:
                sentence["end"] = sentence["end"] / 1000
        
        print(f"📊 识别到 {len(result['sentence_info'])} 个句子\n")
        
        # 显示前3个句子
        print("句子示例:")
        print("-" * 60)
        for i, seg in enumerate(result["sentence_info"][:], 1):
            print(f"{i}. [{seg['start']:.2f}s - {seg['end']:.2f}s]")
            print(f"   {seg['text']}\n")
        
        # 保存到文件
        print(f"💾 保存到: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存 {len(result['sentence_info'])} 个句子")
    
    # 情况 2: 没有 sentence_info，需要手动构建
    else:
        print("\n⚠️ 未检测到 sentence_info，尝试手动构建...")
        
        if "timestamp" in result and "text" in result:
            text = result["text"]
            timestamps = result["timestamp"]
            
            # 按标点符号分割句子
            sentences = re.split(r'([。！？.!?])', text)
            sentences = [s1 + s2 for s1, s2 in zip(sentences[0::2], sentences[1::2])]
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # 构建 sentence_info
            sentence_info = []
            char_idx = 0
            
            for sentence in sentences:
                if not sentence:
                    continue
                
                # 找到这个句子的字符范围
                start_char = char_idx
                end_char = char_idx + len(sentence)
                
                # 获取时间戳（毫秒转秒）
                if start_char < len(timestamps):
                    start_time = timestamps[start_char][0] / 1000
                else:
                    start_time = 0
                
                if end_char - 1 < len(timestamps):
                    end_time = timestamps[end_char - 1][1] / 1000
                else:
                    end_time = timestamps[-1][1] / 1000 if timestamps else 0
                
                sentence_info.append({
                    "start": start_time,
                    "end": end_time,
                    "text": sentence
                })
                
                char_idx = end_char
            
            # 更新结果
            result["sentence_info"] = sentence_info
            
            print(f"✅ 手动构建了 {len(sentence_info)} 个句子")
            print("\n句子示例:")
            print("-" * 60)
            for i, seg in enumerate(sentence_info[:], 1):
                print(f"{i}. [{seg['start']:.2f}s - {seg['end']:.2f}s]")
                print(f"   {seg['text']}\n")
            
            # 保存到文件
            print(f"💾 保存到: {OUTPUT_FILE}")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump([result], f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已保存 {len(sentence_info)} 个句子")
        else:
            print("❌ 无法构建句子信息：缺少必要字段")
            print("可用字段:", list(result.keys()))
else:
    print("❌ 输出格式异常")

print("\n" + "="*60)
print("🎉 Step 1 完成！")
print(f"📄 输出文件: {OUTPUT_FILE}")
print("\n📋 下一步：运行翻译脚本")
print("   python step2_translate.py")
print("="*60)