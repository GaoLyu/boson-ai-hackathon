from funasr import AutoModel
import os
import json

# ✅ 方案1: 使用简化的模型名称
print("正在加载模型...")
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    # 尝试使用简化名称
    alignment_model="fa-zh",  # 或者试试 "mfa"
    disable_update=True
)

# 输入音频路径
audio_path = "/Users/lyugao/Documents/GitHub/boson-ai-hackathon/sleep.mp3"
assert os.path.exists(audio_path), f"音频文件不存在: {audio_path}"

# 调用模型 - 添加更多参数
print("开始处理音频...")
res = model.generate(
    input=[audio_path],
    batch_size_s=300,
    return_raw_text=False,
    sentence_timestamp=True,  # 显式要求句子时间戳
)

print("\n=== 原始输出 ===")
print(json.dumps(res, ensure_ascii=False, indent=2))

# 检查输出结构
if isinstance(res, list) and len(res) > 0:
    result = res[0]
    
    # 检查是否有 sentence_info
    if "sentence_info" in result:
        print("\n✅ 成功获取句子级时间戳！\n")
        print("=== 句子时间戳 ===\n")
        for seg in result["sentence_info"]:
            start = seg.get("start", 0) / 1000  # 转换为秒
            end = seg.get("end", 0) / 1000
            text = seg.get("text", "")
            print(f"[{start:.2f}s - {end:.2f}s] {text}")
    else:
        print("\n⚠️ 未检测到 sentence_info 字段")
        print("可用的字段:", list(result.keys()))
        
        # 尝试从 timestamp 手动构建句子信息
        if "timestamp" in result and "text" in result:
            print("\n尝试从现有 timestamp 构建句子信息...")
            text = result["text"]
            timestamps = result["timestamp"]
            
            # 按标点符号分割句子
            import re
            sentences = re.split(r'([。！？])', text)
            sentences = [''.join(i) for i in zip(sentences[0::2], sentences[1::2])]
            
            print("\n=== 手动分割的句子（基于字级时间戳） ===\n")
            char_idx = 0
            for sentence in sentences:
                if sentence.strip():
                    start_ms = timestamps[char_idx][0] if char_idx < len(timestamps) else 0
                    char_idx += len(sentence)
                    end_ms = timestamps[min(char_idx-1, len(timestamps)-1)][1] if char_idx <= len(timestamps) else 0
                    print(f"[{start_ms/1000:.2f}s - {end_ms/1000:.2f}s] {sentence}")
else:
    print("\n❌ 输出格式异常")

