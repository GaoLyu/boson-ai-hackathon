"""
视频合成模块
将新音频与原视频合并，可选添加字幕
"""

import os
import json
import subprocess


class VideoComposer:
    """视频合成器"""
    
    def __init__(self):
        """初始化视频合成器"""
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except:
            raise RuntimeError("❌ ffmpeg 未安装或不可用")
    
    def compose(self, video_path, audio_path, output_path, 
                subtitle_path=None, subtitle_style="default", keep_original_audio=False):
        """
        合成最终视频
        
        Args:
            video_path: 原视频路径
            audio_path: 新音频路径
            output_path: 输出视频路径
            subtitle_path: 字幕文件路径（可选）
            subtitle_style: 字幕样式 ("default" 或 "custom")
            keep_original_audio: 是否保留原音频并混合
        
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            return False
        
        if not os.path.exists(audio_path):
            print(f"❌ 音频文件不存在: {audio_path}")
            return False
        
        try:
            print("🎬 开始合成视频...")
            
            # 根据配置选择合成方式
            if subtitle_path and os.path.exists(subtitle_path):
                # 有字幕的情况
                return self._compose_with_subtitles(
                    video_path, audio_path, output_path,
                    subtitle_path, subtitle_style, keep_original_audio
                )
            else:
                # 无字幕的情况
                return self._compose_without_subtitles(
                    video_path, audio_path, output_path, keep_original_audio
                )
        
        except Exception as e:
            print(f"❌ 视频合成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _compose_without_subtitles(self, video_path, audio_path, output_path, keep_original_audio):
        """合成视频（无字幕）"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            # 混合原音频和新音频
            cmd.extend([
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                "-map", "0:v",
                "-map", "[aout]"
            ])
        else:
            # 只使用新音频
            cmd.extend([
                "-map", "0:v",
                "-map", "1:a"
            ])
        
        cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ])
        
        print("  🔄 处理中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ 视频已保存: {output_path}")
            return True
        else:
            print(f"  ❌ 失败: {result.stderr[:200]}")
            return False
    
    def _compose_with_subtitles(self, video_path, audio_path, output_path, 
                                 subtitle_path, style, keep_original_audio):
        """合成视频（带字幕）"""
        # 第一步：替换音频
        temp_video = output_path.replace(".mp4", "_temp.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            cmd.extend([
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                "-map", "0:v",
                "-map", "[aout]"
            ])
        else:
            cmd.extend([
                "-map", "0:v",
                "-map", "1:a"
            ])
        
        cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            temp_video
        ])
        
        print("  🔄 步骤 1/2: 替换音频...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  ❌ 音频替换失败: {result.stderr[:200]}")
            return False
        
        # 第二步：烧录字幕
        print("  🔄 步骤 2/2: 烧录字幕...")
        
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        
        if style == "custom":
            subtitles_filter = f"subtitles={subtitle_path_escaped}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,Outline=2,Shadow=1,MarginV=30'"
        else:
            subtitles_filter = f"subtitles={subtitle_path_escaped}"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-vf", subtitles_filter,
            "-c:a", "copy",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 删除临时文件
        if os.path.exists(temp_video):
            os.remove(temp_video)
        
        if result.returncode == 0:
            print(f"  ✅ 视频已保存: {output_path}")
            return True
        else:
            print(f"  ❌ 字幕烧录失败: {result.stderr[:200]}")
            return False
    
    def create_subtitles(self, translated_json_path, output_srt_path):
        """
        从翻译JSON生成SRT字幕文件
        
        Args:
            translated_json_path: 翻译后的JSON文件路径
            output_srt_path: 输出SRT文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            print("📝 生成SRT字幕...")
            
            with open(translated_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sentences = data[0].get("sentence_info", [])
            
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                subtitle_index = 1
                
                for sent in sentences:
                    # 优先使用英文翻译，否则使用通用翻译字段
                    text = sent.get("text_en", sent.get("text_translated", ""))
                    start = sent.get("start", 0)
                    end = sent.get("end", 0)
                    
                    # 跳过失败的句子
                    if "[FAILED:" in text or not text:
                        continue
                    
                    # 写入字幕
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{self._format_srt_time(start)} --> {self._format_srt_time(end)}\n")
                    f.write(f"{text}\n\n")
                    
                    subtitle_index += 1
            
            print(f"  ✅ 字幕文件已保存: {output_srt_path} ({subtitle_index-1} 条)")
            return True
        
        except Exception as e:
            print(f"  ❌ 字幕生成失败: {e}")
            return False
    
    def _format_srt_time(self, seconds):
        """格式化SRT时间戳 (00:00:01,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_video_duration(self, video_path):
        """获取视频时长（秒）"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0