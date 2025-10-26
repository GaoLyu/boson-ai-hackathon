"""
视频语言翻译 Streamlit 应用
功能: 上传视频 -> 提取音频 -> 语音识别 -> 翻译 -> 生成新音频 -> 合成视频
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
import json
import time

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
    .edit-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin: 1rem 0;
    }
    .sentence-item {
        background-color: white;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
        border: 1px solid #e9ecef;
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
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'target_lang' not in st.session_state:
        st.session_state.target_lang = None
    if 'output_video_data' not in st.session_state:
        st.session_state.output_video_data = None
    if 'edited_transcript' not in st.session_state:
        st.session_state.edited_transcript = None
    if 'edited_translation' not in st.session_state:
        st.session_state.edited_translation = None
    if 'transcript_edited' not in st.session_state:
        st.session_state.transcript_edited = False
    if 'translation_edited' not in st.session_state:
        st.session_state.translation_edited = False
    if 'waiting_for_transcript_edit' not in st.session_state:
        st.session_state.waiting_for_transcript_edit = False
    if 'waiting_for_translation_edit' not in st.session_state:
        st.session_state.waiting_for_translation_edit = False


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
            # 字幕选项
            add_subtitles = st.checkbox("添加字幕", value=True)
            subtitle_style = st.selectbox(
                "字幕样式",
                options=["default", "yellow_bottom", "blurred_bar"],
                format_func=lambda x: {
                    "default": "默认样式（简单白色）",
                    "yellow_bottom": "黄色底部（经典）",
                    "blurred_bar": "模糊底条（推荐✨）"
                }[x],
                index=2,  # 默认选择模糊底条
                disabled=not add_subtitles,
                help="模糊底条效果最漂亮，但渲染时间稍长"
            )
            
            # 音频选项
            keep_original_audio = st.checkbox("保留原音频（混合）", value=False)
            audio_bitrate = st.select_slider(
                "音频比特率",
                options=["128k", "192k", "256k", "320k"],
                value="192k"
            )
            
            st.divider()
            
            # TTS选项
            st.subheader("🎤 语音生成选项")
            
            voice_mode = st.radio(
                "声音模式",
                options=["clone", "preset"],
                format_func=lambda x: "🎭 克隆原视频音色" if x == "clone" else "🎵 使用预设声音",
                index=0,
                help="克隆模式：保持原视频说话者的音色\n预设模式：使用AI模型的内置声音"
            )
            
            if voice_mode == "preset":
                preset_voice = st.selectbox(
                    "选择预设声音",
                    options=[
                        "female_american",
                        "female_british", 
                        "male_american",
                        "male_british"
                    ],
                    format_func=lambda x: {
                        "female_american": "👩 美式女声（清晰温暖）",
                        "female_british": "👩 英式女声（优雅）",
                        "male_american": "👨 美式男声（沉稳）",
                        "male_british": "👨 英式男声（磁性）"
                    }[x],
                    index=0
                )
            else:
                preset_voice = "female_american"  # 默认值
            
            st.info("💡 **智能音频处理**：系统会自动尝试分离人声和背景音，以提高识别准确度和配音质量")

            separate_vocals = True
            keep_background = True

            bgm_volume = st.slider(
                "背景音音量",
                min_value=0.0,
                max_value=1.0,
                value=0.18,
                step=0.02,
                help="调整最终视频中背景音乐的音量"
            )
        
        st.divider()
        
        # 处理进度
        st.header("📊 处理进度")
        # 创建进度显示的占位符
        if 'progress_placeholder' not in st.session_state:
            st.session_state.progress_placeholder = st.empty()
        
        # 定义更新函数并存储在 session state 中
        def update_progress_display():
            with st.session_state.progress_placeholder.container():
                progress_text = ["等待上传", "提取音频", "语音识别", "编辑原文", "翻译文本", "编辑译文", "生成音频", "合成视频"]
                for i, text in enumerate(progress_text):
                    if i < st.session_state.processing_stage:
                        st.success(f"✅ {text}")
                    elif i == st.session_state.processing_stage:
                        st.info(f"⏳ {text}")
                    else:
                        st.text(f"⭕ {text}")
        
        # 将函数存储在 session state 中
        st.session_state.update_progress_display = update_progress_display
        
        # 初始显示或更新显示
        update_progress_display()
    
    # 主内容区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 如果处理已完成，显示结果
        if st.session_state.processing_complete and st.session_state.output_video_path:
            st.header("🎉 处理完成！")
            
            # 显示最终视频
            st.video(st.session_state.output_video_path)
            
            # 文件信息
            if os.path.exists(st.session_state.output_video_path):
                output_size = os.path.getsize(st.session_state.output_video_path) / (1024 * 1024)
                st.info(f"📹 输出视频大小: {output_size:.2f} MB")
            
            # 下载按钮 - 使用预加载的数据
            if st.session_state.output_video_data:
                st.download_button(
                    label="📥 下载翻译后的视频",
                    data=st.session_state.output_video_data,
                    file_name=f"translated_video_{st.session_state.target_lang}.mp4",
                    mime="video/mp4",
                    key="download_button"
                )
            
            # 统计信息
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("处理阶段", "8/8")
            with col_b:
                if st.session_state.transcript:
                    sentences = st.session_state.transcript[0].get("sentence_info", [])
                    st.metric("识别句子数", len(sentences))
            with col_c:
                st.metric("目标语言", st.session_state.target_lang.upper() if st.session_state.target_lang else "")
            
            st.divider()
            
            # 重新开始按钮
            if st.button("🔄 翻译新视频", type="secondary"):
                # 清空所有状态
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # 等待转录编辑的状态
        elif st.session_state.waiting_for_transcript_edit:
            edit_transcript_interface(st.session_state.transcript, st.session_state.work_dir)
        
        # 等待翻译编辑的状态
        elif st.session_state.waiting_for_translation_edit:
            edit_translation_interface(st.session_state.translation, st.session_state.work_dir, st.session_state.target_lang)
        
        else:
            # 未完成处理，显示上传界面
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
                    # 创建工作目录并存储在 session state
                    work_dir = tempfile.mkdtemp()
                    st.session_state.work_dir = work_dir
                    st.session_state.target_lang = target_lang_code
                    
                    process_video(
                        st.session_state.video_path,
                        target_lang_code,
                        add_subtitles,
                        subtitle_style,
                        keep_original_audio,
                        audio_bitrate,
                        voice_mode,
                        preset_voice,
                        separate_vocals,
                        keep_background,
                        bgm_volume
                    )
    
    with col2:
        st.header("ℹ️ 使用说明")
        st.markdown("""
        **处理流程:**
        1. 📤 上传您的视频文件
        2. 🌍 选择目标语言
        3. ⚙️ 调整高级选项（可选）
        4. 🚀 点击"开始翻译视频"
        5. ✏️ 编辑识别文本（可选）
        6. ✏️ 编辑翻译结果（可选）
        7. ⏳ 等待处理完成
        8. 📥 下载翻译后的视频
        
        **编辑功能:**
        - ✅ 可修改语音识别结果
        - ✅ 可调整时间节点
        - ✅ 可修改翻译结果
        - ✅ 实时预览效果
        
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


def edit_transcript_interface(transcript_data, work_dir):
    """编辑转录文本的界面"""
    st.header("✏️ 步骤 3: 编辑识别文本")
    st.info("请检查并修改语音识别结果。您可以修改文本内容或调整时间节点。")
    
    if not transcript_data or not isinstance(transcript_data, list) or len(transcript_data) == 0:
        st.error("没有可编辑的转录文本")
        return None
    
    sentences = transcript_data[0].get("sentence_info", [])
    
    # 初始化编辑状态
    if 'edited_sentences' not in st.session_state:
        st.session_state.edited_sentences = sentences.copy()
    
    # 显示编辑界面
    edited_sentences = []
    
    with st.form("edit_transcript_form"):
        st.subheader("编辑句子内容")
        
        for i, sentence in enumerate(st.session_state.edited_sentences):
            with st.container():
                st.markdown(f"**句子 {i+1}**")
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # 文本编辑
                    new_text = st.text_area(
                        f"文本内容 {i+1}",
                        value=sentence.get("text", ""),
                        key=f"text_{i}",
                        height=60,
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # 开始时间编辑
                    start_time = st.number_input(
                        f"开始时间 (秒) {i+1}",
                        value=float(sentence.get("start", 0)),
                        min_value=0.0,
                        step=0.1,
                        key=f"start_{i}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    # 结束时间编辑
                    end_time = st.number_input(
                        f"结束时间 (秒) {i+1}",
                        value=float(sentence.get("end", 0)),
                        min_value=0.0,
                        step=0.1,
                        key=f"end_{i}",
                        label_visibility="collapsed"
                    )
                
                # 更新时间戳
                if start_time >= end_time:
                    st.warning(f"句子 {i+1}: 开始时间不能大于或等于结束时间")
                    end_time = start_time + 1.0  # 自动调整
                
                edited_sentences.append({
                    "text": new_text,
                    "start": start_time,
                    "end": end_time
                })
                
                st.markdown("---")
        
        # 表单提交按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            skip_edit = st.form_submit_button("⏭️ 跳过编辑")
        with col2:
            submitted = st.form_submit_button("✅ 确认编辑并继续")
        
        if submitted:
            # 保存编辑后的数据
            edited_data = transcript_data.copy()
            edited_data[0]["sentence_info"] = edited_sentences
            
            # 保存到文件
            edited_path = os.path.join(work_dir, "edited_transcript.json")
            with open(edited_path, 'w', encoding='utf-8') as f:
                json.dump(edited_data, f, ensure_ascii=False, indent=2)
            
            st.session_state.edited_transcript = edited_data
            st.session_state.transcript_edited = True
            st.session_state.waiting_for_transcript_edit = False
            
            st.success("✅ 编辑已保存！继续翻译流程...")
            st.session_state.processing_stage = 4
            
            # 显示预览
            with st.expander("📋 编辑后预览"):
                for i, sent in enumerate(edited_sentences[:5]):
                    st.text(f"{i+1}. [{sent['start']:.1f}s-{sent['end']:.1f}s] {sent['text']}")
                if len(edited_sentences) > 5:
                    st.text(f"... 共 {len(edited_sentences)} 句")
            
            # 继续后续流程
            time.sleep(2)
            st.rerun()
            
        elif skip_edit:
            st.session_state.waiting_for_transcript_edit = False
            st.session_state.processing_stage = 4
            st.info("ℹ️ 跳过编辑，使用原始识别文本继续处理")
            time.sleep(2)
            st.rerun()
    
    return None


def edit_translation_interface(translation_data, work_dir, target_lang):
    """编辑翻译结果的界面"""
    st.header("✏️ 步骤 5: 编辑翻译结果")
    st.info("请检查并修改翻译结果。确保翻译准确且符合您的需求。")
    
    if not translation_data or not isinstance(translation_data, list) or len(translation_data) == 0:
        st.error("没有可编辑的翻译结果")
        return None
    
    sentences = translation_data[0].get("sentence_info", [])
    
    # 初始化编辑状态
    if 'edited_translations' not in st.session_state:
        st.session_state.edited_translations = sentences.copy()
    
    # 显示编辑界面
    edited_sentences = []
    
    with st.form("edit_translation_form"):
        st.subheader("编辑翻译内容")
        
        for i, sentence in enumerate(st.session_state.edited_translations):
            with st.container():
                st.markdown(f"**句子 {i+1}**")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 原文显示（只读）
                    st.text_area(
                        f"原文 {i+1}",
                        value=sentence.get("text", ""),
                        key=f"original_{i}",
                        height=80,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # 翻译编辑
                    if target_lang == "en":
                        field_name = "text_en"
                    else:
                        field_name = "text_translated"
                    
                    new_translation = st.text_area(
                        f"翻译 {i+1}",
                        value=sentence.get(field_name, ""),
                        key=f"translation_{i}",
                        height=80,
                        label_visibility="collapsed"
                    )
                
                edited_sentences.append({
                    "text": sentence.get("text", ""),
                    field_name: new_translation,
                    "start": sentence.get("start", 0),
                    "end": sentence.get("end", 0)
                })
                
                st.markdown("---")
        
        # 表单提交按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            skip_edit = st.form_submit_button("⏭️ 跳过编辑")
        with col2:
            submitted = st.form_submit_button("✅ 确认编辑并继续")
        
        if submitted:
            # 保存编辑后的数据
            edited_data = translation_data.copy()
            edited_data[0]["sentence_info"] = edited_sentences
            
            # 保存到文件
            edited_path = os.path.join(work_dir, "edited_translation.json")
            with open(edited_path, 'w', encoding='utf-8') as f:
                json.dump(edited_data, f, ensure_ascii=False, indent=2)
            
            st.session_state.edited_translation = edited_data
            st.session_state.translation_edited = True
            st.session_state.waiting_for_translation_edit = False
            
            st.success("✅ 翻译编辑已保存！继续生成音频...")
            st.session_state.processing_stage = 6
            
            # 显示预览
            with st.expander("📋 编辑后预览"):
                for i, sent in enumerate(edited_sentences[:5]):
                    orig = sent.get("text", "")
                    trans = sent.get(field_name, "")
                    st.text(f"{i+1}. 原文: {orig}")
                    st.text(f"    译文: {trans}")
                    st.text("")
                if len(edited_sentences) > 5:
                    st.text(f"... 共 {len(edited_sentences)} 句")
            
            # 继续后续流程
            time.sleep(2)
            st.rerun()
            
        elif skip_edit:
            st.session_state.waiting_for_translation_edit = False
            st.session_state.processing_stage = 6
            st.info("ℹ️ 跳过编辑，使用原始翻译结果继续处理")
            time.sleep(2)
            st.rerun()
    
    return None


def process_video(video_path, target_lang, add_subs, sub_style, keep_audio, bitrate,
                  voice_mode="clone", preset_voice="female_american", 
                  separate_vocals=False, keep_background=True, bgm_volume=0.18):
    """处理视频的主流程"""
    
    work_dir = st.session_state.work_dir
    
    def update_progress(stage):
        """更新进度并刷新显示"""
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== 步骤 1: 提取音频 ==========
        update_progress(1)
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
        update_progress(2)
        with st.spinner("🎤 正在识别语音..."):
            transcriber = Transcriber()
            transcript_path = os.path.join(work_dir, "transcript.json")
            
            success = transcriber.transcribe(audio_path, transcript_path)
            
            if success:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    st.session_state.transcript = json.load(f)
                st.success("✅ 语音识别完成")
            else:
                st.error("❌ 语音识别失败")
                return
        
        # ========== 步骤 3: 等待用户编辑转录文本 ==========
        update_progress(3)
        st.session_state.waiting_for_transcript_edit = True
        st.rerun()
        return  # 暂停流程，等待用户编辑
        
    except Exception as e:
        st.error(f"❌ 处理过程中出现错误: {str(e)}")
        import traceback
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())


def continue_after_transcript_edit():
    """在转录编辑后继续流程"""
    work_dir = st.session_state.work_dir
    target_lang = st.session_state.target_lang
    
    def update_progress(stage):
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== 步骤 4: 翻译文本 ==========
        update_progress(4)
        with st.spinner(f"🌍 正在翻译到 {target_lang}..."):
            translator = Translator()
            translated_path = os.path.join(work_dir, "translated.json")
            
            # 使用编辑后的转录文件（如果存在）
            if st.session_state.transcript_edited:
                input_path = os.path.join(work_dir, "edited_transcript.json")
            else:
                input_path = os.path.join(work_dir, "transcript.json")
            
            success = translator.translate(input_path, translated_path, target_lang)
            
            if success:
                with open(translated_path, 'r', encoding='utf-8') as f:
                    st.session_state.translation = json.load(f)
                st.success("✅ 文本翻译完成")
            else:
                st.error("❌ 文本翻译失败")
                return
        
        # ========== 步骤 5: 等待用户编辑翻译结果 ==========
        update_progress(5)
        st.session_state.waiting_for_translation_edit = True
        st.rerun()
        return  # 暂停流程，等待用户编辑
        
    except Exception as e:
        st.error(f"❌ 处理过程中出现错误: {str(e)}")
        import traceback
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())


def continue_after_translation_edit(video_path, add_subs, sub_style, keep_audio, bitrate,
                                   voice_mode, preset_voice, separate_vocals, keep_background, bgm_volume):
    """在翻译编辑后继续流程"""
    work_dir = st.session_state.work_dir
    target_lang = st.session_state.target_lang
    
    def update_progress(stage):
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== 步骤 6: 生成音频 ==========
        update_progress(6)
        with st.spinner("🔊 正在生成新音频..."):
            tts = TTSGenerator()
            new_audio_path = os.path.join(work_dir, "translated_audio.mp3")
            
            # 使用编辑后的翻译文件（如果存在）
            if st.session_state.translation_edited:
                final_translation_path = os.path.join(work_dir, "edited_translation.json")
            else:
                final_translation_path = os.path.join(work_dir, "translated.json")

            success = tts.generate(
                final_translation_path, 
                new_audio_path, 
                target_lang, 
                bitrate,
                original_audio_path=st.session_state.audio_path,
                voice_mode=voice_mode,
                preset_voice=preset_voice,
                separate_vocals=separate_vocals,
                keep_background=keep_background,
                bgm_volume=bgm_volume
            )
            
            if success:
                st.success("✅ 音频生成完成")
                
                # 播放新音频
                with st.expander("🔊 试听翻译音频"):
                    st.audio(new_audio_path)
            else:
                st.error("❌ 音频生成失败")
                return
        
        # ========== 步骤 7: 合成视频 ==========
        update_progress(7)
        with st.spinner("🎬 正在合成最终视频..."):
            composer = VideoComposer()
            output_path = os.path.join(work_dir, "output_video.mp4")
            
            # 准备字幕（如果需要）
            subtitle_path = None
            if add_subs:
                subtitle_path = os.path.join(work_dir, "subtitles.srt")
                composer.create_subtitles(final_translation_path, subtitle_path)
            
            # 合成视频
            success = composer.compose(
                video_path=video_path,
                audio_path=new_audio_path,
                output_path=output_path,
                subtitle_path=subtitle_path,
                subtitle_style=sub_style,
                keep_original_audio=keep_audio
            )
            
            if success:
                st.session_state.output_video_path = output_path
                st.session_state.processing_stage = 8
                update_progress(8)
                st.session_state.processing_complete = True
                
                # 预加载视频数据到内存
                with open(output_path, "rb") as f:
                    st.session_state.output_video_data = f.read()
                
                st.success("✅ 视频合成完成！")
                st.balloons()
                
                # 触发页面刷新以显示结果
                st.rerun()
            else:
                st.error("❌ 视频合成失败")
                return
    
    except Exception as e:
        st.error(f"❌ 处理过程中出现错误: {str(e)}")
        import traceback
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())


# 在 main 函数后添加流程继续的逻辑
if __name__ == "__main__":
    # 检查是否需要继续流程
    if (st.session_state.get('processing_stage', 0) >= 3 and 
        not st.session_state.get('waiting_for_transcript_edit', False) and
        not st.session_state.get('waiting_for_translation_edit', False) and
        not st.session_state.get('processing_complete', False)):
        
        if st.session_state.get('processing_stage', 0) == 4:
            continue_after_transcript_edit()
        elif st.session_state.get('processing_stage', 0) == 6:
            # 需要从 session state 获取参数
            continue_after_translation_edit(
                st.session_state.video_path,
                st.session_state.get('add_subs', True),
                st.session_state.get('sub_style', 'blurred_bar'),
                st.session_state.get('keep_audio', False),
                st.session_state.get('bitrate', '192k'),
                st.session_state.get('voice_mode', 'clone'),
                st.session_state.get('preset_voice', 'female_american'),
                st.session_state.get('separate_vocals', True),
                st.session_state.get('keep_background', True),
                st.session_state.get('bgm_volume', 0.18)
            )
    
    main()