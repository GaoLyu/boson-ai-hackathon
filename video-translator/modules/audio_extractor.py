"""
Audio Extraction Module
Extracts audio from video files
"""

import os
import subprocess
from pathlib import Path


class AudioExtractor:
    """Audio extraction utility class supporting multiple methods"""
    
    def __init__(self, prefer_method="auto"):
        """
        Initialize the audio extractor
        
        Args:
            prefer_method: Preferred extraction method ("moviepy", "ffmpeg", "auto")
        """
        self.prefer_method = prefer_method
        self.available_methods = self._check_available_methods()
    
    def _check_available_methods(self):
        """Check which extraction methods are available"""
        methods = {}
        
        # Check for moviepy
        try:
            import moviepy.editor
            methods["moviepy"] = True
        except ImportError:
            methods["moviepy"] = False
        
        # Check for ffmpeg CLI
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            methods["ffmpeg"] = True
        except:
            methods["ffmpeg"] = False
        
        # Check for ffmpeg-python
        try:
            import ffmpeg
            methods["ffmpeg_python"] = True
        except ImportError:
            methods["ffmpeg_python"] = False
        
        return methods
    
    def extract_audio(self, video_path, audio_path=None, method=None):
        """
        Main method to extract audio
        
        Args:
            video_path: Path to the input video
            audio_path: Path for the output audio file
            method: Extraction method ("moviepy", "ffmpeg", "ffmpeg_python", "auto")
        
        Returns:
            str: Path to the extracted audio file, or None if extraction fails
        """
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return None
        
        if audio_path is None:
            base_name = os.path.splitext(video_path)[0]
            audio_path = f"{base_name}_audio.mp3"
        
        # Determine extraction method
        if method is None:
            method = self.prefer_method
        
        if method == "auto":
            # Automatically select the best available method
            if self.available_methods.get("moviepy"):
                method = "moviepy"
            elif self.available_methods.get("ffmpeg_python"):
                method = "ffmpeg_python"
            elif self.available_methods.get("ffmpeg"):
                method = "ffmpeg"
            else:
                print("❌ No available audio extraction method found")
                return None
        
        print(f"🎬 Using method '{method}' for audio extraction...")
        
        # Execute according to the selected method
        if method == "moviepy" and self.available_methods.get("moviepy"):
            return self._extract_with_moviepy(video_path, audio_path)
        elif method == "ffmpeg_python" and self.available_methods.get("ffmpeg_python"):
            return self._extract_with_ffmpeg_python(video_path, audio_path)
        elif method == "ffmpeg" and self.available_methods.get("ffmpeg"):
            return self._extract_with_ffmpeg_cli(video_path, audio_path)
        else:
            print(f"❌ Method '{method}' is not available")
            return None
    
    def _extract_with_moviepy(self, video_path, audio_path):
        """Extract audio using moviepy"""
        try:
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            audio = video.audio
            audio.write_audiofile(audio_path, verbose=False, logger=None)
            audio.close()
            video.close()
            print(f"✅ Audio saved: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ Audio extraction with moviepy failed: {e}")
            return None
    
    def _extract_with_ffmpeg_python(self, video_path, audio_path):
        """Extract audio using ffmpeg-python"""
        try:
            import ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='mp3', audio_bitrate='192k')
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"✅ Audio saved: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ Audio extraction with ffmpeg-python failed: {e}")
            return None
    
    def _extract_with_ffmpeg_cli(self, video_path, audio_path):
        """Extract audio using ffmpeg command line"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "mp3",
                "-ab", "192k",
                "-ar", "44100",
                audio_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"✅ Audio saved: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ Audio extraction with ffmpeg CLI failed: {e}")
            return None
    
    def get_available_methods(self):
        """Return a list of available extraction methods"""
        return [method for method, available in self.available_methods.items() if available]