"""
视频合成模块（增强版）
功能：
1. 合并视频和新音频
2. 自动时长对齐
3. 混合原音频（可选）
4. 生成SRT字幕
5. 烧录字幕（多种样式）
   - 默认样式
   - 黄色底部样式
   - 模糊底条样式（漂亮推荐）
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import timedelta


class VideoComposer:
    """视频合成器 - 增强版"""
    
    # 字幕样式预设
    SUBTITLE_STYLES = {
        "default": {
            "name": "默认样式",
            "description": "简单的白色字幕带黑色描边",
            "force_style": (
                "FontName=Arial,"
                "FontSize=24,"
                "PrimaryColour=&HFFFFFF&,"
                "OutlineColour=&H000000&,"
                "Outline=2,"
                "Shadow=1,"
                "MarginV=30"
            )
        },
        "yellow_bottom": {
            "name": "黄色底部",
            "description": "黄色字幕，底部居中，黑色描边",
            "force_style": (
                "FontName=Arial,"
                "FontSize=20,"
                "PrimaryColour=&H00FFFF&,"
                "OutlineColour=&H000000&,"
                "Outline=2,"
                "Shadow=1,"
                "MarginV=30"
            )
        },
        "blurred_bar": {
            "name": "模糊底条（推荐）",
            "description": "柔和的模糊底条背景 + 白色黑边字幕",
            "force_style": (
                "FontName=Arial,"
                "FontSize=26,"
                "PrimaryColour=&HFFFFFF&,"
                "BackColour=&H00000000&,"
                "OutlineColour=&H00000000&,"
                "BorderStyle=1,"
                "Outline=2,"
                "Shadow=0,"
                "Alignment=2"
            ),
            "requires_filter": True  # 需要特殊的视频滤镜
        }
    }
    
    def __init__(self):
        """初始化视频合成器"""
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True,
                check=True
            )
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
            subtitle_style: 字幕样式 ("default", "yellow_bottom", "blurred_bar")
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
            print("=" * 80)
            print("🎬 Step 5: 视频合成")
            print("=" * 80)
            
            # 先对齐音视频时长
            aligned_audio = self._align_audio_to_video(video_path, audio_path, output_path)
            if not aligned_audio:
                print("⚠️  音频对齐失败，使用原音频")
                aligned_audio = audio_path
            
            # 根据配置选择合成方式
            if subtitle_path and os.path.exists(subtitle_path):
                # 有字幕的情况
                style_name = self.SUBTITLE_STYLES.get(subtitle_style, self.SUBTITLE_STYLES["default"])["name"]
                print(f"📝 字幕样式: {style_name}")
                
                return self._compose_with_subtitles(
                    video_path, aligned_audio, output_path,
                    subtitle_path, subtitle_style, keep_original_audio
                )
            else:
                # 无字幕的情况
                print("📝 无字幕模式")
                return self._compose_without_subtitles(
                    video_path, aligned_audio, output_path, keep_original_audio
                )
        
        except Exception as e:
            print(f"❌ 视频合成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _align_audio_to_video(self, video_path, audio_path, output_path):
        """
        自动对齐音频和视频的时长
        Returns: 对齐后的音频路径
        """
        try:
            video_dur = self._get_duration(video_path)
            audio_dur = self._get_duration(audio_path)
            
            print(f"📊 视频时长: {video_dur:.1f}s")
            print(f"📊 音频时长: {audio_dur:.1f}s")
            
            # 如果时长差异小于0.5秒，不需要对齐
            if abs(video_dur - audio_dur) <= 0.5:
                print("✅ 时长已对齐，无需调整")
                return audio_path
            
            # 创建对齐后的音频
            aligned_audio = str(Path(output_path).parent / "aligned_audio.wav")
            shorter = min(video_dur, audio_dur)
            
            print(f"⚙️  对齐音频长度 → {shorter:.1f}s")
            
            subprocess.run([
                "ffmpeg", "-y",
                "-i", audio_path,
                "-t", str(shorter),
                "-c", "copy",
                aligned_audio
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            print("✅ 音频对齐完成")
            return aligned_audio
        
        except:
            return None
    
    def _get_duration(self, file_path):
        """获取媒体文件时长"""
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
        """合成视频（无字幕）"""
        print("\n🔄 合并视频和音频...")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        if keep_original_audio:
            # 混合原音频和新音频
            cmd.extend([
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest[aout]",
                "-map", "0:v:0",
                "-map", "[aout]"
            ])
        else:
            # 只使用新音频
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
            print(f"✅ 视频已保存: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ 合成失败")
            if result.stderr:
                print(f"   错误信息: {result.stderr[-300:]}")
            return False
    
    def _compose_with_subtitles(self, video_path, audio_path, output_path, 
                                 subtitle_path, style, keep_original_audio):
        """合成视频（带字幕）"""
        style_config = self.SUBTITLE_STYLES.get(style, self.SUBTITLE_STYLES["default"])
        
        # 检查是否需要模糊底条效果
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
        """合成视频（简单字幕样式）"""
        print("\n🔄 合并视频、音频和字幕...")
        
        # 转义字幕路径
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        
        # 构建字幕滤镜
        force_style = style_config.get("force_style", "")
        subtitles_filter = f"subtitles={subtitle_path_escaped}:force_style='{force_style}'"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path
        ]
        
        # 音频处理
        if keep_original_audio:
            # 混合原音频和新音频，并添加字幕
            cmd.extend([
                "-filter_complex", 
                f"[0:a][1:a]amix=inputs=2:duration=shortest[aout];[0:v]{subtitles_filter}[vout]",
                "-map", "[vout]",
                "-map", "[aout]"
            ])
        else:
            # 只使用新音频，添加字幕
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
            print(f"✅ 视频已保存: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ 合成失败")
            if result.stderr:
                print(f"   错误信息: {result.stderr[-300:]}")
            return False
    
    def _compose_with_blurred_subtitles(self, video_path, audio_path, output_path, 
                                         subtitle_path, style_config, keep_original_audio):
        """
        合成视频（模糊底条字幕样式）
        创建柔和的模糊底条背景，然后叠加清晰的白色黑边字幕
        """
        print("\n🔄 合并视频、音频和模糊底条字幕...")
        print("   提示: 这个样式最漂亮，但渲染时间稍长")
        
        # 转义字幕路径
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
        
        # 获取字幕样式
        force_style = style_config.get("force_style", "")
        
        # 构建复杂的视频滤镜
        # 1. 分离视频流为两份
        # 2. 一份模糊底部25%区域
        # 3. 混合模糊底条到原视频
        # 4. 叠加字幕
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
        
        # 音频处理
        if keep_original_audio:
            # 混合原音频和新音频
            cmd.extend([
                "-filter_complex", 
                f"{vf_filter}[vout];[0:a][1:a]amix=inputs=2:duration=shortest[aout]",
                "-map", "[vout]",
                "-map", "[aout]"
            ])
        else:
            # 只使用新音频
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
        
        print("   正在渲染（包含模糊效果）...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ 视频已保存: {output_path}")
            print("=" * 80)
            return True
        else:
            print(f"❌ 合成失败")
            if result.stderr:
                print(f"   错误信息: {result.stderr[-300:]}")
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
            
            # 确保输出目录存在
            Path(output_srt_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                subtitle_index = 1
                
                for sent in sentences:
                    # 优先使用英文翻译，否则使用通用翻译字段
                    text = sent.get("text_en", sent.get("text_translated", ""))
                    start = sent.get("start", 0)
                    end = sent.get("end", 0)
                    
                    # 跳过失败的句子或空文本
                    if "[FAILED:" in text or not text or not text.strip():
                        continue
                    
                    # 写入字幕（使用更精确的时间戳格式）
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{self._sec_to_timestamp(start)} --> {self._sec_to_timestamp(end)}\n")
                    f.write(f"{text.strip()}\n\n")
                    
                    subtitle_index += 1
            
            print(f"✅ 字幕文件已保存: {output_srt_path} ({subtitle_index-1} 条)")
            return True
        
        except Exception as e:
            print(f"❌ 字幕生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _sec_to_timestamp(self, seconds):
        """
        将浮点秒转换为 SRT 格式时间戳
        格式: 00:00:00,000
        """
        td = timedelta(seconds=seconds)
        timestamp = str(td)
        
        # 处理时间戳格式
        if '.' in timestamp:
            # 有毫秒
            timestamp = timestamp.replace('.', ',')
            # 确保毫秒是3位
            parts = timestamp.split(',')
            if len(parts) == 2:
                ms = parts[1][:3].ljust(3, '0')
                timestamp = f"{parts[0]},{ms}"
        else:
            # 没有毫秒，添加 ,000
            timestamp = f"{timestamp},000"
        
        # 确保格式为 HH:MM:SS,mmm
        if timestamp.count(':') == 2:
            return timestamp.rjust(12, "0")
        else:
            # 补充缺失的小时部分
            return f"00:{timestamp}".rjust(12, "0")
    
    def get_video_info(self, video_path):
        """
        获取视频信息
        Returns: dict with duration, width, height, fps
        """
        try:
            # 获取时长
            duration = self._get_duration(video_path)
            
            # 获取分辨率和帧率
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
                
                # 计算FPS
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
            "width": 0,
            "height": 0,
            "fps": 0
        }