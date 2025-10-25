"""
语音识别模块
使用FunASR进行语音识别并生成带时间戳的转录文本
"""

import os
import json
import re


class Transcriber:
    """语音识别器"""
    
    def __init__(self):
        """初始化识别器"""
        self.model = None
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            print("🔄 正在加载 FunASR 模型...")
            try:
                from funasr import AutoModel
                self.model = AutoModel(
                    model="paraformer-zh",
                    vad_model="fsmn-vad",
                    punc_model="ct-punc",
                    alignment_model="fa-zh",
                    disable_update=True
                )
                print("✅ 模型加载完成")
            except Exception as e:
                print(f"❌ 模型加载失败: {e}")
                raise
    
    def transcribe(self, audio_path, output_json_path):
        """
        执行语音识别
        
        Args:
            audio_path: 音频文件路径
            output_json_path: 输出JSON路径
        
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(audio_path):
            print(f"❌ 音频文件不存在: {audio_path}")
            return False
        
        try:
            # 加载模型
            self._load_model()
            
            # 执行识别
            print("🎤 开始语音识别...")
            res = self.model.generate(
                input=[audio_path],
                batch_size_s=300,
                return_raw_text=False,
                sentence_timestamp=True,
            )
            
            # 处理结果
            if isinstance(res, list) and len(res) > 0:
                result = res[0]
                
                # 情况 1: 已经有 sentence_info
                if "sentence_info" in result:
                    print(f"✅ 识别到 {len(result['sentence_info'])} 个句子")
                    
                    # 转换时间戳格式（毫秒 -> 秒）
                    for sentence in result["sentence_info"]:
                        if "start" in sentence:
                            sentence["start"] = sentence["start"] / 1000
                        if "end" in sentence:
                            sentence["end"] = sentence["end"] / 1000
                
                # 情况 2: 需要手动构建 sentence_info
                elif "timestamp" in result and "text" in result:
                    print("⚠️ 手动构建 sentence_info...")
                    result["sentence_info"] = self._build_sentence_info(
                        result["text"],
                        result["timestamp"]
                    )
                    print(f"✅ 构建了 {len(result['sentence_info'])} 个句子")
                
                else:
                    print("❌ 无法提取句子信息")
                    return False
                
                # 保存结果
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
                
                print(f"💾 识别结果已保存: {output_json_path}")
                return True
            
            else:
                print("❌ 识别结果为空")
                return False
        
        except Exception as e:
            print(f"❌ 语音识别失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _build_sentence_info(self, text, timestamps):
        """手动构建句子信息"""
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
                end_time = start_time + 1
            
            sentence_info.append({
                "text": sentence,
                "start": start_time,
                "end": end_time
            })
            
            char_idx = end_char
        
        return sentence_info