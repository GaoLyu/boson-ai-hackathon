# 🎬 Video Language Translator

**Transform any video into another language — while preserving the speaker’s tone, emotion, and background ambiance.**  
This Streamlit web app performs end-to-end video translation with editable transcripts, AI-generated speech, and automatic subtitle rendering.

---

## 🚀 Overview

The **Video Language Translator** automatically:
1. **Extracts audio** from a video.  
2. **Transcribes speech** using ASR (FunASR).  
3. **Translates** the transcript into a chosen language.  
4. **Generates new speech audio** in the target language — using **voice cloning** or **preset voices**  via **Boson AI**.  
5. **Re-composes the video**, aligning the new audio track and optional subtitles with the original visuals.  

You can preview, edit, and re-run each step interactively — no coding required.

---

## ✨ Key Features

| Feature | Description |
|----------|-------------|
| 🎥 **Multi-language translation** | Translate videos into English, Chinese, Japanese, Korean, French, German, Spanish, Russian, Arabic, or Hindi. |
| 🎙️ **Automatic speech recognition (ASR)** | Uses FunASR for accurate transcription with timestamps. |
| 🌐 **AI-powered translation** | Employs Boson AI’s large model to retain tone, humor, and style. |
| 🗣️ **Voice cloning or presets** | Clone the original speaker’s voice or select from preset natural voices. |
| 🎵 **Smart audio processing** | Separates vocals and background, adjusts mix and bitrate automatically. |
| ✏️ **Interactive editing** | Edit transcripts and translations before generating final audio. |
| 💬 **Subtitle generation** | Automatically creates and burns SRT subtitles (default / yellow / blurred bar). |
| 📀 **Final video composition** | Merges everything with adaptive subtitle styling and synchronized timing. |

---

## 🧩 Module Structure

| File | Purpose |
|------|----------|
| `app.py` | Streamlit front-end app orchestrating the full translation pipeline. |
| `audio_extractor.py` | Extracts audio tracks from uploaded videos using MoviePy or FFmpeg. |
| `transcriber.py` | Performs speech-to-text transcription using FunASR models. |
| `translator.py` | Translates recognized text via Boson AI with context-aware style analysis. |
| `tts_generator.py` | Generates translated speech via Boson AI’s TTS, supports cloning and preset voices. |
| `video_composer.py` | Merges new audio, subtitles, and video; supports multiple subtitle styles. |
| `__init__.py` | Makes the above modules importable as a unified package. |

---

## 🧠 Architecture

```text
Video Input
   ↓
AudioExtractor  →  Transcriber (ASR)  →  Translator (Boson AI)
   ↓                                        ↓
Original Audio                        Translated Text
   ↓                                        ↓
   └────>  TTSGenerator (Voice clone / preset)  →  Translated Audio
                                                ↓
                                          VideoComposer  →  Final Video (MP4)
```

---

## 🖥️ How to Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/video-translator.git
cd video-translator
```

### 2. Install Dependencies
You’ll need Python 3.9+ and FFmpeg.

```bash
pip install -r requirements.txt
```

Make sure these are installed:
```bash
pip install streamlit moviepy funasr demucs openai
brew install ffmpeg   # or apt install ffmpeg
```

### 3. Set Your Boson API Key
```bash
export BOSON_API_KEY="your-api-key"
```

### 4. Run the Streamlit App
```bash
streamlit run app.py
```

The app will open automatically at:  
👉 http://localhost:8501

---

## 🧭 How to Use the App

1. **Upload your video** (MP4, MOV, MKV, AVI).  
2. **Select target language** in the sidebar.  
3. *(Optional)* Adjust advanced options (voice type, background music, subtitles, etc.).  
4. Click **Start Translation**.  
5. Review and **edit the transcript** if needed.  
6. Review and **edit the translation** for accuracy or tone.  
7. Wait for the system to generate new audio and compose the final video.  
8. **Preview and download** your translated video.  

---

## 🧪 Example Workflow

- Input: `chinese_vlog.mp4`  
- Target Language: **English**  
- Mode: **Voice Cloning**  
- Subtitles: **Blurred bar style**  

Output:
- `output_video.mp4` — video dubbed in English with original voice style and subtitles.  
- `subtitles.srt` — synchronized translated captions.  

---

## ⚙️ Technical Requirements

- Python 3.9+
- FFmpeg (for audio/video operations)
- GPU recommended for faster TTS and ASR
- Internet connection (for Boson AI API access)

---

## 📄 License
MIT License © 2025 — Built for the Boson Hackathon.

---

## ❤️ Credits
Powered by **Boson AI**, **FunASR**, **Demucs**, and **FFmpeg**.
