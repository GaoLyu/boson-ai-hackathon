import json
import os
import base64
import subprocess
from openai import OpenAI
from pathlib import Path
import wave
import struct
import time

# ===== 配置 =====
API_BASE = "https://hackathon.boson.ai/v1"
API_KEY = os.getenv("BOSON_API_KEY", "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH")

INPUT_JSON = "translated_with_timestamps.json"
ORIGINAL_AUDIO = "sleep.mp3"
OUTPUT_DIR = "generated_audio"
FINAL_OUTPUT = "final_english_audio.wav"

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def b64_encode(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

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

def extract_audio_segment(input_file, output_file, start_time, duration=None):
    """从音频中提取片段"""
    try:
        cmd = ["ffmpeg", "-y", "-i", input_file, "-ss", str(start_time)]
        if duration:
            cmd.extend(["-t", str(duration)])
        cmd.extend(["-acodec", "copy", output_file])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def extract_reference_audio(original_audio, start, duration, output_path):
    """从原视频提取参考音频"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", original_audio,
            "-ss", str(start),
            "-t", str(duration),
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def find_best_reference(sentences, min_duration=3.0, max_duration=6.0):
    """找到最适合做参考的句子"""
    candidates = []
    
    for i, sent in enumerate(sentences):
        duration = sent.get("duration", 0)
        text = sent.get("text_zh", "")
        
        if min_duration <= duration <= max_duration and len(text) > 8:
            candidates.append((i, sent, duration))
    
    if not candidates:
        candidates = sorted(
            [(i, s, s.get("duration", 0)) for i, s in enumerate(sentences)],
            key=lambda x: x[2],
            reverse=True
        )[:3]
    
    if candidates:
        return candidates[0]
    return None

def generate_with_voice_cloning(text_en, reference_audio, reference_text, output_raw, max_retries=2):
    """
    使用语音克隆生成音频
    添加重试机制处理异常长音频
    """
    for attempt in range(max_retries):
        try:
            ref_b64 = b64_encode(reference_audio)
            
            response = client.chat.completions.create(
                model="higgs-audio-generation-Hackathon",
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
                    {"role": "user", "content": text_en}
                ],
                modalities=["text", "audio"],
                max_completion_tokens=4096,
                temperature=0.85,
                top_p=0.9,
                stream=False,
                stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
                extra_body={"top_k": 40}
            )
            
            if hasattr(response.choices[0].message, 'audio') and response.choices[0].message.audio:
                audio_b64 = response.choices[0].message.audio.data
                audio_data = base64.b64decode(audio_b64)
                
                with open(output_raw, "wb") as f:
                    f.write(audio_data)
                
                # 检查音频时长是否异常
                duration = get_audio_duration(output_raw)
                
                # 如果音频超过30秒，很可能是幻觉
                if duration > 30:
                    if attempt < max_retries - 1:
                        print(f"  ⚠️  异常长音频({duration:.1f}s)，重试 {attempt + 1}/{max_retries - 1}...")
                        time.sleep(1)
                        continue
                    else:
                        print(f"  ⚠️  多次异常，可能需要手动处理")
                
                return True
            
            return False
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️  生成失败，重试 {attempt + 1}/{max_retries - 1}...")
                time.sleep(1)
            else:
                print(f"  ❌ {str(e)[:80]}")
                return False
    
    return False

def check_and_process_audio(raw_audio, output_audio, reference_duration, target_duration):
    """检查并处理生成的音频，包括异常检测"""
    try:
        total_duration = get_audio_duration(raw_audio)
        
        if total_duration == 0:
            return False
        
        # 异常检测：如果音频超过预期太多，尝试只保留开头部分
        if total_duration > target_duration * 10:  # 超过10倍
            print(f"  🚨 异常长音频({total_duration:.1f}s)，截取前{target_duration*1.5:.1f}秒...")
            
            # 只保留前面合理长度的部分
            max_duration = target_duration * 1.5
            if extract_audio_segment(raw_audio, output_audio, 0, max_duration):
                extracted_duration = get_audio_duration(output_audio)
                print(f"  ✂️  截取后: {extracted_duration:.1f}s")
                return True
            else:
                return False
        
        # 判断是否包含参考音频
        contains_reference = total_duration > (reference_duration + target_duration * 0.5)
        
        if contains_reference:
            print(f"  📏 长音频({total_duration:.1f}s)，提取有效部分...")
            start_time = max(reference_duration - 0.3, 0)
            
            if extract_audio_segment(raw_audio, output_audio, start_time):
                extracted_duration = get_audio_duration(output_audio)
                
                # 如果提取后还是太长，再次截断
                if extracted_duration > target_duration * 3:
                    print(f"  ⚠️  提取后仍然太长({extracted_duration:.1f}s)，继续截取...")
                    temp_file = output_audio.replace(".wav", "_temp.wav")
                    os.rename(output_audio, temp_file)
                    
                    if extract_audio_segment(temp_file, output_audio, 0, target_duration * 1.5):
                        os.remove(temp_file)
                        extracted_duration = get_audio_duration(output_audio)
                        print(f"  ✂️  最终: {extracted_duration:.1f}s")
                    else:
                        os.rename(temp_file, output_audio)
                
                return True
            else:
                return False
        else:
            print(f"  ✅ 正常({total_duration:.1f}s)，直接使用")
            import shutil
            shutil.copy(raw_audio, output_audio)
            return True
        
    except Exception as e:
        print(f"  ⚠️ {e}")
        return False

def create_silence(duration_seconds, output_path):
    """创建指定时长的静音WAV文件"""
    try:
        # 计算样本数
        num_samples = int(duration_seconds * SAMPLE_RATE)
        
        # 创建静音数据（全0）
        silence_data = b'\x00\x00' * num_samples  # 16-bit samples
        
        # 写入WAV文件
        with wave.open(output_path, 'wb') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(silence_data)
        
        return True
    except Exception as e:
        print(f"  ⚠️ 创建静音失败: {e}")
        return False

def assemble_audio_timeline(audio_segments, total_duration, output_path):
    """
    按时间轴组装音频
    
    参数:
        audio_segments: [(start_time, audio_file), ...]
        total_duration: 总时长（秒）
        output_path: 输出文件
    """
    print("\n🎬 按时间轴组装音频...")
    print(f"   总时长: {total_duration:.1f}秒")
    print(f"   片段数: {len(audio_segments)}")
    
    try:
        # 按开始时间排序
        audio_segments = sorted(audio_segments, key=lambda x: x[0])
        
        # 创建完整的音频数据
        total_samples = int(total_duration * SAMPLE_RATE)
        
        # 初始化为静音
        print("  📝 创建时间轴...")
        audio_data = bytearray(b'\x00\x00' * total_samples)
        
        # 插入每个音频片段
        for i, (start_time, audio_file) in enumerate(audio_segments, 1):
            if not os.path.exists(audio_file):
                print(f"  ⚠️  跳过: {audio_file} (不存在)")
                continue
            
            try:
                # 读取音频片段
                with wave.open(audio_file, 'rb') as wav:
                    if wav.getnchannels() != CHANNELS or wav.getframerate() != SAMPLE_RATE:
                        print(f"  ⚠️  跳过: {audio_file} (格式不匹配)")
                        continue
                    
                    frames = wav.readframes(wav.getnframes())
                
                # 计算插入位置
                start_sample = int(start_time * SAMPLE_RATE)
                start_byte = start_sample * SAMPLE_WIDTH
                
                # 插入数据
                end_byte = start_byte + len(frames)
                
                if end_byte > len(audio_data):
                    # 截断超出部分
                    frames = frames[:len(audio_data) - start_byte]
                    end_byte = len(audio_data)
                
                audio_data[start_byte:end_byte] = frames
                
                duration = len(frames) / (SAMPLE_RATE * SAMPLE_WIDTH)
                print(f"  [{i}/{len(audio_segments)}] {start_time:.1f}s: {os.path.basename(audio_file)} ({duration:.1f}s)")
                
            except Exception as e:
                print(f"  ⚠️  处理失败: {audio_file} - {e}")
                continue
        
        # 写入最终文件
        print(f"  💾 写入文件...")
        with wave.open(output_path, 'wb') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(bytes(audio_data))
        
        print(f"  ✅ 组装完成: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ 组装失败: {e}")
        return False

def add_background_music(speech, music, output, volume=0.15):
    """添加背景音乐"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", speech,
            "-i", music,
            "-filter_complex",
            f"[1:a]volume={volume}[m];[0:a][m]amix=inputs=2:duration=first",
            output
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def extract_background_music(original_audio, output):
    """从原音频提取背景音乐"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", original_audio,
            "-af", "highpass=f=200,lowpass=f=3000,volume=0.3",
            output
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def main():
    print("="*80)
    print("🎤 Step 3: 英文音频生成（时间轴精确对齐）")
    print("="*80)
    
    ensure_dir(OUTPUT_DIR)
    
    # 读取翻译
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        print(f"❌ 找不到: {INPUT_JSON}")
        return
    
    sentences = data[0].get("sentence_info", [])
    print(f"\n✅ 加载 {len(sentences)} 个句子")
    
    # 检查原音频
    if not os.path.exists(ORIGINAL_AUDIO):
        print(f"❌ 找不到原音频: {ORIGINAL_AUDIO}")
        return
    
    print(f"✅ 原音频: {ORIGINAL_AUDIO}")
    
    # 计算总时长
    if sentences:
        last_sentence = sentences[-1]
        total_duration = last_sentence.get("end", 0)
        print(f"✅ 总时长: {total_duration:.1f}秒\n")
    else:
        print("❌ 没有句子数据")
        return
    
    # 步骤1: 提取参考音频
    print("="*80)
    print("🎯 步骤 1/3: 提取参考音色")
    print("="*80)
    
    result = find_best_reference(sentences)
    
    if not result:
        print("❌ 无法找到合适的参考句子")
        return
    
    ref_idx, ref_sent, ref_duration = result
    ref_text = ref_sent.get("text_zh", "")
    ref_start = ref_sent.get("start", 0)
    
    print(f"\n选择句子 {ref_idx+1}:")
    print(f"  文本: {ref_text}")
    print(f"  时长: {ref_duration:.2f}秒")
    print(f"  位置: {ref_start:.1f}s")
    
    reference_audio = os.path.join(OUTPUT_DIR, "reference.wav")
    
    if not extract_reference_audio(ORIGINAL_AUDIO, ref_start, ref_duration, reference_audio):
        print("❌ 提取参考音频失败")
        return
    
    print(f"  ✅ 参考音频: {reference_audio}")
    
    # 步骤2: 批量生成
    print("\n" + "="*80)
    print("🎤 步骤 2/3: 生成所有英文句子")
    print("="*80)
    print(f"\n💡 使用克隆音色生成，时长与原视频一致\n")
    
    audio_segments = []  # [(start_time, audio_file), ...]
    stats = {"success": 0, "failed": 0}
    
    for i, sent in enumerate(sentences, 1):
        text_en = sent.get("text_en", "")
        text_zh = sent.get("text_zh", "")
        start_time = sent.get("start", 0)
        target_duration = sent.get("duration", 0)
        
        if not text_en or "[FAILED:" in text_en:
            print(f"[{i:02d}/{len(sentences)}] ⏭️  跳过")
            continue
        
        display = text_en if len(text_en) <= 45 else text_en[:42] + "..."
        print(f"[{i:02d}/{len(sentences)}] {display}")
        print(f"  ⏱️  {start_time:.1f}s, 目标时长: {target_duration:.1f}s")
        
        # 生成音频
        raw_output = os.path.join(OUTPUT_DIR, f"raw_{i:03d}.wav")
        
        if generate_with_voice_cloning(text_en, reference_audio, ref_text, raw_output, max_retries=3):
            raw_duration = get_audio_duration(raw_output)
            print(f"  🎵 生成: {raw_duration:.1f}s")
            
            final_output = os.path.join(OUTPUT_DIR, f"s_{i:03d}.wav")
            
            if check_and_process_audio(raw_output, final_output, ref_duration, target_duration):
                final_duration = get_audio_duration(final_output)
                ratio = final_duration / target_duration if target_duration > 0 else 1.0
                
                # 再次检查：如果还是太长，标记为失败
                if final_duration > target_duration * 5:
                    print(f"  ❌ 异常：{final_duration:.1f}s，跳过此句")
                    stats["failed"] += 1
                    if os.path.exists(raw_output):
                        os.remove(raw_output)
                    if os.path.exists(final_output):
                        os.remove(final_output)
                    continue
                
                if 0.7 <= ratio <= 1.3:
                    status = "✅"
                elif ratio > 1.3:
                    status = "⚠️ 偏长"
                else:
                    status = "⚠️ 偏短"
                
                print(f"  {status} 最终: {final_duration:.1f}s (比例: {ratio:.2f}x)")
                
                # 添加到时间轴
                audio_segments.append((start_time, final_output))
                stats["success"] += 1
                
                # 清理
                if os.path.exists(raw_output) and raw_output != final_output:
                    os.remove(raw_output)
            else:
                print(f"  ❌ 处理失败")
                stats["failed"] += 1
        else:
            stats["failed"] += 1
        
        # API限流
        if i < len(sentences):
            time.sleep(0.5)
    
    print("\n" + "-"*80)
    print(f"📊 生成统计:")
    print(f"   成功: {stats['success']}/{len(sentences)}")
    print(f"   失败: {stats['failed']}")
    print("-"*80)
    
    if not audio_segments:
        print("\n❌ 没有成功生成任何音频")
        return
    
    # 步骤3: 按时间轴组装
    print("\n" + "="*80)
    print("🎬 步骤 3/3: 按时间轴组装音频")
    print("="*80)
    
    speech_only = os.path.join(OUTPUT_DIR, "speech_only.wav")
    
    if assemble_audio_timeline(audio_segments, total_duration, speech_only):
        print(f"\n✅ 语音轨道完成")
        
        # 背景音乐
        print("\n" + "="*80)
        add_bgm = input("\n添加背景音乐? (y/n) [y]: ").strip().lower() or "y"
        
        if add_bgm == "y":
            bgm = os.path.join(OUTPUT_DIR, "bgm.wav")
            
            print("\n🎵 提取背景音乐...")
            if extract_background_music(ORIGINAL_AUDIO, bgm):
                print("  ✅ 提取完成")
                
                volume = input("背景音乐音量 (0.0-1.0) [默认: 0.15]: ").strip()
                volume = float(volume) if volume else 0.15
                
                print(f"🎵 混合音频 (音量: {volume})...")
                if add_background_music(speech_only, bgm, FINAL_OUTPUT, volume):
                    print("  ✅ 完成")
                else:
                    print("  ⚠️  混合失败，使用纯语音")
                    import shutil
                    shutil.copy(speech_only, FINAL_OUTPUT)
            else:
                print("  ⚠️  提取失败，使用纯语音")
                import shutil
                shutil.copy(speech_only, FINAL_OUTPUT)
        else:
            import shutil
            shutil.copy(speech_only, FINAL_OUTPUT)
        
        # 完成
        print("\n" + "="*80)
        print("✅ 音频生成完成！")
        print("="*80)
        
        if os.path.exists(FINAL_OUTPUT):
            size = os.path.getsize(FINAL_OUTPUT) / (1024*1024)
            duration = get_audio_duration(FINAL_OUTPUT)
            
            print(f"\n📁 {FINAL_OUTPUT}")
            print(f"📦 {size:.2f} MB")
            print(f"⏱️  {duration:.1f}秒")
            
            # 时长对比
            original_duration = get_audio_duration(ORIGINAL_AUDIO)
            if original_duration > 0:
                ratio = duration / original_duration
                print(f"📊 时长匹配: {ratio:.1%} (原视频: {original_duration:.1f}s)")
            
            print(f"\n💡 下一步: python step4_merge_video.py")
        
        print("="*80)
    else:
        print("\n❌ 组装失败")

if __name__ == "__main__":
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("❌ 需要 ffmpeg")
        exit(1)
    
    main()