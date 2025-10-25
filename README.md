# 🌏 CrossLingual Video Voiceover

### 🎬 Transform videos across languages — while keeping the fun moments alive!

This project converts videos from one language (e.g. **Chinese**) into another (e.g. **English**) by combining speech understanding, translation, and expressive audio generation.  
Unlike typical translators, our system keeps the **tone, humor, and timing** consistent — so the translated video still *feels* like the original.

---

## 🧠 Overview

> 🎯 Goal: Turn Chinese videos into English while preserving humor, cultural flavor, and emotional pacing.

This project was built for the **Boson AI Hackathon 2025**, showcasing how multimodal AI models can recreate the same storytelling energy in another language — not just the same words.

---

## ⚙️ Pipeline

1. **🎧 Speech Transcription**
   - Extracts and timestamps speech from `.mp3` or `.mp4` files using **FunASR** or **Higgs Audio Understanding**.
   - Produces sentence-level transcripts with accurate timing.

2. **🈶 Humor-Preserving Translation**
   - Translates Chinese → English using **Qwen-32B**.
   - Keeps punchlines, idioms, and personality intact — not a literal translation, but a natural rewrite.

3. **🗣️ Voice Generation**
   - Uses **Higgs Audio Generation** to synthesize English speech that matches the rhythm, emotion, and tone of the original.
   - Timing is aligned with the transcript for smooth dubbing.

4. **🎞️ Video Reconstruction**
   - Combines the new English voice track and optional background music with the original video via **FFmpeg / MoviePy**.

---

## 💡 Key Features

| Feature | Description |
|----------|-------------|
| 🔊 **Speech-to-Speech Translation** | End-to-end multilingual dubbing pipeline |
| 😄 **Humor Retention** | Keeps jokes, timing, and emotional flow intact |
| ⏱️ **Time Alignment** | Generated audio matches original pacing |
| 🧠 **Multimodal AI** | Combines ASR, LLM translation, and TTS seamlessly |

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| **ASR (Speech Recognition)** | FunASR, Higgs Audio Understanding |
| **Translation** | Qwen-32B LLM |
| **Voice Generation** | Higgs Audio Generation |
| **Video Processing** | FFmpeg, MoviePy |
| **Environment** | Python 3.10+, Conda |

---

## 🚀 Quick Start

```bash
# 1️⃣ Clone the repo
git clone https://github.com/yourusername/crosslingual-video-voiceover.git
cd crosslingual-video-voiceover

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run the pipeline
python main.py --input input_video.mp4 --output output_video_en.mp4
