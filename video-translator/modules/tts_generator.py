"""
TTS音频生成模块（增强版）
功能：
1. 语音克隆（使用原视频音色）
2. 预设声音（女声、男声等）
3. 人声背景分离
4. 时长精确对齐
"""

import os
import json
import base64
import subprocess
from openai import OpenAI
from pathlib import Path
import wave
import time
import tempfile
import shutil
import numpy as np


class TTSGenerator:
    """文字转语音生成器 - 增强版"""
    
    # 预设声音配置
    PRESET_VOICES = {
        "female_american": {
            "name": "美式女声（清晰温暖）",
            "system_prompt": (
                "You are an English text-to-speech (TTS) model. "
                "Always use the same clear, warm female American English voice. "
                "Speak naturally, fluently, and consistently across all generations. "
                "Do not include any background noise, effects, or non-speech sounds."
            ),
            "temperature": 0.4
        },
        "female_british": {
            "name": "英式女声（优雅）",
            "system_prompt": (
                "You are an English text-to-speech model. "
                "Use a clear, elegant female British English voice with RP accent. "
                "Speak naturally and fluently. "
                "No background noise or effects."
            ),
            "temperature": 0.4
        },
        "male_american": {
            "name": "美式男声（沉稳）",
            "system_prompt": (
                "You are an English text-to-speech model. "
                "Use a deep, steady male American English voice. "
                "Speak clearly and professionally. "
                "No background noise or effects."
            ),
            "temperature": 0.4
        },
        "male_british": {
            "name": "英式男声（磁性）",
            "system_prompt": (
                "You are an English text-to-speech model. "
                "Use a deep, smooth male British English voice. "
                "Speak with clarity and warmth. "
                "No background noise or effects."
            ),
            "temperature": 0.4
        }
    }
    
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
    
    def generate(self, translated_json_path, output_audio_path, target_lang="en", 
                 bitrate="192k", original_audio_path=None, 
                 voice_mode="clone", preset_voice="female_american",
                 separate_vocals=False, keep_background=True, bgm_volume=0.18):
        """
        从翻译的JSON生成完整音频
        
        Args:
            translated_json_path: 翻译后的JSON文件路径
            output_audio_path: 输出音频路径
            target_lang: 目标语言代码
            bitrate: 音频比特率
            original_audio_path: 原始音频路径（用于语音克隆或背景音提取）
            voice_mode: 声音模式 ("clone" 克隆原音 / "preset" 使用预设声音)
            preset_voice: 预设声音类型（当voice_mode="preset"时使用）
            separate_vocals: 是否分离人声和背景音
            keep_background: 是否保留背景音
            bgm_volume: 背景音音量 (0.0-1.0)
        
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
            
            print("=" * 80)
            print(f"🔊 开始生成 {total} 个音频片段...")
            print(f"🎤 声音模式: {voice_mode}")
            if voice_mode == "preset":
                print(f"🎵 预设声音: {self.PRESET_VOICES[preset_voice]['name']}")
            print("=" * 80)
            
            # 创建临时目录
            temp_dir = Path(output_audio_path).parent / "temp_audio"
            temp_dir.mkdir(exist_ok=True)
            
            # 步骤1: 处理原始音频（分离人声/提取参考）
            reference_audio = None
            reference_text = None
            bgm_path = None
            
            if original_audio_path and os.path.exists(original_audio_path):
                if voice_mode == "clone":
                    # 克隆模式：提取参考音频
                    print("\n🎯 步骤 1: 提取参考音色（克隆模式）")
                    print("-" * 80)
                    
                    if separate_vocals:
                        # 先分离人声
                        print("🎧 分离人声和背景音...")
                        vocals_path, bgm_path = self._separate_audio(
                            original_audio_path, 
                            str(temp_dir)
                        )
                        if vocals_path:
                            print(f"✅ 人声轨: {vocals_path}")
                            source_for_reference = vocals_path
                        else:
                            print("⚠️  人声分离失败，使用原音频")
                            source_for_reference = original_audio_path
                    else:
                        source_for_reference = original_audio_path
                    
                    # 从人声轨（或原音频）提取参考片段
                    ref_result = self._find_best_reference(sentences)
                    if ref_result:
                        ref_idx, ref_sent, ref_duration = ref_result
                        ref_text = ref_sent.get("text", "")
                        ref_start = ref_sent.get("start", 0)
                        
                        reference_audio = str(temp_dir / "reference.wav")
                        
                        if self._extract_reference_audio(source_for_reference, ref_start, ref_duration, reference_audio):
                            reference_text = ref_text
                            print(f"✅ 使用参考句子 {ref_idx+1}: {ref_text[:30]}...")
                        else:
                            reference_audio = None
                
                elif separate_vocals and keep_background:
                    # 预设声音模式但需要保留背景音
                    print("\n🎧 步骤 1: 提取背景音")
                    print("-" * 80)
                    _, bgm_path = self._separate_audio(original_audio_path, str(temp_dir))
                    if bgm_path:
                        print(f"✅ 背景音: {bgm_path}")
            
            # 步骤2: 生成每个句子的音频
            print("\n🎤 步骤 2: 生成音频片段")
            print("-" * 80)
            
            audio_segments = []
            success_count = 0
            
            for i, sentence in enumerate(sentences, 1):
                # 获取翻译文本
                if target_lang == "en":
                    text = sentence.get("text_en", "")
                else:
                    text = sentence.get("text_translated", "")
                
                start_time = sentence.get("start", 0)
                end_time = sentence.get("end", 0)
                target_duration = end_time - start_time
                
                if not text or "[FAILED:" in text:
                    print(f"  [{i}/{total}] ⏭️  跳过")
                    continue
                
                display = text if len(text) <= 45 else text[:42] + "..."
                print(f"  [{i}/{total}] {display}")
                
                # 生成音频
                raw_output = str(temp_dir / f"raw_{i:03d}.wav")
                final_output = str(temp_dir / f"segment_{i:03d}.wav")
                
                if voice_mode == "clone" and reference_audio and reference_text:
                    # 使用语音克隆
                    if self._generate_with_voice_cloning(text, reference_audio, reference_text, raw_output):
                        raw_duration = self._get_audio_duration(raw_output)
                        print(f"    🎵 生成: {raw_duration:.1f}s")
                        
                        # 调整时长
                        if self._align_audio_duration(raw_output, target_duration, final_output):
                            audio_segments.append((start_time, final_output))
                            success_count += 1
                        else:
                            print(f"    ⚠️  时长调整失败")
                    else:
                        print(f"    ❌ 生成失败")
                
                elif voice_mode == "preset":
                    # 使用预设声音
                    if self._generate_with_preset_voice(text, preset_voice, raw_output):
                        raw_duration = self._get_audio_duration(raw_output)
                        print(f"    🎵 生成: {raw_duration:.1f}s")
                        
                        # 调整时长
                        if self._align_audio_duration(raw_output, target_duration, final_output):
                            audio_segments.append((start_time, final_output))
                            success_count += 1
                        else:
                            print(f"    ⚠️  时长调整失败")
                    else:
                        print(f"    ❌ 生成失败")
                else:
                    # 创建静音（降级处理）
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
            print("\n🔄 步骤 3: 按时间轴组装音频")
            print("-" * 80)
            
            speech_only = str(temp_dir / "speech_only.wav")
            
            if self._assemble_audio_timeline(audio_segments, total_duration, speech_only):
                print(f"✅ 语音轨道完成: {speech_only}")
                
                # 步骤5: 混合背景音（如果需要）
                if keep_background and bgm_path and os.path.exists(bgm_path):
                    print("\n🎵 步骤 4: 混合背景音")
                    print("-" * 80)
                    
                    temp_output = str(temp_dir / "with_bgm.wav")
                    if self._mix_audio_with_bgm(speech_only, bgm_path, temp_output, bgm_volume):
                        speech_only = temp_output
                        print(f"✅ 背景音混合完成")
                
                # 转换为MP3格式
                print("\n🔄 步骤 5: 转换为MP3")
                print("-" * 80)
                self._convert_to_mp3(speech_only, output_audio_path, bitrate)
                
                print(f"💾 音频已保存: {output_audio_path}")
                print("=" * 80)
                
                # 清理临时文件
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
    
    def _separate_audio(self, input_audio, output_dir):
        """
        使用 Demucs 分离人声和背景音
        
        Returns:
            tuple: (vocals_path, bgm_path)
        """
        try:
            # 检查 demucs 是否安装
            subprocess.run(
                ["demucs", "--help"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                check=True
            )
        except:
            print("⚠️  Demucs 未安装，跳过人声分离")
            print("   提示: pip install demucs")
            return None, None
        
        try:
            audio_name = Path(input_audio).stem
            
            # 执行分离
            subprocess.run(
                ["demucs", "-n", "htdemucs", "--two-stems=vocals", input_audio],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 构建输出路径
            separated_root = Path("separated") / "htdemucs" / audio_name
            vocals = separated_root / "vocals.wav"
            bgm = separated_root / "no_vocals.wav"
            
            # 复制到统一输出目录
            final_vocals = Path(output_dir) / "vocals.wav"
            final_bgm = Path(output_dir) / "accompaniment.wav"
            
            if vocals.exists():
                shutil.copy(vocals, final_vocals)
            else:
                final_vocals = None
            
            if bgm.exists():
                shutil.copy(bgm, final_bgm)
            else:
                final_bgm = None
            
            return str(final_vocals) if final_vocals else None, str(final_bgm) if final_bgm else None
        
        except Exception as e:
            print(f"⚠️  人声分离失败: {e}")
            return None, None
    
    def _generate_with_preset_voice(self, text, voice_type, output_path, max_retries=10):
        """使用预设声音生成音频"""
        if not text.strip():
            return False
        
        voice_config = self.PRESET_VOICES.get(voice_type, self.PRESET_VOICES["female_american"])
        
        for attempt in range(max_retries):
            try:
                # 记录开始时间
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": voice_config["system_prompt"]
                        },
                        {"role": "user", "content": text.strip()}
                    ],
                    modalities=["text", "audio"],
                    max_completion_tokens=2048,
                    temperature=voice_config["temperature"],
                    top_p=0.9,
                    stream=False,
                    timeout=30  # 添加30秒超时
                )
                
                # 计算生成时间
                generation_time = time.time() - start_time
                
                audio_b64 = getattr(response.choices[0].message.audio, "data", None)
                if not audio_b64:
                    if attempt < max_retries - 1:
                        print(f"    ⚠️  无音频响应，{attempt+1}/{max_retries} 次重试...")
                        time.sleep(3)
                        continue
                    return False
                
                tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                with open(tmp_output, "wb") as f:
                    f.write(base64.b64decode(audio_b64))
                
                duration = self._get_audio_duration(tmp_output)
                
                # 检查生成是否异常
                # 1. 音频时长异常（太长或太短）
                if duration > 20 or duration < 0.5:
                    os.remove(tmp_output)
                    if attempt < max_retries - 1:
                        print(f"    ⚠️  异常时长 {duration:.1f}s，重新生成...")
                        time.sleep(3)
                        continue
                    return False
                
                # 2. 生成时间异常（超过30秒）
                if generation_time > 30:
                    print(f"    ⚠️  生成时间过长 ({generation_time:.1f}s)，可能存在问题")
                    # 但如果音频看起来正常，还是使用它
                    if duration < 1 or duration > 15:
                        os.remove(tmp_output)
                        if attempt < max_retries - 1:
                            print(f"    ⚠️  重新生成...")
                            time.sleep(3)
                            continue
                        return False
                
                os.rename(tmp_output, output_path)
                return True
            
            except TimeoutError:
                print(f"    ⚠️  请求超时，{attempt+1}/{max_retries} 次重试...")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return False
            
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"    ⚠️  超时错误，{attempt+1}/{max_retries} 次重试...")
                elif attempt < max_retries - 1:
                    print(f"    ⚠️  错误: {error_msg[:60]}，重试中...")
                else:
                    print(f"    ❌ 错误: {error_msg[:60]}")
                    return False
                
                if attempt < max_retries - 1:
                    time.sleep(3)
        
        return False
    
    def _align_audio_duration(self, input_file, target_duration, output_file):
        """调整音频时长以精确对齐"""
        try:
            actual_duration = self._get_audio_duration(input_file)
            
            if actual_duration <= 0:
                return False
            
            ratio = target_duration / actual_duration
            
            # 如果长度接近，直接使用
            if 0.9 <= ratio <= 1.1:
                shutil.copy(input_file, output_file)
                return True
            
            # 需要调速
            if 0.5 < ratio < 2.0:
                speed = 1.0 / ratio
                return self._change_audio_speed(input_file, output_file, speed)
            
            # 长度差异太大，补静音或截断
            if ratio >= 2.0:
                return self._pad_silence(input_file, output_file, target_duration - actual_duration)
            else:
                # 截断
                shutil.copy(input_file, output_file)
                return True
        
        except:
            return False
    
    def _change_audio_speed(self, input_file, output_file, speed):
        """改变音频播放速度"""
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_file, "-filter:a", f"atempo={speed}", output_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except:
            return False
    
    def _pad_silence(self, input_file, output_file, pad_seconds):
        """在音频后补静音"""
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_file, "-af", f"apad=pad_dur={pad_seconds}", output_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except:
            return False
    
    def _mix_audio_with_bgm(self, speech, bgm, output_path, volume=0.2):
        """混合语音和背景音"""
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", speech,
                    "-i", bgm,
                    "-filter_complex",
                    f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first",
                    output_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except:
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
    
    def _generate_with_voice_cloning(self, text, reference_audio, reference_text, output_path, max_retries=3):
        """使用语音克隆生成音频"""
        for attempt in range(max_retries):
            try:
                # 记录开始时间
                start_time = time.time()
                
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
                    extra_body={"top_k": 40},
                    timeout=45  # 添加45秒超时
                )
                
                # 计算生成时间
                generation_time = time.time() - start_time
                
                # 获取生成的音频
                if hasattr(response.choices[0].message, 'audio') and response.choices[0].message.audio:
                    audio_b64 = response.choices[0].message.audio.data
                    audio_data = base64.b64decode(audio_b64)
                    
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    
                    # 检查音频时长是否异常
                    duration = self._get_audio_duration(output_path)
                    
                    # 检查生成是否异常
                    # 1. 音频时长异常
                    if duration > 30:
                        print(f"    ⚠️  异常时长 {duration:.1f}s")
                        if attempt < max_retries - 1:
                            print(f"    ⚠️  重新生成...")
                            time.sleep(2)
                            continue
                    
                    # 2. 生成时间异常（超过45秒）
                    if generation_time > 45:
                        print(f"    ⚠️  生成时间过长 ({generation_time:.1f}s)")
                        # 但如果音频看起来正常，还是使用它
                        if duration < 1 or duration > 20:
                            if attempt < max_retries - 1:
                                print(f"    ⚠️  重新生成...")
                                time.sleep(2)
                                continue
                    
                    return True
                
                # 没有音频响应
                if attempt < max_retries - 1:
                    print(f"    ⚠️  无音频响应，{attempt+1}/{max_retries} 次重试...")
                    time.sleep(2)
                    continue
                
                return False
            
            except TimeoutError:
                print(f"    ⚠️  克隆超时，{attempt+1}/{max_retries} 次重试...")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    return False
            
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"    ⚠️  超时错误，{attempt+1}/{max_retries} 次重试...")
                elif attempt < max_retries - 1:
                    print(f"    ⚠️  错误: {error_msg[:60]}，重试中...")
                else:
                    print(f"    ❌ 克隆失败: {error_msg[:60]}")
                    return False
                
                if attempt < max_retries - 1:
                    time.sleep(2)
        
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