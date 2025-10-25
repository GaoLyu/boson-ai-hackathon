"""
音频提取模块
从视频中提取音频
"""

import os
import subprocess
from pathlib import Path


class AudioExtractor:
    """音频提取工具类，支持多种方法"""
    
    def __init__(self, prefer_method="auto"):
        """
        初始化音频提取器
        
        Args:
            prefer_method: 优先使用的方法 ("moviepy", "ffmpeg", "auto")
        """
        self.prefer_method = prefer_method
        self.available_methods = self._check_available_methods()
    
    def _check_available_methods(self):
        """检查可用的提取方法"""
        methods = {}
        
        # 检查moviepy
        try:
            import moviepy.editor
            methods["moviepy"] = True
        except ImportError:
            methods["moviepy"] = False
        
        # 检查ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            methods["ffmpeg"] = True
        except:
            methods["ffmpeg"] = False
        
        # 检查ffmpeg-python
        try:
            import ffmpeg
            methods["ffmpeg_python"] = True
        except ImportError:
            methods["ffmpeg_python"] = False
        
        return methods
    
    def extract_audio(self, video_path, audio_path=None, method=None):
        """
        提取音频的主方法
        
        Args:
            video_path: 输入视频路径
            audio_path: 输出音频路径
            method: 指定方法 ("moviepy", "ffmpeg", "ffmpeg_python", "auto")
        
        Returns:
            str: 输出的音频文件路径，失败返回None
        """
        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            return None
        
        if audio_path is None:
            base_name = os.path.splitext(video_path)[0]
            audio_path = f"{base_name}_audio.mp3"
        
        # 确定使用的方法
        if method is None:
            method = self.prefer_method
        
        if method == "auto":
            # 自动选择最佳方法
            if self.available_methods.get("moviepy"):
                method = "moviepy"
            elif self.available_methods.get("ffmpeg_python"):
                method = "ffmpeg_python"
            elif self.available_methods.get("ffmpeg"):
                method = "ffmpeg"
            else:
                print("❌ 没有可用的音频提取方法")
                return None
        
        print(f"🎬 使用方法 '{method}' 提取音频...")
        
        # 根据选择的方法调用相应的函数
        if method == "moviepy" and self.available_methods.get("moviepy"):
            return self._extract_with_moviepy(video_path, audio_path)
        elif method == "ffmpeg_python" and self.available_methods.get("ffmpeg_python"):
            return self._extract_with_ffmpeg_python(video_path, audio_path)
        elif method == "ffmpeg" and self.available_methods.get("ffmpeg"):
            return self._extract_with_ffmpeg_cli(video_path, audio_path)
        else:
            print(f"❌ 方法 '{method}' 不可用")
            return None
    
    def _extract_with_moviepy(self, video_path, audio_path):
        """使用moviepy提取"""
        try:
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            audio = video.audio
            audio.write_audiofile(audio_path, verbose=False, logger=None)
            audio.close()
            video.close()
            print(f"✅ 音频已保存: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ moviepy提取失败: {e}")
            return None
    
    def _extract_with_ffmpeg_python(self, video_path, audio_path):
        """使用ffmpeg-python提取"""
        try:
            import ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='mp3', audio_bitrate='192k')
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"✅ 音频已保存: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ ffmpeg-python提取失败: {e}")
            return None
    
    def _extract_with_ffmpeg_cli(self, video_path, audio_path):
        """使用ffmpeg命令行提取"""
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
            print(f"✅ 音频已保存: {audio_path}")
            return audio_path
        except Exception as e:
            print(f"❌ ffmpeg命令行提取失败: {e}")
            return None
    
    def get_available_methods(self):
        """获取可用的方法列表"""
        return [method for method, available in self.available_methods.items() if available]