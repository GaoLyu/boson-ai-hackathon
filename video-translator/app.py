"""
Video Language Translation Streamlit App
Function: Upload Video -> Extract Audio -> Speech Recognition -> Translation -> Generate New Audio -> Compose Final Video
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
import json
import time

# Import custom modules
from modules.audio_extractor import AudioExtractor
from modules.transcriber import Transcriber
from modules.translator import Translator
from modules.tts_generator import TTSGenerator
from modules.video_composer import VideoComposer

# Page configuration
st.set_page_config(
    page_title="Video Language Translator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    """Initialize session state"""
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
    """Main app"""
    init_session_state()
    
    # Title and description
    st.title("🎬 Video Language Translator")
    st.markdown("### Translate your video into any language while preserving the original style.")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Target language selection
        target_language = st.selectbox(
            "Select target language",
            options=[
                "English",
                "Chinese",
                "Japanese",
                "Korean",
                "French",
                "German",
                "Spanish",
                "Russian",
                "Arabic",
                "Hindi"
            ],
            index=0
        )
        
        # Parse language codes
        language_map = {
            "English": "en",
            "Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "French": "fr",
            "German": "de",
            "Spanish": "es",
            "Russian": "ru",
            "Arabic": "ar",
            "Hindi": "hi"
        }
        target_lang_code = language_map[target_language]
        
        st.divider()
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            # TTS options
            st.subheader("🎤 Voice Generation Options")
            
            voice_mode = st.radio(
                "Voice mode",
                options=["clone", "preset"],
                format_func=lambda x: "🎭 Clone original voice" if x == "clone" else "🎵 Use preset voice",
                index=0,
                help="Clone mode: Keep the original speaker’s timbre.\nPreset mode: Use AI model's built-in voice."
            )
            
            if voice_mode == "preset":
                preset_voice = st.selectbox(
                    "Select preset voice",
                    options=[
                        "female_american",
                        "female_british", 
                        "male_american",
                        "male_british"
                    ],
                    format_func=lambda x: {
                        "female_american": "👩 Female (Warm & Clear)",
                        "female_british": "👩 Female (Elegant)",
                        "male_american": "👨 Male (Calm)",
                        "male_british": "👨 Male (Deep)"
                    }[x],
                    index=0
                )
            else:
                preset_voice = "female_american"  # Default
            
            st.info("💡 **Smart audio processing**: The system will automatically separate vocals and background to improve recognition and dubbing quality.")

            separate_vocals = True
            keep_background = True

            bgm_volume = st.slider(
                "Background volume",
                min_value=0.0,
                max_value=1.0,
                value=0.18,
                step=0.02,
                help="Adjust the background music volume in the final video"
            )
            # Audio options
            keep_original_audio = st.checkbox("Keep original audio (mixed)", value=False)
            audio_bitrate = st.select_slider(
                "Audio bitrate",
                options=["128k", "192k", "256k", "320k"],
                value="192k"
            )
            
            st.divider()
            # Subtitle options
            add_subtitles = st.checkbox("Add subtitles", value=True)
            subtitle_style = st.selectbox(
                "Subtitle style",
                options=["default", "yellow_bottom", "blurred_bar"],
                format_func=lambda x: {
                    "default": "Default (Simple white)",
                    "yellow_bottom": "Yellow bottom (Classic)",
                    "blurred_bar": "Blurred bar (Recommended✨)"
                }[x],
                index=2,
                disabled=not add_subtitles,
                help="Blurred bar looks best but may take longer to render"
            )
        
        st.divider()
        
        # Processing progress
        st.header("📊 Processing Progress")
        if 'progress_placeholder' not in st.session_state:
            st.session_state.progress_placeholder = st.empty()
        
        # Define update function
        def update_progress_display():
            with st.session_state.progress_placeholder.container():
                progress_text = ["Waiting for upload", "Extracting audio", "Speech recognition", "Edit transcript", "Translating text", "Edit translation", "Generating audio", "Composing video"]
                for i, text in enumerate(progress_text):
                    if i < st.session_state.processing_stage:
                        st.success(f"✅ {text}")
                    elif i == st.session_state.processing_stage:
                        st.info(f"⏳ {text}")
                    else:
                        st.text(f"⭕ {text}")
        
        st.session_state.update_progress_display = update_progress_display
        update_progress_display()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.session_state.processing_complete and st.session_state.output_video_path:
            st.header("🎉 Processing Complete!")
            
            st.video(st.session_state.output_video_path)
            
            if os.path.exists(st.session_state.output_video_path):
                output_size = os.path.getsize(st.session_state.output_video_path) / (1024 * 1024)
                st.info(f"📹 Output video size: {output_size:.2f} MB")
            
            if st.session_state.output_video_data:
                st.download_button(
                    label="📥 Download Translated Video",
                    data=st.session_state.output_video_data,
                    file_name=f"translated_video_{st.session_state.target_lang}.mp4",
                    mime="video/mp4",
                    key="download_button"
                )
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Processing Stage", "8/8")
            with col_b:
                if st.session_state.transcript:
                    sentences = st.session_state.transcript[0].get("sentence_info", [])
                    st.metric("Recognized Sentences", len(sentences))
            with col_c:
                st.metric("Target Language", st.session_state.target_lang.upper() if st.session_state.target_lang else "")
            
            st.divider()
            
            if st.button("🔄 Translate New Video", type="secondary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        elif st.session_state.waiting_for_transcript_edit:
            edit_transcript_interface(st.session_state.transcript, st.session_state.work_dir)
        
        elif st.session_state.waiting_for_translation_edit:
            edit_translation_interface(st.session_state.translation, st.session_state.work_dir, st.session_state.target_lang)
        
        else:
            st.header("📁 Step 1: Upload Video")
            uploaded_file = st.file_uploader(
                "Select a video file to translate",
                type=["mp4", "avi", "mov", "mkv", "flv"],
                help="Supported formats: MP4, AVI, MOV, MKV, FLV"
            )
            
            if uploaded_file is not None:
                if st.session_state.video_path is None:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        st.session_state.video_path = tmp_file.name
                
                st.video(st.session_state.video_path)
                
                video_size = os.path.getsize(st.session_state.video_path) / (1024 * 1024)
                st.info(f"📹 Video size: {video_size:.2f} MB")
                
                st.divider()
                st.header("🚀 Step 2: Start Processing")
                
                if st.button("Start Translation", type="primary"):
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
        st.header("ℹ️ Instructions")
        st.markdown("""
        **Processing Steps:**
        1. 📤 Upload your video
        2. 🌍 Choose target language
        3. ⚙️ Adjust advanced options (optional)
        4. 🚀 Click "Start Translation"
        5. ✏️ Edit transcript (optional)
        6. ✏️ Edit translation (optional)
        7. ⏳ Wait for processing
        8. 📥 Download final video
        
        **Editing Features:**
        - ✅ Modify speech recognition text
        - ✅ Adjust timestamps
        - ✅ Edit translations
        - ✅ Real-time preview
        
        **Notes:**
        - Processing time depends on video length
        - Recommended video length < 10 minutes
        - Keep stable internet connection
        - Models will be downloaded on first use
        
        **Supported Languages:**
        - Auto-detect source language
        - 10+ target languages
        - Keeps original video style
        """)


def edit_transcript_interface(transcript_data, work_dir):
    """Interface for editing recognized transcript"""
    st.header("✏️ Step 3: Edit Recognized Transcript")
    st.info("Please check and modify the speech recognition results. You can edit the text or adjust timestamps.")
    
    if not transcript_data or not isinstance(transcript_data, list) or len(transcript_data) == 0:
        st.error("No editable transcript found")
        return None
    
    sentences = transcript_data[0].get("sentence_info", [])
    
    # Initialize edit state
    if 'edited_sentences' not in st.session_state:
        st.session_state.edited_sentences = sentences.copy()
    
    # Display editing interface
    edited_sentences = []
    
    with st.form("edit_transcript_form"):
        st.subheader("Edit Sentence Content")
        
        for i, sentence in enumerate(st.session_state.edited_sentences):
            with st.container():
                st.markdown(f"**Sentence {i+1}**")
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Edit text
                    new_text = st.text_area(
                        f"Sentence text {i+1}",
                        value=sentence.get("text", ""),
                        key=f"text_{i}",
                        height=60,
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # Edit start time
                    start_time = st.number_input(
                        f"Start time (sec) {i+1}",
                        value=float(sentence.get("start", 0)),
                        min_value=0.0,
                        step=0.1,
                        key=f"start_{i}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    # Edit end time
                    end_time = st.number_input(
                        f"End time (sec) {i+1}",
                        value=float(sentence.get("end", 0)),
                        min_value=0.0,
                        step=0.1,
                        key=f"end_{i}",
                        label_visibility="collapsed"
                    )
                
                # Update timestamps
                if start_time >= end_time:
                    st.warning(f"Sentence {i+1}: Start time cannot be greater than or equal to end time")
                    end_time = start_time + 1.0  # Auto adjust
                
                edited_sentences.append({
                    "text": new_text,
                    "start": start_time,
                    "end": end_time
                })
                
                st.markdown("---")
        
        # Submit buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            skip_edit = st.form_submit_button("⏭️ Skip Editing")
        with col2:
            submitted = st.form_submit_button("✅ Save and Continue")
        
        if submitted:
            # Save edited data
            edited_data = transcript_data.copy()
            edited_data[0]["sentence_info"] = edited_sentences
            
            # Save to file
            edited_path = os.path.join(work_dir, "edited_transcript.json")
            with open(edited_path, 'w', encoding='utf-8') as f:
                json.dump(edited_data, f, ensure_ascii=False, indent=2)
            
            st.session_state.edited_transcript = edited_data
            st.session_state.transcript_edited = True
            st.session_state.waiting_for_transcript_edit = False
            
            st.success("✅ Edits saved! Continuing to translation...")
            st.session_state.processing_stage = 4
            
            # Show preview
            with st.expander("📋 Preview Edited Transcript"):
                for i, sent in enumerate(edited_sentences[:5]):
                    st.text(f"{i+1}. [{sent['start']:.1f}s-{sent['end']:.1f}s] {sent['text']}")
                if len(edited_sentences) > 5:
                    st.text(f"... Total {len(edited_sentences)} sentences")
            
            # Continue next step
            time.sleep(2)
            st.rerun()
            
        elif skip_edit:
            st.session_state.waiting_for_transcript_edit = False
            st.session_state.processing_stage = 4
            st.info("ℹ️ Skipped editing — using original transcript for next step")
            time.sleep(2)
            st.rerun()
    
    return None


def edit_translation_interface(translation_data, work_dir, target_lang):
    """Interface for editing translation results"""
    st.header("✏️ Step 5: Edit Translation Results")
    st.info("Please check and modify the translated text. Ensure it’s accurate and fits your context.")
    
    if not translation_data or not isinstance(translation_data, list) or len(translation_data) == 0:
        st.error("No editable translation found")
        return None
    
    sentences = translation_data[0].get("sentence_info", [])
    
    # Initialize edit state
    if 'edited_translations' not in st.session_state:
        st.session_state.edited_translations = sentences.copy()
    
    # Display editing interface
    edited_sentences = []
    
    with st.form("edit_translation_form"):
        st.subheader("Edit Translation Content")
        
        for i, sentence in enumerate(st.session_state.edited_translations):
            with st.container():
                st.markdown(f"**Sentence {i+1}**")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Display original (read-only)
                    st.text_area(
                        f"Original {i+1}",
                        value=sentence.get("text", ""),
                        key=f"original_{i}",
                        height=80,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # Edit translation
                    if target_lang == "en":
                        field_name = "text_en"
                    else:
                        field_name = "text_translated"
                    
                    new_translation = st.text_area(
                        f"Translation {i+1}",
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
        
        # Submit buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            skip_edit = st.form_submit_button("⏭️ Skip Editing")
        with col2:
            submitted = st.form_submit_button("✅ Save and Continue")
        
        if submitted:
            # Save edited data
            edited_data = translation_data.copy()
            edited_data[0]["sentence_info"] = edited_sentences
            
            edited_path = os.path.join(work_dir, "edited_translation.json")
            with open(edited_path, 'w', encoding='utf-8') as f:
                json.dump(edited_data, f, ensure_ascii=False, indent=2)
            
            st.session_state.edited_translation = edited_data
            st.session_state.translation_edited = True
            st.session_state.waiting_for_translation_edit = False
            
            st.success("✅ Translation edits saved! Proceeding to audio generation...")
            st.session_state.processing_stage = 6
            
            # Show preview
            with st.expander("📋 Preview Edited Translations"):
                for i, sent in enumerate(edited_sentences[:5]):
                    orig = sent.get("text", "")
                    trans = sent.get(field_name, "")
                    st.text(f"{i+1}. Original: {orig}")
                    st.text(f"    Translation: {trans}")
                    st.text("")
                if len(edited_sentences) > 5:
                    st.text(f"... Total {len(edited_sentences)} sentences")
            
            time.sleep(2)
            st.rerun()
            
        elif skip_edit:
            st.session_state.waiting_for_translation_edit = False
            st.session_state.processing_stage = 6
            st.info("ℹ️ Skipped editing — using original translation for next step")
            time.sleep(2)
            st.rerun()
    
    return None

def process_video(video_path, target_lang, add_subs, sub_style, keep_audio, bitrate,
                  voice_mode="clone", preset_voice="female_american", 
                  separate_vocals=False, keep_background=True, bgm_volume=0.18):
    """Main video processing pipeline"""
    
    work_dir = st.session_state.work_dir
    
    def update_progress(stage):
        """Update progress and refresh display"""
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== Step 1: Extract audio ==========
        update_progress(1)
        with st.spinner("🎵 Extracting audio..."):
            extractor = AudioExtractor()
            audio_path = os.path.join(work_dir, "audio.mp3")
            
            result = extractor.extract_audio(video_path, audio_path)
            
            if result:
                st.session_state.audio_path = audio_path
                st.success("✅ Audio extraction complete")
            else:
                st.error("❌ Audio extraction failed")
                return
        
        # ========== Step 2: Speech recognition ==========
        update_progress(2)
        with st.spinner("🎤 Performing speech recognition..."):
            transcriber = Transcriber()
            transcript_path = os.path.join(work_dir, "transcript.json")
            
            success = transcriber.transcribe(audio_path, transcript_path)
            
            if success:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    st.session_state.transcript = json.load(f)
                st.success("✅ Speech recognition complete")
            else:
                st.error("❌ Speech recognition failed")
                return
        
        # ========== Step 3: Wait for transcript editing ==========
        update_progress(3)
        st.session_state.waiting_for_transcript_edit = True
        st.rerun()
        return  # Pause pipeline until user finishes editing
        
    except Exception as e:
        st.error(f"❌ An error occurred during processing: {str(e)}")
        import traceback
        with st.expander("Show detailed error information"):
            st.code(traceback.format_exc())


def continue_after_transcript_edit():
    """Continue processing after transcript editing"""
    work_dir = st.session_state.work_dir
    target_lang = st.session_state.target_lang
    
    def update_progress(stage):
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== Step 4: Translate text ==========
        update_progress(4)
        with st.spinner(f"🌍 Translating to {target_lang}..."):
            translator = Translator()
            translated_path = os.path.join(work_dir, "translated.json")
            
            # Use edited transcript if available
            if st.session_state.transcript_edited:
                input_path = os.path.join(work_dir, "edited_transcript.json")
            else:
                input_path = os.path.join(work_dir, "transcript.json")
            
            success = translator.translate(input_path, translated_path, target_lang)
            
            if success:
                with open(translated_path, 'r', encoding='utf-8') as f:
                    st.session_state.translation = json.load(f)
                st.success("✅ Translation complete")
            else:
                st.error("❌ Translation failed")
                return
        
        # ========== Step 5: Wait for translation editing ==========
        update_progress(5)
        st.session_state.waiting_for_translation_edit = True
        st.rerun()
        return  # Pause pipeline until user edits translation
        
    except Exception as e:
        st.error(f"❌ An error occurred during processing: {str(e)}")
        import traceback
        with st.expander("Show detailed error information"):
            st.code(traceback.format_exc())


def continue_after_translation_edit(video_path, add_subs, sub_style, keep_audio, bitrate,
                                   voice_mode, preset_voice, separate_vocals, keep_background, bgm_volume):
    """Continue processing after translation editing"""
    work_dir = st.session_state.work_dir
    target_lang = st.session_state.target_lang
    
    def update_progress(stage):
        st.session_state.processing_stage = stage
        if 'update_progress_display' in st.session_state:
            st.session_state.update_progress_display()
    
    try:
        # ========== Step 6: Generate audio ==========
        update_progress(6)
        with st.spinner("🔊 Generating new audio..."):
            tts = TTSGenerator()
            new_audio_path = os.path.join(work_dir, "translated_audio.mp3")
            
            # Use edited translation if available
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
                st.success("✅ Audio generation complete")
                
                # Preview generated audio
                with st.expander("🔊 Preview Translated Audio"):
                    st.audio(new_audio_path)
            else:
                st.error("❌ Audio generation failed")
                return
        
        # ========== Step 7: Compose final video ==========
        update_progress(7)
        with st.spinner("🎬 Composing final video..."):
            composer = VideoComposer()
            output_path = os.path.join(work_dir, "output_video.mp4")
            
            # Prepare subtitles if needed
            subtitle_path = None
            if add_subs:
                subtitle_path = os.path.join(work_dir, "subtitles.srt")
                composer.create_subtitles(final_translation_path, subtitle_path)
            
            # Compose video
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
                
                # Preload video into memory
                with open(output_path, "rb") as f:
                    st.session_state.output_video_data = f.read()
                
                st.success("✅ Video composition complete!")
                st.balloons()
                
                # Refresh to show results
                st.rerun()
            else:
                st.error("❌ Video composition failed")
                return
    
    except Exception as e:
        st.error(f"❌ An error occurred during processing: {str(e)}")
        import traceback
        with st.expander("Show detailed error information"):
            st.code(traceback.format_exc())


# Continue pipeline if user has already completed earlier steps
if __name__ == "__main__":
    # Check if we should continue from a mid-process state
    if (st.session_state.get('processing_stage', 0) >= 3 and 
        not st.session_state.get('waiting_for_transcript_edit', False) and
        not st.session_state.get('waiting_for_translation_edit', False) and
        not st.session_state.get('processing_complete', False)):
        
        if st.session_state.get('processing_stage', 0) == 4:
            continue_after_transcript_edit()
        elif st.session_state.get('processing_stage', 0) == 6:
            # Retrieve parameters from session state
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