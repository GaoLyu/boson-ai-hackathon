"""
视频语言翻译 Streamlit 应用
功能: 上传视频 -> 提取音频 -> 语音识别 -> 翻译 -> 生成新音频 -> 合成视频
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
import json

# 导入自定义模块
from modules.audio_extractor import AudioExtractor
from modules.transcriber import Transcriber
from modules.translator import Translator
from modules.tts_generator import TTSGenerator
from modules.video_composer import VideoComposer

# 页面配置
st.set_page_config(
    page_title="视频语言翻译工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    </style>
    """, unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'processing_stage' not in st.session_state:
        st.session_state.processing_stage = 0
    if 'temp_files' not in st.session_state:
        st.session_state.temp_files = {}
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None
    if 'audio_path' not in st.session_state:
        st.session_state.audio_path = None
    if 'transcript' not in st.session_state:
        st.session_state.transcript = None
    if 'translation' not in st.session_state:
        st.session_state.translation = None
    if 'output_video_path' not in st.session_state:
        st.session_state.output_video_path = None


def main():
    """主函数"""
    init_session_state()
    
    # 标题和说明
    st.title("🎬 视频语言翻译工具")
    st.markdown("### 将您的视频翻译成任何语言，保持原始风格")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置选项")
        
        # 目标语言选择
        target_language = st.selectbox(
            "选择目标语言",
            options=[
                "英语 (English)",
                "中文 (Chinese)",
                "日语 (Japanese)",
                "韩语 (Korean)",
                "法语 (French)",
                "德语 (German)",
                "西班牙语 (Spanish)",
                "俄语 (Russian)",
                "阿拉伯语 (Arabic)",
                "印地语 (Hindi)"
            ],
            index=0
        )
        
        # 解析语言代码
        language_map = {
            "英语 (English)": "en",
            "中文 (Chinese)": "zh",
            "日语 (Japanese)": "ja",
            "韩语 (Korean)": "ko",
            "法语 (French)": "fr",
            "德语 (German)": "de",
            "西班牙语 (Spanish)": "es",
            "俄语 (Russian)": "ru",
            "阿拉伯语 (Arabic)": "ar",
            "印地语 (Hindi)": "hi"
        }
        target_lang_code = language_map[target_language]
        
        st.divider()
        
        # 高级选项
        with st.expander("🔧 高级选项"):
            add_subtitles = st.checkbox("添加字幕", value=True)
            subtitle_style = st.selectbox(
                "字幕样式",
                ["默认", "自定义（黄色底部）"],
                disabled=not add_subtitles
            )
            
            keep_original_audio = st.checkbox("保留原音频（混合）", value=False)
            audio_bitrate = st.select_slider(
                "音频比特率",
                options=["128k", "192k", "256k", "320k"],
                value="192k"
            )
        
        st.divider()
        
        # 处理进度
        st.header("📊 处理进度")
        progress_text = ["等待上传", "提取音频", "语音识别", "翻译文本", "生成音频", "合成视频"]
        for i, text in enumerate(progress_text):
            if i < st.session_state.processing_stage:
                st.success(f"✅ {text}")
            elif i == st.session_state.processing_stage:
                st.info(f"⏳ {text}")
            else:
                st.text(f"⭕ {text}")
    
    # 主内容区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 步骤 1: 上传视频")
        uploaded_file = st.file_uploader(
            "选择要翻译的视频文件",
            type=["mp4", "avi", "mov", "mkv", "flv"],
            help="支持常见视频格式: MP4, AVI, MOV, MKV, FLV"
        )
        
        if uploaded_file is not None:
            # 保存上传的视频
            if st.session_state.video_path is None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    st.session_state.video_path = tmp_file.name
            
            # 显示视频预览
            st.video(st.session_state.video_path)
            
            # 视频信息
            video_size = os.path.getsize(st.session_state.video_path) / (1024 * 1024)
            st.info(f"📹 视频大小: {video_size:.2f} MB")
            
            st.divider()
            
            # 开始处理按钮
            st.header("🚀 步骤 2: 开始处理")
            
            if st.button("开始翻译视频", type="primary"):
                process_video(
                    st.session_state.video_path,
                    target_lang_code,
                    add_subtitles,
                    subtitle_style,
                    keep_original_audio,
                    audio_bitrate
                )
    
    with col2:
        st.header("ℹ️ 使用说明")
        st.markdown("""
        **处理流程:**
        1. 📤 上传您的视频文件
        2. 🌍 选择目标语言
        3. ⚙️ 调整高级选项（可选）
        4. 🚀 点击"开始翻译视频"
        5. ⏳ 等待处理完成
        6. 📥 下载翻译后的视频
        
        **注意事项:**
        - 处理时间取决于视频长度
        - 建议视频时长 < 10分钟
        - 保持网络连接稳定
        - 首次使用需要下载模型
        
        **支持的语言:**
        - 自动识别源语言
        - 支持10+种目标语言
        - 保持原视频风格
        """)


def process_video(video_path, target_lang, add_subs, sub_style, keep_audio, bitrate):
    """处理视频的主流程"""
    
    # 创建临时工作目录
    work_dir = tempfile.mkdtemp()
    
    try:
        # ========== 步骤 1: 提取音频 ==========
        st.session_state.processing_stage = 1
        with st.spinner("🎵 正在提取音频..."):
            extractor = AudioExtractor()
            audio_path = os.path.join(work_dir, "audio.mp3")
            
            result = extractor.extract_audio(video_path, audio_path)
            
            if result:
                st.session_state.audio_path = audio_path
                st.success("✅ 音频提取完成")
            else:
                st.error("❌ 音频提取失败")
                return
        
        # ========== 步骤 2: 语音识别 ==========
        st.session_state.processing_stage = 2
        with st.spinner("🎤 正在识别语音..."):
            transcriber = Transcriber()
            transcript_path = os.path.join(work_dir, "transcript.json")
            
            success = transcriber.transcribe(audio_path, transcript_path)
            
            if success:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    st.session_state.transcript = json.load(f)
                st.success("✅ 语音识别完成")
                
                # 显示识别的文本
                with st.expander("📝 查看识别文本"):
                    if isinstance(st.session_state.transcript, list) and len(st.session_state.transcript) > 0:
                        sentences = st.session_state.transcript[0].get("sentence_info", [])
                        for i, sent in enumerate(sentences[:5], 1):
                            st.text(f"{i}. {sent.get('text', '')}")
                        if len(sentences) > 5:
                            st.text(f"... 共 {len(sentences)} 句")
            else:
                st.error("❌ 语音识别失败")
                return
        
        # ========== 步骤 3: 翻译文本 ==========
        st.session_state.processing_stage = 3
        with st.spinner(f"🌍 正在翻译到 {target_lang}..."):
            translator = Translator()
            translated_path = os.path.join(work_dir, "translated.json")
            
            success = translator.translate(transcript_path, translated_path, target_lang)
            
            if success:
                with open(translated_path, 'r', encoding='utf-8') as f:
                    st.session_state.translation = json.load(f)
                st.success("✅ 文本翻译完成")
                
                # 显示翻译结果
                with st.expander("🌍 查看翻译文本"):
                    if isinstance(st.session_state.translation, list) and len(st.session_state.translation) > 0:
                        sentences = st.session_state.translation[0].get("sentence_info", [])
                        for i, sent in enumerate(sentences[:5], 1):
                            orig = sent.get('text', '')
                            trans = sent.get('text_en', '') if target_lang == 'en' else sent.get('text_translated', '')
                            st.text(f"{i}. {orig}")
                            st.text(f"   → {trans}")
                            st.text("")
                        if len(sentences) > 5:
                            st.text(f"... 共 {len(sentences)} 句")
            else:
                st.error("❌ 文本翻译失败")
                return
        
        # ========== 步骤 4: 生成音频 ==========
        st.session_state.processing_stage = 4
        with st.spinner("🔊 正在生成新音频..."):
            tts = TTSGenerator()
            new_audio_path = os.path.join(work_dir, "translated_audio.mp3")
            
            # 传入原始音频路径用于语音克隆
            success = tts.generate(
                translated_path, 
                new_audio_path, 
                target_lang, 
                bitrate,
                original_audio_path=st.session_state.audio_path  # 传入原始音频
            )
            
            if success:
                st.success("✅ 音频生成完成")
                
                # 播放新音频
                with st.expander("🔊 试听翻译音频"):
                    st.audio(new_audio_path)
            else:
                st.error("❌ 音频生成失败")
                return
        
        # ========== 步骤 5: 合成视频 ==========
        st.session_state.processing_stage = 5
        with st.spinner("🎬 正在合成最终视频..."):
            composer = VideoComposer()
            output_path = os.path.join(work_dir, "output_video.mp4")
            
            # 准备字幕（如果需要）
            subtitle_path = None
            if add_subs:
                subtitle_path = os.path.join(work_dir, "subtitles.srt")
                composer.create_subtitles(translated_path, subtitle_path)
            
            # 合成视频
            success = composer.compose(
                video_path=video_path,
                audio_path=new_audio_path,
                output_path=output_path,
                subtitle_path=subtitle_path,
                subtitle_style="custom" if sub_style == "自定义（黄色底部）" else "default",
                keep_original_audio=keep_audio
            )
            
            if success:
                st.session_state.output_video_path = output_path
                st.session_state.processing_stage = 6
                st.success("✅ 视频合成完成！")
                
                # 显示最终视频
                st.header("🎉 处理完成！")
                st.video(output_path)
                
                # 文件信息
                output_size = os.path.getsize(output_path) / (1024 * 1024)
                st.info(f"📹 输出视频大小: {output_size:.2f} MB")
                
                # 下载按钮
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="📥 下载翻译后的视频",
                        data=f.read(),
                        file_name=f"translated_video_{target_lang}.mp4",
                        mime="video/mp4"
                    )
                
                # 统计信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("处理阶段", "6/6")
                with col2:
                    if st.session_state.transcript:
                        sentences = st.session_state.transcript[0].get("sentence_info", [])
                        st.metric("识别句子数", len(sentences))
                with col3:
                    st.metric("目标语言", target_lang.upper())
                
            else:
                st.error("❌ 视频合成失败")
                return
    
    except Exception as e:
        st.error(f"❌ 处理过程中出现错误: {str(e)}")
        import traceback
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())
    
    finally:
        # 清理临时文件（可选）
        pass


if __name__ == "__main__":
    main()