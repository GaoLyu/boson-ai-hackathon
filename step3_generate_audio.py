import json
import os
import subprocess
from openai import OpenAI
from pathlib import Path
import wave
import time

# ===== 配置 =====
API_BASE = "https://hackathon.boson.ai/v1"
API_KEY = os.getenv("BOSON_API_KEY", "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH")

INPUT_JSON = "translated_with_timestamps.json"
OUTPUT_DIR = "generated_audio"
FINAL_OUTPUT = "final_english_audio.wav"

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def save_pcm_as_wav(pcm_data, output_path):
    """将PCM保存为WAV"""
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm_data)

def generate_audio_simple(text, voice, output_path):
    """
    使用简单API生成音频
    这是正确的方法！
    """
    try:
        response = client.audio.speech.create(
            model="higgs-audio-generation-Hackathon",
            voice=voice,
            input=text,
            response_format="pcm"
        )
        save_pcm_as_wav(response.content, output_path)
        return True
    except Exception as e:
        print(f"  ❌ {str(e)[:80]}")
        return False

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

def adjust_audio_speed(input_file, output_file, target_duration):
    """
    调整音频速度以匹配目标时长
    """
    try:
        current_duration = get_audio_duration(input_file)
        if current_duration == 0:
            return False
        
        # 计算速度调整比例
        speed_ratio = current_duration / target_duration
        
        # 限制调整范围（0.8-1.5倍速）
        if speed_ratio < 0.5:
            speed_ratio = 0.5
        elif speed_ratio > 2.0:
            speed_ratio = 2.0
        
        # 使用atempo调整速度
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-filter:a", f"atempo={speed_ratio}",
            output_file
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def concatenate_audio_files(audio_files, output_path):
    """拼接音频文件"""
    if not audio_files:
        return False
    
    print(f"  拼接 {len(audio_files)} 个文件...")
    
    try:
        # 使用filter_complex
        inputs = []
        filters = []
        
        for i, audio_path in enumerate(audio_files):
            inputs.extend(["-i", audio_path])
            filters.append(f"[{i}:a]")
        
        filter_str = f"{''.join(filters)}concat=n={len(audio_files)}:v=0:a=1[out]"
        
        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return True
        
    except:
        # 备用：手动拼接
        try:
            with wave.open(output_path, 'wb') as out:
                out.setnchannels(CHANNELS)
                out.setsampwidth(SAMPLE_WIDTH)
                out.setframerate(SAMPLE_RATE)
                
                for audio_file in audio_files:
                    with wave.open(audio_file, 'rb') as inp:
                        out.writeframes(inp.readframes(inp.getnframes()))
            return True
        except Exception as e:
            print(f"  ❌ 拼接失败: {e}")
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

def main():
    print("="*80)
    print("🎤 Step 3: 音频生成（简化版 - 只用预设音色）")
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
    print(f"\n✅ 加载 {len(sentences)} 个句子\n")
    
    # 可用音色
    voices = {
        "1": ("en_woman", "女声（清晰）"),
        "2": ("en_man", "男声（沉稳）"),
        "3": ("belinda", "Belinda（年轻女性）"),
        "4": ("chadwick", "Chadwick（成熟男性）"),
        "5": ("mabel", "Mabel（活泼女性）"),
        "6": ("vex", "Vex（中性）")
    }
    
    print("可用音色:")
    for k, (name, desc) in voices.items():
        print(f"  {k}. {desc}")
    
    choice = input("\n选择音色 (1-6) [默认: 1]: ").strip() or "1"
    voice = voices.get(choice, ("en_woman", ""))[0]
    
    print(f"\n🎤 使用音色: {voice}")
    print(f"🔄 开始生成...\n")
    
    generated_files = []
    stats = {"success": 0, "failed": 0, "adjusted": 0}
    
    for i, sent in enumerate(sentences, 1):
        text_en = sent.get("text_en", "")
        target_duration = sent.get("duration", 0)
        
        if not text_en or "[FAILED:" in text_en:
            print(f"[{i:02d}/{len(sentences)}] ⏭️  跳过失败句子")
            continue
        
        # 显示进度
        display_text = text_en if len(text_en) <= 50 else text_en[:47] + "..."
        print(f"[{i:02d}/{len(sentences)}] {display_text}")
        
        output_file = os.path.join(OUTPUT_DIR, f"s_{i:03d}.wav")
        
        # 生成音频
        if generate_audio_simple(text_en, voice, output_file):
            actual_duration = get_audio_duration(output_file)
            
            # 检查时长
            if actual_duration > 0:
                ratio = actual_duration / target_duration if target_duration > 0 else 1.0
                
                # 如果时长差距太大，调整速度
                if ratio > 1.5 or ratio < 0.7:
                    print(f"  ⚠️  {actual_duration:.1f}s (预期 {target_duration:.1f}s) - 调整中...")
                    
                    adjusted_file = output_file.replace(".wav", "_adj.wav")
                    if adjust_audio_speed(output_file, adjusted_file, target_duration):
                        os.replace(adjusted_file, output_file)
                        actual_duration = get_audio_duration(output_file)
                        print(f"  ✅ 已调整到 {actual_duration:.1f}s")
                        stats["adjusted"] += 1
                    else:
                        print(f"  ⚠️  调整失败，保持原样")
                
                generated_files.append(output_file)
                stats["success"] += 1
                print(f"  ✅ {actual_duration:.1f}s")
            else:
                print(f"  ❌ 音频无效")
                stats["failed"] += 1
        else:
            stats["failed"] += 1
        
        # 防止API限流
        if i < len(sentences):
            time.sleep(0.4)
    
    # 统计
    print("\n" + "-"*80)
    print(f"📊 生成完成: {stats['success']}/{len(sentences)} 成功")
    if stats["adjusted"] > 0:
        print(f"   调速: {stats['adjusted']} 个")
    if stats["failed"] > 0:
        print(f"   失败: {stats['failed']} 个")
    print("-"*80)
    
    if not generated_files:
        print("\n❌ 没有成功生成任何音频")
        return
    
    # 拼接
    print("\n🔗 拼接音频...")
    speech_only = os.path.join(OUTPUT_DIR, "speech_only.wav")
    
    if concatenate_audio_files(generated_files, speech_only):
        print(f"  ✅ 拼接成功")
        
        # 背景音乐（可选）
        add_bgm = input("\n添加背景音乐? (y/n) [n]: ").strip().lower()
        
        if add_bgm == "y":
            music_file = input("背景音乐文件路径: ").strip()
            
            if os.path.exists(music_file):
                print("🎵 混合背景音乐...")
                if add_background_music(speech_only, music_file, FINAL_OUTPUT, volume=0.15):
                    print("  ✅ 完成")
                else:
                    print("  ⚠️  失败，使用纯语音版本")
                    import shutil
                    shutil.copy(speech_only, FINAL_OUTPUT)
            else:
                print("  ⚠️  文件不存在，跳过")
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
            size_mb = os.path.getsize(FINAL_OUTPUT) / (1024*1024)
            duration = get_audio_duration(FINAL_OUTPUT)
            
            print(f"\n📁 输出文件: {FINAL_OUTPUT}")
            print(f"📦 文件大小: {size_mb:.2f} MB")
            print(f"⏱️  音频时长: {duration:.1f} 秒")
            print(f"\n💡 下一步: python step4_merge_video.py")
        
        print("="*80)
    else:
        print("\n❌ 拼接失败")

if __name__ == "__main__":
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("❌ 需要安装 ffmpeg")
        exit(1)
    
    main()