"""
TTS Audio Generation Module (Enhanced Version)
Features:
1. Voice cloning (using the tone from the original video)
2. Preset voices (female, male, etc.)
3. Vocal and background separation
4. Precise duration alignment
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
    """Text-to-Speech Generator – Enhanced Version (Multilingual Support)"""
    
    # Language configuration mapping
    LANGUAGE_CONFIGS = {
        "zh": {"name": "Chinese", "instruction": "Speak in natural Mandarin Chinese"},
        "ja": {"name": "Japanese", "instruction": "Speak in natural Japanese"},
        "ko": {"name": "Korean", "instruction": "Speak in natural Korean"},
        "fr": {"name": "French", "instruction": "Speak in natural French"},
        "de": {"name": "German", "instruction": "Speak in natural German"},
        "es": {"name": "Spanish", "instruction": "Speak in natural Spanish"},
        "ru": {"name": "Russian", "instruction": "Speak in natural Russian"},
        "ar": {"name": "Arabic", "instruction": "Speak in natural Arabic"},
        "pt": {"name": "Portuguese", "instruction": "Speak in natural Portuguese"},
        "en": {"name": "English", "instruction": "Speak in natural English"}
    }
    
    # Preset voice configurations
    PRESET_VOICES = {
        "female_american": {
            "name": "American Female (Clear & Warm)",
            "gender": "female",
            "style": "clear, warm",
            "accent": "American",
            "temperature": 0.4
        },
        "female_british": {
            "name": "British Female (Elegant)",
            "gender": "female",
            "style": "clear, elegant",
            "accent": "British RP",
            "temperature": 0.4
        },
        "male_american": {
            "name": "American Male (Deep & Steady)",
            "gender": "male",
            "style": "deep, steady",
            "accent": "American",
            "temperature": 0.4
        },
        "male_british": {
            "name": "British Male (Smooth & Magnetic)",
            "gender": "male",
            "style": "deep, smooth",
            "accent": "British",
            "temperature": 0.4
        }
    }
    
    def __init__(self, api_key=None, api_base=None):
        """
        Initialize the TTS Generator
        
        Args:
            api_key: API key
            api_base: API base URL
        """
        self.api_key = api_key or os.getenv("BOSON_API_KEY", "bai-4RckqUuoLpgxtUFcgT4fMwHQddd-dR0_AZOxII6UOZhPmR1s")
        self.api_base = api_base or "https://hackathon.boson.ai/v1"
        self.model = "higgs-audio-generation-Hackathon"
        
        self.SAMPLE_RATE = 24000
        self.CHANNELS = 1
        self.SAMPLE_WIDTH = 2
        
        self.client = None
    
    def _init_client(self):
        """Initialize Boson AI TTS client"""
        if self.client is not None:
            return
        
        print("🔄 Initializing Boson AI TTS client...")
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        print("✅ Client initialized successfully")
    
    def _get_system_prompt(self, target_lang, voice_type):
        """
        Generate system prompt based on target language and voice type
        """
        lang_config = self.LANGUAGE_CONFIGS.get(target_lang, self.LANGUAGE_CONFIGS["en"])
        voice_config = self.PRESET_VOICES.get(voice_type, self.PRESET_VOICES["female_american"])
        
        if target_lang == "en":
            system_prompt = (
                f"You are an English text-to-speech (TTS) model. "
                f"Use a {voice_config['style']} {voice_config['gender']} {voice_config['accent']} voice. "
                f"{lang_config['instruction']} naturally, fluently, and consistently across all generations. "
                f"Do not include background noise, effects, or non-speech sounds."
            )
        else:
            system_prompt = (
                f"You are a multilingual text-to-speech (TTS) model. "
                f"The user will provide text in {lang_config['name']} ({target_lang}). "
                f"You MUST speak in {lang_config['name']} language. "
                f"Use a {voice_config['style']} {voice_config['gender']} voice. "
                f"{lang_config['instruction']}. "
                f"Speak naturally, fluently, and consistently across all generations. "
                f"Do not include background noise, effects, or non-speech sounds. "
                f"IMPORTANT: The output MUST be in {lang_config['name']}, NOT English."
            )
        return system_prompt
    
    def generate(self, translated_json_path, output_audio_path, target_lang="en", 
                 bitrate="192k", original_audio_path=None, 
                 voice_mode="clone", preset_voice="female_american",
                 separate_vocals=False, keep_background=True, bgm_volume=0.18):
        """
        Generate full audio from the translated JSON file
        """
        if not os.path.exists(translated_json_path):
            print(f"❌ Input file not found: {translated_json_path}")
            return False
        
        try:
            self._init_client()
            
            with open(translated_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sentences = data[0].get("sentence_info", [])
            total = len(sentences)
            
            print("=" * 80)
            print(f"🔊 Starting generation of {total} audio segments...")
            print(f"🎤 Voice mode: {voice_mode}")
            if voice_mode == "preset":
                print(f"🎵 Preset voice: {self.PRESET_VOICES[preset_voice]['name']}")
            print("=" * 80)
            
            temp_dir = Path(output_audio_path).parent / "temp_audio"
            temp_dir.mkdir(exist_ok=True)
            
            reference_audio = None
            reference_text = None
            bgm_path = None
            
            # Step 1: Handle source audio (voice extraction)
            if original_audio_path and os.path.exists(original_audio_path):
                if voice_mode == "clone":
                    print("\n🎯 Step 1: Extracting reference voice (Clone Mode)")
                    print("-" * 80)
                    
                    if separate_vocals:
                        print("🎧 Separating vocals and background...")
                        vocals_path, bgm_path = self._separate_audio(original_audio_path, str(temp_dir))
                        if vocals_path:
                            print(f"✅ Vocal track: {vocals_path}")
                            source_for_reference = vocals_path
                        else:
                            print("⚠️  Vocal separation failed, using original audio")
                            source_for_reference = original_audio_path
                    else:
                        source_for_reference = original_audio_path
                    
                    ref_result = self._find_best_reference(sentences)
                    if ref_result:
                        ref_idx, ref_sent, ref_duration = ref_result
                        ref_text = ref_sent.get("text", "")
                        ref_start = ref_sent.get("start", 0)
                        
                        reference_audio = str(temp_dir / "reference.wav")
                        
                        if self._extract_reference_audio(source_for_reference, ref_start, ref_duration, reference_audio):
                            reference_text = ref_text
                            print(f"✅ Using reference sentence {ref_idx+1}: {ref_text[:30]}...")
                        else:
                            reference_audio = None
                
                elif separate_vocals and keep_background:
                    print("\n🎧 Step 1: Extracting background music")
                    print("-" * 80)
                    _, bgm_path = self._separate_audio(original_audio_path, str(temp_dir))
                    if bgm_path:
                        print(f"✅ Background music: {bgm_path}")
            
            # Step 2: Generate audio for each sentence
            print("\n🎤 Step 2: Generating sentence audio")
            print("-" * 80)
            
            audio_segments = []
            success_count = 0
            
            for i, sentence in enumerate(sentences, 1):
                text = sentence.get("text_en", "") if target_lang == "en" else sentence.get("text_translated", "")
                start_time = sentence.get("start", 0)
                end_time = sentence.get("end", 0)
                target_duration = end_time - start_time
                
                if not text or "[FAILED:" in text:
                    print(f"  [{i}/{total}] ⏭️  Skipped")
                    continue
                
                display = text if len(text) <= 45 else text[:42] + "..."
                print(f"  [{i}/{total}] {display}")
                
                raw_output = str(temp_dir / f"raw_{i:03d}.wav")
                final_output = str(temp_dir / f"segment_{i:03d}.wav")
                
                if voice_mode == "clone" and reference_audio and reference_text:
                    if self._generate_with_voice_cloning(text, reference_audio, reference_text, raw_output, target_lang, target_duration):
                        raw_duration = self._get_audio_duration(raw_output)
                        print(f"    🎵 Generated: {raw_duration:.1f}s")
                        if self._align_audio_duration(raw_output, target_duration, final_output):
                            audio_segments.append((start_time, final_output))
                            success_count += 1
                    else:
                        print("    ❌ Generation failed")
                
                elif voice_mode == "preset":
                    if self._generate_with_preset_voice(text, preset_voice, raw_output, target_lang, target_duration):
                        raw_duration = self._get_audio_duration(raw_output)
                        print(f"    🎵 Generated: {raw_duration:.1f}s")
                        if self._align_audio_duration(raw_output, target_duration, final_output):
                            audio_segments.append((start_time, final_output))
                            success_count += 1
                    else:
                        print("    ❌ Generation failed")
                
                else:
                    if self._create_silence(target_duration, final_output):
                        audio_segments.append((start_time, final_output))
                
                if i < total:
                    time.sleep(0.3)
            
            print(f"\n✅ Audio generation completed: {success_count}/{total}")
            
            total_duration = sentences[-1].get("end", 0) if sentences else 60
            
            # Step 3: Assemble timeline
            print("\n🔄 Step 3: Assembling audio timeline")
            print("-" * 80)
            speech_only = str(temp_dir / "speech_only.wav")
            
            if self._assemble_audio_timeline(audio_segments, total_duration, speech_only):
                print(f"✅ Speech track complete: {speech_only}")
                
                if keep_background and bgm_path and os.path.exists(bgm_path):
                    print("\n🎵 Step 4: Mixing background audio")
                    print("-" * 80)
                    temp_output = str(temp_dir / "with_bgm.wav")
                    if self._mix_audio_with_bgm(speech_only, bgm_path, temp_output, bgm_volume):
                        speech_only = temp_output
                        print("✅ Background mixing complete")
                
                print("\n🔄 Step 5: Converting to MP3")
                print("-" * 80)
                self._convert_to_mp3(speech_only, output_audio_path, bitrate)
                
                print(f"💾 Audio saved: {output_audio_path}")
                print("=" * 80)
                
                shutil.rmtree(temp_dir)
                return True
            else:
                print("❌ Audio assembly failed")
                return False
        
        except Exception as e:
            print(f"❌ Audio generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    

    # (All helper methods below have been translated too)
    def _separate_audio(self, input_audio, output_dir):
        """Separate vocals and background using Demucs"""
        try:
            subprocess.run(["demucs", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except:
            print("⚠️  Demucs not installed, skipping separation")
            print("   Tip: pip install demucs")
            return None, None
        
        try:
            audio_name = Path(input_audio).stem
            subprocess.run(["demucs", "-n", "htdemucs", "--two-stems=vocals", input_audio],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            separated_root = Path("separated") / "htdemucs" / audio_name
            vocals = separated_root / "vocals.wav"
            bgm = separated_root / "no_vocals.wav"
            
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
            print(f"⚠️  Vocal separation failed: {e}")
            return None, None

    def _generate_with_preset_voice(self, text, voice_type, output_path, target_lang="en", target_duration=None, max_retries=10):
        """Generate audio using preset voice (supports multiple languages)"""
        if not text.strip():
            return False
        
        voice_config = self.PRESET_VOICES.get(voice_type, self.PRESET_VOICES["female_american"])
        # Get system prompt matching the target language
        system_prompt = self._get_system_prompt(target_lang, voice_type)
        
        for attempt in range(max_retries):
            try:
                # Record start time
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt  # Dynamically generated prompt
                        },
                        {"role": "user", "content": text.strip()}
                    ],
                    modalities=["text", "audio"],
                    max_completion_tokens=2048,
                    temperature=voice_config["temperature"],
                    top_p=0.9,
                    stream=False,
                    timeout=30  # Add 30-second timeout
                )
                
                # Calculate generation time
                generation_time = time.time() - start_time
                
                audio_b64 = getattr(response.choices[0].message.audio, "data", None)
                if not audio_b64:
                    if attempt < max_retries - 1:
                        print(f"    ⚠️  No audio response, retrying {attempt+1}/{max_retries} ...")
                        time.sleep(3)
                        continue
                    return False
                
                tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                with open(tmp_output, "wb") as f:
                    f.write(base64.b64decode(audio_b64))
                
                duration = self._get_audio_duration(tmp_output)
                if target_duration is not None and target_duration > 0:
                    duration_ratio = duration / target_duration
                    
                    print(f"    📊 Generated {duration:.2f}s / Target {target_duration:.2f}s (Ratio {duration_ratio:.2f}x)")
                    
                    # Check abnormal duration
                    if duration > 30:
                        print(f"    ⚠️  Abnormally long audio ({duration:.1f}s)")
                        if attempt < max_retries - 1:
                            print(f"    🔄 Regenerating ({attempt + 2}/{max_retries})...")
                            time.sleep(1)
                            continue
                        else:
                            return True
                    
                    # Duration ratio check
                    if 0.5 <= duration_ratio <= 2.2:
                        if 0.9 <= duration_ratio <= 1.1:
                            print(f"    ✅ Perfect duration match")
                        else:
                            print(f"    ✅ Reasonable duration, suggested speed adjustment {duration_ratio:.2f}x")
                        return True
                    else:
                        if duration_ratio < 0.5:
                            print(f"    ⚠️  Too short ({duration_ratio:.2f}x < 0.5x)")
                        else:
                            print(f"    ⚠️  Too long ({duration_ratio:.2f}x > 2.0x)")
                        
                        if attempt < max_retries - 1:
                            print(f"    🔄 Regenerating ({attempt + 2}/{max_retries})...")
                            time.sleep(1)
                            continue
                        else:
                            print(f"    ⚠️  Max retries reached — returning result (requires forced speed adjustment)")
                            return True
                else:    
                # Check for abnormal generation
                # 1. Abnormal duration (too long or too short)
                    if duration > 20 or duration < 0.5:
                        os.remove(tmp_output)
                        if attempt < max_retries - 1:
                            print(f"    ⚠️  Abnormal duration {duration:.1f}s, regenerating...")
                            time.sleep(3)
                            continue
                        return False
                    
                    # 2. Excessive generation time (>30 seconds)
                    if generation_time > 30:
                        print(f"    ⚠️  Generation took too long ({generation_time:.1f}s), possible issue")
                        # If audio appears fine, still use it
                        if duration < 1 or duration > 15:
                            os.remove(tmp_output)
                            if attempt < max_retries - 1:
                                print(f"    ⚠️  Regenerating...")
                                time.sleep(3)
                                continue
                            return False
                
                os.rename(tmp_output, output_path)
                return True
            
            except TimeoutError:
                print(f"    ⚠️  Request timed out, retrying {attempt+1}/{max_retries} ...")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return False
            
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"    ⚠️  Timeout error, retrying {attempt+1}/{max_retries} ...")
                elif attempt < max_retries - 1:
                    print(f"    ⚠️  Error: {error_msg[:60]}, retrying...")
                else:
                    print(f"    ❌ Error: {error_msg[:60]}")
                    return False
                
                if attempt < max_retries - 1:
                    time.sleep(3)
        
        return False
    
    def _align_audio_duration(self, input_file, target_duration, output_file):
        """Adjust audio duration for precise alignment"""
        try:
            actual_duration = self._get_audio_duration(input_file)
            
            if actual_duration <= 0:
                return False
            
            ratio = target_duration / actual_duration
            
            # If close enough, use directly
            if 0.9 <= ratio <= 1.1:
                shutil.copy(input_file, output_file)
                return True
            
            # Adjust speed if needed
            if ratio < 2.2:
                speed = 1.0 / ratio
                return self._change_audio_speed(input_file, output_file, speed)
            
            # If too different, pad silence or truncate
            if ratio >= 2.2:
                return self._pad_silence(input_file, output_file, target_duration - actual_duration)
            else:
                # Truncate
                shutil.copy(input_file, output_file)
                return True
        
        except:
            return False
    
    def _change_audio_speed(self, input_file, output_file, speed):
        """Change playback speed of audio"""
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
        """Add silence padding to the end of audio"""
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
        """Mix speech with background music"""
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
        """Find the most suitable sentence as reference"""
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
        """Extract reference audio from original video"""
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
    
    def _generate_with_voice_cloning(self, text, reference_audio, reference_text, output_path, target_lang="en", target_duration=None, max_retries=5):
        """Generate speech using voice cloning (supports multiple languages)"""
        # Get language configuration
        lang_config = self.LANGUAGE_CONFIGS.get(target_lang, self.LANGUAGE_CONFIGS["en"])
        
        for attempt in range(max_retries):
            try:
                # Record start time
                start_time = time.time()
                
                # Read and encode reference audio as base64
                with open(reference_audio, "rb") as f:
                    ref_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                # Dynamically construct system prompt based on target language
                if target_lang == "en":
                    system_prompt = (
                        "You are a voice cloning assistant. "
                        "Clone the voice from the reference audio and speak the new text "
                        "naturally and fluently in English with the same tone, accent, and speaking style."
                    )
                else:
                    system_prompt = (
                        f"You are a multilingual voice cloning assistant. "
                        f"Clone the voice from the reference audio and speak the new text "
                        f"in {lang_config['name']} naturally and fluently "
                        f"while preserving the same tone, rhythm, and style. "
                        f"IMPORTANT: The output audio MUST be in {lang_config['name']}, not English."
                    )
                
                # Call API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": system_prompt  # Dynamically generated prompt
                        },
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
                    timeout=45  # Add 45-second timeout
                )
                
                # Calculate generation time
                generation_time = time.time() - start_time
                
                # Retrieve generated audio
                if hasattr(response.choices[0].message, 'audio') and response.choices[0].message.audio:
                    audio_b64 = response.choices[0].message.audio.data
                    audio_data = base64.b64decode(audio_b64)
                    
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    
                    # Check for abnormal audio duration
                    duration = self._get_audio_duration(output_path)
                    
                    # === Intelligent duration validation logic ===
                    if target_duration is not None and target_duration > 0:
                        duration_ratio = duration / target_duration
                        
                        print(f"    📊 Generated {duration:.2f}s / Target {target_duration:.2f}s (Ratio {duration_ratio:.2f}x)")
                        
                        # Check 1: Absolute abnormal duration (>30s)
                        if duration > 30:
                            print(f"    ⚠️  Abnormally long audio ({duration:.1f}s)")
                            if attempt < max_retries - 1:
                                print(f"    🔄 Regenerating ({attempt + 2}/{max_retries})...")
                                time.sleep(2)
                                continue
                            else:
                                # Final attempt — return but mark as needing speed adjustment
                                return True
                        
                        # Check 2: Duration ratio validation
                        if 0.5 <= duration_ratio <= 2.2:
                            # Acceptable range
                            if 0.9 <= duration_ratio <= 1.1:
                                print(f"    ✅ Perfect duration match")
                            else:
                                print(f"    ✅ Reasonable duration, suggested speed adjustment {duration_ratio:.2f}x")
                            return True
                        else:
                            # Too large deviation
                            if duration_ratio < 0.5:
                                print(f"    ⚠️  Too short ({duration_ratio:.2f}x < 0.5x)")
                            else:
                                print(f"    ⚠️  Too long ({duration_ratio:.2f}x > 2.0x)")
                            
                            if attempt < max_retries - 1:
                                print(f"    🔄 Regenerating ({attempt + 2}/{max_retries})...")
                                time.sleep(2)
                                continue
                            else:
                                # Final attempt — return but requires forced speed adjustment
                                print(f"    ⚠️  Max retries reached — returning result (requires forced speed adjustment)")
                                return True
                    
                    else:
                        # General generation quality checks
                        # 1. Abnormal duration
                        if duration > 30:
                            print(f"    ⚠️  Abnormal duration {duration:.1f}s")
                            if attempt < max_retries - 1:
                                print(f"    ⚠️  Regenerating...")
                                time.sleep(2)
                                continue
                        
                        # 2. Excessive generation time (>45s)
                        if generation_time > 45:
                            print(f"    ⚠️  Generation took too long ({generation_time:.1f}s)")
                            # If audio still seems fine, accept
                            if duration < 1 or duration > 20:
                                if attempt < max_retries - 1:
                                    print(f"    ⚠️  Regenerating...")
                                    time.sleep(2)
                                    continue
                    
                    return True
                
                # No audio response
                if attempt < max_retries - 1:
                    print(f"    ⚠️  No audio response, retrying {attempt+1}/{max_retries} ...")
                    time.sleep(2)
                    continue
                
                return False
            
            except TimeoutError:
                print(f"    ⚠️  Voice cloning timed out, retrying {attempt+1}/{max_retries} ...")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    return False
            
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"    ⚠️  Timeout error, retrying {attempt+1}/{max_retries} ...")
                elif attempt < max_retries - 1:
                    print(f"    ⚠️  Error: {error_msg[:60]}, retrying...")
                else:
                    print(f"    ❌ Cloning failed: {error_msg[:60]}")
                    return False
                
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def _create_silence(self, duration_seconds, output_path):
        """Create silent audio of specified duration"""
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
        """Assemble final audio based on timeline alignment"""
        try:
            # Sort segments by start time
            audio_segments = sorted(audio_segments, key=lambda x: x[0])
            
            # Create full-length empty audio buffer
            total_samples = int(total_duration * self.SAMPLE_RATE)
            audio_data = bytearray(b'\x00\x00' * total_samples)
            
            # Insert each audio segment at proper position
            for i, (start_time, audio_file) in enumerate(audio_segments, 1):
                if not os.path.exists(audio_file):
                    continue
                
                try:
                    with wave.open(audio_file, 'rb') as wav:
                        if wav.getnchannels() != self.CHANNELS or wav.getframerate() != self.SAMPLE_RATE:
                            continue
                        
                        frames = wav.readframes(wav.getnframes())
                    
                    # Calculate insertion point
                    start_sample = int(start_time * self.SAMPLE_RATE)
                    start_byte = start_sample * self.SAMPLE_WIDTH
                    end_byte = start_byte + len(frames)
                    
                    if end_byte > len(audio_data):
                        frames = frames[:len(audio_data) - start_byte]
                        end_byte = len(audio_data)
                    
                    audio_data[start_byte:end_byte] = frames
                    
                except:
                    continue
            
            # Write final assembled file
            with wave.open(output_path, 'wb') as wav:
                wav.setnchannels(self.CHANNELS)
                wav.setsampwidth(self.SAMPLE_WIDTH)
                wav.setframerate(self.SAMPLE_RATE)
                wav.writeframes(bytes(audio_data))
            
            return True
        
        except:
            return False
    
    def _get_audio_duration(self, audio_path):
        """Get duration of an audio file"""
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
        """Convert WAV file to MP3"""
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