"""
TTS音频生成模块
使用 Boson AI 语音克隆生成音频
"""

import os
import json
import base64
import subprocess
from openai import OpenAI
from pathlib import Path
import wave
import time


class TTSGenerator:
    """文字转语音生成器 - 使用 Boson AI 语音克隆"""
    
    def __init__(self, api_key=None, api_base=None):
        """
        初始化TTS生成器
        
        Args:
            api_key: API密钥
            api_base: API基础URL
        """
        self.api_key = api_key or os.getenv("BOSON_API_KEY", "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH")
        self.api_base = api_base or "https://hackathon.boson.ai/v1"
        self.model = "higgs-audio-generation-Hackathon"
        
        self.SAMPLE_RATE = 24000
        self.CHANNELS = 1
        self.SAMPLE_WIDTH = 2
        
        self.client = None
    
    def _init_client(self):
        """初始化API客户端"""
        if self.client is not None:
            return
        
        print(f"🔄 初始化 Boson AI TTS 客户端...")
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        print("✅ 客户端初始化完成")
    
    def generate(self, translated_json_path, output_audio_path, target_lang="en", bitrate="192k", original_audio_path=None):
        """
        从翻译的JSON生成完整音频
        
        Args:
            translated_json_path: 翻译后的JSON文件路径
            output_audio_path: 输出音频路径
            target_lang: 目标语言代码
            bitrate: 音频比特率
            original_audio_path: 原始音频路径（用于提取参考音色）
        
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(translated_json_path):
            print(f"❌ 输入文件不存在: {translated_json_path}")
            return False
        
        try:
            # 初始化客户端
            self._init_client()
            
            # 读取翻译数据
            with open(translated_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sentences = data[0].get("sentence_info", [])
            total = len(sentences)
            
            print(f"🔊 开始生成 {total} 个音频片段...")
            
            # 创建临时目录
            temp_dir = Path(output_audio_path).parent / "temp_audio"
            temp_dir.mkdir(exist_ok=True)
            
            # 步骤1: 提取参考音频
            reference_audio = None
            reference_text = None
            
            if original_audio_path and os.path.exists(original_audio_path):
                print("\n🎯 提取参考音色...")
                ref_result = self._find_best_reference(sentences)
                
                if ref_result:
                    ref_idx, ref_sent, ref_duration = ref_result
                    ref_text = ref_sent.get("text", "")
                    ref_start = ref_sent.get("start", 0)
                    
                    reference_audio = str(temp_dir / "reference.wav")
                    
                    if self._extract_reference_audio(original_audio_path, ref_start, ref_duration, reference_audio):
                        reference_text = ref_text
                        print(f"  ✅ 使用参考句子 {ref_idx+1}: {ref_text[:30]}...")
                    else:
                        reference_audio = None
            
            # 步骤2: 生成每个句子的音频
            audio_segments = []
            success_count = 0
            
            for i, sentence in enumerate(sentences, 1):
                # 获取翻译文本
                if target_lang == "en":
                    text = sentence.get("text_en", "")
                else:
                    text = sentence.get("text_translated", "")
                
                start_time = sentence.get("start", 0)
                target_duration = sentence.get("end", 0) - start_time
                
                if not text or "[FAILED:" in text:
                    print(f"  [{i}/{total}] ⏭️  跳过")
                    continue
                
                display = text if len(text) <= 45 else text[:42] + "..."
                print(f"  [{i}/{total}] {display}")
                
                # 生成音频
                raw_output = str(temp_dir / f"raw_{i:03d}.wav")
                final_output = str(temp_dir / f"segment_{i:03d}.wav")
                
                if reference_audio and reference_text:
                    # 使用语音克隆
                    if self._generate_with_voice_cloning(text, reference_audio, reference_text, raw_output):
                        raw_duration = self._get_audio_duration(raw_output)
                        print(f"    🎵 生成: {raw_duration:.1f}s")
                        
                        # 处理音频长度
                        if self._process_audio_length(raw_output, final_output, target_duration):
                            audio_segments.append((start_time, final_output))
                            success_count += 1
                        else:
                            print(f"    ⚠️  处理失败")
                    else:
                        print(f"    ❌ 生成失败")
                else:
                    # 没有参考音频，创建静音
                    if self._create_silence(target_duration, final_output):
                        audio_segments.append((start_time, final_output))
                
                # 避免API限流
                if i < total:
                    time.sleep(0.3)
            
            print(f"\n✅ 音频生成完成: {success_count}/{total}")
            
            # 步骤3: 计算总时长
            if sentences:
                total_duration = sentences[-1].get("end", 0)
            else:
                total_duration = 60
            
            # 步骤4: 按时间轴组装音频
            print("\n🔄 按时间轴组装音频...")
            
            temp_output = str(temp_dir / "assembled.wav")
            
            if self._assemble_audio_timeline(audio_segments, total_duration, temp_output):
                # 转换为MP3格式
                print("🔄 转换为MP3...")
                self._convert_to_mp3(temp_output, output_audio_path, bitrate)
                
                print(f"💾 音频已保存: {output_audio_path}")
                
                # 清理临时文件
                import shutil
                shutil.rmtree(temp_dir)
                
                return True
            else:
                print("❌ 音频组装失败")
                return False
        
        except Exception as e:
            print(f"❌ 音频生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _find_best_reference(self, sentences, min_duration=3.0, max_duration=6.0):
        """找到最适合做参考的句子"""
        candidates = []
        
        for i, sent in enumerate(sentences):
            duration = sent.get("end", 0) - sent.get("start", 0)
            text = sent.get("text", "")
            
            if min_duration <= duration <= max_duration and len(text) > 8:
                candidates.append((i, sent, duration))
        
        if not candidates:
            candidates = sorted(
                [(i, s, s.get("end", 0) - s.get("start", 0)) for i, s in enumerate(sentences)],
                key=lambda x: x[2],
                reverse=True
            )[:3]
        
        if candidates:
            return candidates[0]
        return None
    
    def _extract_reference_audio(self, input_audio, start, duration, output_path):
        """从原视频提取参考音频"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_audio,
                "-ss", str(start),
                "-t", str(duration),
                "-ar", str(self.SAMPLE_RATE),
                "-ac", str(self.CHANNELS),
                output_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False
    
    def _generate_with_voice_cloning(self, text, reference_audio, reference_text, output_path, max_retries=2):
        """使用语音克隆生成音频"""
        for attempt in range(max_retries):
            try:
                # 读取参考音频并编码为base64
                with open(reference_audio, "rb") as f:
                    ref_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                # 调用API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": reference_text},
                        {
                            "role": "assistant",
                            "content": [{
                                "type": "input_audio",
                                "input_audio": {
                                    "data": ref_b64,
                                    "format": "wav"
                                }
                            }]
                        },
                        {"role": "user", "content": text}
                    ],
                    modalities=["text", "audio"],
                    max_completion_tokens=4096,
                    temperature=0.85,
                    top_p=0.9,
                    stream=False,
                    stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
                    extra_body={"top_k": 40}
                )
                
                # 获取生成的音频
                if hasattr(response.choices[0].message, 'audio') and response.choices[0].message.audio:
                    audio_b64 = response.choices[0].message.audio.data
                    audio_data = base64.b64decode(audio_b64)
                    
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    
                    # 检查音频时长是否异常
                    duration = self._get_audio_duration(output_path)
                    
                    if duration > 30:  # 异常长音频
                        if attempt < max_retries - 1:
                            print(f"    ⚠️  异常长音频({duration:.1f}s)，重试...")
                            time.sleep(1)
                            continue
                    
                    return True
                
                return False
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    ⚠️  生成失败，重试...")
                    time.sleep(1)
                else:
                    print(f"    ❌ {str(e)[:80]}")
                    return False
        
        return False
    
    def _process_audio_length(self, raw_audio, output_audio, target_duration):
        """处理生成的音频长度"""
        try:
            duration = self._get_audio_duration(raw_audio)
            
            if duration == 0:
                return False
            
            # 如果音频长度合理，直接使用
            if 0.5 <= duration / target_duration <= 2.0:
                import shutil
                shutil.copy(raw_audio, output_audio)
                return True
            
            # 如果太长，截取
            if duration > target_duration * 2:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", raw_audio,
                    "-t", str(target_duration * 1.2),
                    "-acodec", "copy",
                    output_audio
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            
            # 否则直接使用
            import shutil
            shutil.copy(raw_audio, output_audio)
            return True
        
        except:
            return False
    
    def _create_silence(self, duration_seconds, output_path):
        """创建静音音频"""
        try:
            num_samples = int(duration_seconds * self.SAMPLE_RATE)
            silence_data = b'\x00\x00' * num_samples
            
            with wave.open(output_path, 'wb') as wav:
                wav.setnchannels(self.CHANNELS)
                wav.setsampwidth(self.SAMPLE_WIDTH)
                wav.setframerate(self.SAMPLE_RATE)
                wav.writeframes(silence_data)
            
            return True
        except:
            return False
    
    def _assemble_audio_timeline(self, audio_segments, total_duration, output_path):
        """按时间轴组装音频"""
        try:
            # 按开始时间排序
            audio_segments = sorted(audio_segments, key=lambda x: x[0])
            
            # 创建完整的音频数据
            total_samples = int(total_duration * self.SAMPLE_RATE)
            audio_data = bytearray(b'\x00\x00' * total_samples)
            
            # 插入每个音频片段
            for i, (start_time, audio_file) in enumerate(audio_segments, 1):
                if not os.path.exists(audio_file):
                    continue
                
                try:
                    with wave.open(audio_file, 'rb') as wav:
                        if wav.getnchannels() != self.CHANNELS or wav.getframerate() != self.SAMPLE_RATE:
                            continue
                        
                        frames = wav.readframes(wav.getnframes())
                    
                    # 计算插入位置
                    start_sample = int(start_time * self.SAMPLE_RATE)
                    start_byte = start_sample * self.SAMPLE_WIDTH
                    end_byte = start_byte + len(frames)
                    
                    if end_byte > len(audio_data):
                        frames = frames[:len(audio_data) - start_byte]
                        end_byte = len(audio_data)
                    
                    audio_data[start_byte:end_byte] = frames
                    
                except:
                    continue
            
            # 写入最终文件
            with wave.open(output_path, 'wb') as wav:
                wav.setnchannels(self.CHANNELS)
                wav.setsampwidth(self.SAMPLE_WIDTH)
                wav.setframerate(self.SAMPLE_RATE)
                wav.writeframes(bytes(audio_data))
            
            return True
        
        except:
            return False
    
    def _get_audio_duration(self, audio_path):
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
    
    def _convert_to_mp3(self, input_wav, output_mp3, bitrate="192k"):
        """将WAV转换为MP3"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_wav,
                "-acodec", "libmp3lame",
                "-ab", bitrate,
                output_mp3
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False