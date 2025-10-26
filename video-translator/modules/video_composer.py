"""
Video Composition Module (Enhanced Version)
Features:
1. Merge video and new audio
2. Automatic duration alignment
3. Optional original audio mix
4. Generate SRT subtitles
5. Burn-in subtitles (multiple styles)
   - Default style
   - Yellow bottom style
   - Blurred bar style (recommended)
6. Adaptive subtitle sizing
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import timedelta


class VideoComposer:
    """Video Composer - Enhanced Version"""
    
    # Subtitle style presets (support adaptive scaling)
    SUBTITLE_STYLES = {
        "default": {
            "name": "Default Style",
            "description": "Simple white subtitles with black outline, auto-scaled size",
            "base_font_size": 24,  # Base font size (for 1080p)
            "force_style_template": (
                "FontName=Arial,"
                "PrimaryColour=&HFFFFFF&,"
                "OutlineColour=&H000000&,"
                "Outline=2,"
                "Shadow=1,"
                "MarginV=30"
            )
        },
        "yellow_bottom": {
            "name": "Yellow Bottom",
            "description": "Yellow subtitles, bottom centered, black outline, adaptive size",
            "base_font_size": 20,  # Base font size (for 1080p)
            "force_style_template": (
                "FontName=Arial,"
                "PrimaryColour=&H00FFFF&,"
                "OutlineColour=&H000000&,"
                "Outline=2,"
                "Shadow=1,"
                "MarginV=30"
            )
        },
        "blurred_bar": {
            "name": "Blurred Bar (Recommended)",
            "description": "Soft blurred background bar + white subtitles with black edges, adaptive size",
            "base_font_size": 26,  # Base font size (for 1080p)
            "force_style_template": (
                "FontName=Arial,"
                "PrimaryColour=&HFFFFFF&,"
                "BackColour=&H00000000&,"
                "OutlineColour=&H00000000&,"
                "BorderStyle=1,"
                "Outline=2,"
                "Shadow=0,"
                "Alignment=2"
            ),
            "requires_filter": True  # Requires special video filter
        }
    }
    
    def __init__(self):
        """Initialize the video composer"""
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if ffmpeg is available"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True,
                check=True
            )
        except:
            raise RuntimeError("❌ ffmpeg is not installed or not available")
    
    def _calculate_font_size(self, video_width, video_height, base_font_size=24):
        """
        Calculate adaptive font size based on video resolution
        
        Args:
            video_width: Video width
            video_height: Video height
            base_font_size: Base font size (for 1080p)
        
        Returns:
            int: Calculated font size
        """
        base_width = 1920
        base_height = 1080
        
        base_diagonal = (base_width ** 2 + base_height ** 2) ** 0.5
        current_diagonal = (video_width ** 2 + video_height ** 2) ** 0.5
        
        scale_factor = current_diagonal / base_diagonal
        
        font_size = max(16, min(48, int(base_font_size * scale_factor)))
        
        print(f"📏 Resolution: {video_width}x{video_height}, Computed Font Size: {font_size}px")
        return font_size
    
    def _get_adaptive_style(self, video_path, style_name):
        """
        Get adaptive subtitle style
        
        Args:
            video_path: Path to video file
            style_name: Style name
        
        Returns:
            dict: Style configuration with adaptive font size
        """
        style_config = self.SUBTITLE_STYLES.get(style_name, self.SUBTITLE_STYLES["default"])
        
        video_info = self.get_video_info(video_path)
        video_width = video_info.get("width", 1920)
        video_height = video_info.get("height", 1080)
        
        base_font_size = style_config.get("base_font_size", 24)
        adaptive_font_size = self._calculate_font_size(video_width, video_height, base_font_size)
        
        template = style_config.get("force_style_template", "")
        force_style = template.replace("FontSize={}", f"FontSize={adaptive_font_size}")
        
        return {
            "name": style_config["name"],
            "description": style_config["description"],
            "force_style": force_style,
            "font_size": adaptive_font_size,
            "requires_filter": style_config.get("requires_filter", False)
        }
    
    def compose(self, video_path, audio_path, output_path, 
                subtitle_path=None, subtitle_style="default", keep_original_audio=False):
        """
        Compose the final video
        
        Args:
            video_path: Original video path
            audio_path: New audio path
            output_path: Output video path
            subtitle_path: Subtitle file path (optional)
            subtitle_style: Subtitle style ("default", "yellow_bottom", "blurred_bar")
            keep_original_audio: Whether to keep and mix original audio
        
        Returns:
            bool: Success status
        """
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return False
        
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return False
        
        try:
            print("=" * 80)
            print("🎬 Step 5: Video Composition")
            print("=" * 80)
            
            video_info = self.get_video_info(video_path)
            print(f"📊 Video Info: {video_info['width']}x{video_info['height']}, {video_info['fps']:.2f}fps, {video_info['duration']:.1f}s")
            
            aligned_audio = self._align_audio_to_video(video_path, audio_path, output_path)
            if not aligned_audio:
                print("⚠️  Audio alignment failed, using original audio")
                aligned_audio = audio_path
            
            if subtitle_path and os.path.exists(subtitle_path):
                adaptive_style = self._get_adaptive_style(video_path, subtitle_style)
                print(f"📝 Subtitle Style: {adaptive_style['name']} (Font Size: {adaptive_style['font_size']}px)")
                
                return self._compose_with_subtitles(
                    video_path, aligned_audio, output_path,
                    subtitle_path, adaptive_style, keep_original_audio
                )
            else:
                print("📝 No subtitle mode")
                return self._compose_without_subtitles(
                    video_path, aligned_audio, output_path, keep_original_audio
                )
        
        except Exception as e:
            print(f"❌ Video composition failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _align_audio_to_video(self, video_path, audio_path, output_path):
        """
        Automatically align audio and video durations
        Returns: Path to aligned audio
        """
        try:
            video_dur = self._get_duration(video_path)
            audio_dur = self._get_duration(audio_path)
            
            print(f"📊 Video Duration: {video_dur:.1f}s")
            print(f"📊 Audio Duration: {audio_dur:.1f}s")
            
            if abs(video_dur - audio_dur) <= 0.5:
                print("✅ Durations already aligned, no adjustment needed")
                return audio_path
            
            aligned_audio = str(Path(output_path).parent / "aligned_audio.wav")
            shorter = min(video_dur, audio_dur)
            
            print(f"⚙️  Aligning audio length → {shorter:.1f}s")
            
            subprocess.run([
                "ffmpeg", "-y",
                "-i", audio_path,
                "-t", str(shorter),
                "-c", "copy",
                aligned_audio
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            print("✅ Audio alignment complete")
            return aligned_audio
        
        except:
            return None
    
    def _get_duration(self, file_path):
        """Get media file duration"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def _compose_without_subtitles(self, video_path, audio_path, output_path, keep_original_audio):
        """Compose video (no subtitles)"""
        print("\n🔄 Merging video and audio...")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            cmd.extend([
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest[aout]",
                "-map", "0:v:0",
                "-map", "[aout]"
            ])
        else:
            cmd.extend([
                "-map", "0:v:0",
                "-map", "1:a:0"
            ])
        
        cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ Video saved: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ Composition failed")
            if result.stderr:
                print(f"   Error info: {result.stderr[-300:]}")
            return False
    
    def _compose_with_subtitles(self, video_path, audio_path, output_path, 
                                 subtitle_path, style_config, keep_original_audio):
        """Compose video (with subtitles)"""
        
        if style_config.get("requires_filter", False):
            return self._compose_with_blurred_subtitles(
                video_path, audio_path, output_path, 
                subtitle_path, style_config, keep_original_audio
            )
        else:
            return self._compose_with_simple_subtitles(
                video_path, audio_path, output_path, 
                subtitle_path, style_config, keep_original_audio
            )
    
    def _compose_with_simple_subtitles(self, video_path, audio_path, output_path, 
                                        subtitle_path, style_config, keep_original_audio):
        """Compose video (simple subtitle style)"""
        print("\n🔄 Merging video, audio, and subtitles...")
        
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        
        force_style = style_config.get("force_style", "")
        subtitles_filter = f"subtitles={subtitle_path_escaped}:force_style='{force_style}'"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            cmd.extend([
                "-filter_complex", 
                f"[0:a][1:a]amix=inputs=2:duration=shortest[aout];[0:v]{subtitles_filter}[vout]",
                "-map", "[vout]",
                "-map", "[aout]"
            ])
        else:
            cmd.extend([
                "-vf", subtitles_filter,
                "-map", "0:v",
                "-map", "1:a"
            ])
        
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ Video saved: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ Composition failed")
            if result.stderr:
                print(f"   Error info: {result.stderr[-300:]}")
            return False
    
    def _compose_with_blurred_subtitles(self, video_path, audio_path, output_path, 
                                         subtitle_path, style_config, keep_original_audio):
        """
        Compose video (blurred bar subtitle style)
        Creates a soft blurred bar background, then overlays clear white text
        """
        print("\n🔄 Merging video, audio, and blurred-bar subtitles...")
        print("   Tip: This style looks best but takes slightly longer to render")
        
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        force_style = style_config.get("force_style", "")
        
        vf_filter = (
            "[0:v]split[v][vblur];"
            "[vblur]crop=iw:ih*0.25:0:ih*0.75,boxblur=20:1,format=rgba,colorchannelmixer=aa=0.7[blurred];"
            "[v][blurred]overlay=0:H-h*0.25,"
            f"subtitles='{subtitle_path_escaped}':force_style='{force_style}'"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            cmd.extend([
                "-filter_complex", 
                f"{vf_filter}[vout];[0:a][1:a]amix=inputs=2:duration=shortest[aout]",
                "-map", "[vout]",
                "-map", "[aout]"
            ])
        else:
            cmd.extend([
                "-filter_complex", f"{vf_filter}",
                "-map", "1:a"
            ])
        
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])
        
        print("   Rendering with blur effect...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ Video saved: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ Composition failed")
            if result.stderr:
                print(f"   Error info: {result.stderr[-300:]}")
            return False
    
    def create_subtitles(self, translated_json_path, output_srt_path):
        """
        Generate SRT subtitle file from translated JSON
        
        Args:
            translated_json_path: Path to translated JSON
            output_srt_path: Output SRT file path
        
        Returns:
            bool: Success status
        """
        try:
            print("📝 Generating SRT subtitles...")
            
            with open(translated_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sentences = data[0].get("sentence_info", [])
            Path(output_srt_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                subtitle_index = 1
                
                for sent in sentences:
                    text = sent.get("text_en", sent.get("text_translated", ""))
                    start = sent.get("start", 0)
                    end = sent.get("end", 0)
                    
                    if "[FAILED:" in text or not text or not text.strip():
                        continue
                    
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{self._sec_to_timestamp(start)} --> {self._sec_to_timestamp(end)}\n")
                    f.write(f"{text.strip()}\n\n")
                    
                    subtitle_index += 1
            
            print(f"✅ Subtitle file saved: {output_srt_path} ({subtitle_index-1} entries)")
            return True
        
        except Exception as e:
            print(f"❌ Subtitle generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _sec_to_timestamp(self, seconds):
        """
        Convert float seconds to SRT timestamp format
        Format: 00:00:00,000
        """
        td = timedelta(seconds=seconds)
        timestamp = str(td)
        
        if '.' in timestamp:
            timestamp = timestamp.replace('.', ',')
            parts = timestamp.split(',')
            if len(parts) == 2:
                ms = parts[1][:3].ljust(3, '0')
                timestamp = f"{parts[0]},{ms}"
        else:
            timestamp = f"{timestamp},000"
        
        if timestamp.count(':') == 2:
            return timestamp.rjust(12, "0")
        else:
            return f"00:{timestamp}".rjust(12, "0")
    
    def get_video_info(self, video_path):
        """
        Get video info
        Returns: dict with duration, width, height, fps
        """
        try:
            duration = self._get_duration(video_path)
            
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json as json_lib
                data = json_lib.loads(result.stdout)
                stream = data.get("streams", [{}])[0]
                
                width = stream.get("width", 0)
                height = stream.get("height", 0)
                fps_str = stream.get("r_frame_rate", "0/1")
                
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den) if float(den) != 0 else 0
                else:
                    fps = float(fps_str)
                
                return {
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "fps": fps
                }
        except:
            pass
        
        return {
            "duration": 0,
            "width": 1920,
            "height": 1080,
            "fps": 0
        }