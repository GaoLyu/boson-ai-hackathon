"""
Translation Module
Uses the Boson AI API to translate text into a target language
(Enhanced Version – includes style analysis and comparative output)
"""

import os
import json
import time
import re
from openai import OpenAI


class Translator:
    """Text Translator using Boson AI (Enhanced Version)"""
    
    def __init__(self, api_key=None, api_base=None, model=None):
        """
        Initialize the translator
        
        Args:
            api_key: API key
            api_base: Base URL for the API
            model: Model name
        """
        self.api_key = api_key or os.getenv("BOSON_API_KEY", "bai-4RckqUuoLpgxtUFcgT4fMwHQddd-dR0_AZOxII6UOZhPmR1s")
        self.api_base = api_base or "https://hackathon.boson.ai/v1"
        self.model = model or "Qwen3-32B-non-thinking-Hackathon"
        self.client = None
    
    def _init_client(self):
        """Initialize the API client"""
        if self.client is not None:
            return
        
        print(f"🔄 Initializing Boson AI client...")
        
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            print("✅ Client initialized successfully")
        
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            raise
    
    def translate(self, input_json_path, output_json_path, target_lang="en"):
        """
        Translate all sentences in a JSON file
        
        Args:
            input_json_path: Path to the input JSON file
            output_json_path: Path to save the output JSON file
            target_lang: Target language code
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(input_json_path):
            print(f"❌ Input file not found: {input_json_path}")
            return False
        
        try:
            # Initialize client
            self._init_client()
            
            # Load input file
            with open(input_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list) or len(data) == 0:
                print("❌ Invalid JSON format")
                return False
            
            result = data[0]
            sentences = result.get("sentence_info", [])
            total = len(sentences)
            
            print("=" * 80)
            print(f"🎬 Step 2: Text Translation")
            print("=" * 80)
            print(f"✅ Loaded {total} sentences")
            
            # Source and target languages
            source_lang = "Chinese"  # Assume source is Chinese
            target_lang_name = self._get_language_name(target_lang)
            print(f"🌍 Translation direction: {source_lang} → {target_lang_name}")
            
            # ===== Step 1: Analyze content style =====
            print("\n" + "=" * 80)
            print("🔍 Step 1/3: Analyzing content style")
            print("=" * 80)
            style_info = self._analyze_content_style(sentences)
            
            # ===== Step 2: Full translation =====
            print("\n" + "=" * 80)
            print(f"📝 Step 2/3: Translating ({source_lang} → {target_lang_name})")
            print("=" * 80)
            translations = self._translate_full_script(sentences, style_info, source_lang, target_lang_name)
            
            if not translations:
                print("❌ Translation failed")
                return False
            
            # ===== Step 2.5: Global refinement (optional, disabled by default) =====
            # Uncomment the section below to enable natural translation polishing
            # print("\n" + "=" * 80)
            # print("🎭 Step 2.5/3: Global refinement (optional)")
            # print("=" * 80)
            # translations = self._refine_translation_globally(sentences, translations, style_info, target_lang_name)
            
            # ===== Step 3: Output comparison =====
            print("\n" + "=" * 80)
            print("✏️ Step 3/3: Translation Comparison")
            print("=" * 80)
            
            print("\nTranslation Comparison:")
            print("-" * 80)
            for i in range(min(len(sentences), len(translations))):
                orig = sentences[i].get("text", "")
                trans = translations[i]
                orig_words = len(orig)
                trans_words = len(trans.split())
                
                print(f"\n[{i+1}/{total}] Original: {orig}")
                print(f"     Translation: {trans}")
                print(f"     Word count: CN {orig_words} chars → {target_lang_name} {trans_words} words")
            
            if len(sentences) > 5:
                print(f"\n... (showing first 5 out of {total} sentences)")
            print("-" * 80)
            
            # Build output
            translated_sentences = []
            for i, s in enumerate(sentences):
                trans_text = translations[i] if i < len(translations) else ""
                
                # Determine field name by target language
                if target_lang == "en":
                    field_name = "text_en"
                else:
                    field_name = "text_translated"
                
                translated_sentences.append({
                    "text": s.get("text", ""),
                    field_name: trans_text,
                    "start": s.get("start", 0),
                    "end": s.get("end", 0)
                })
            
            # Update and save data
            data[0]["sentence_info"] = translated_sentences
            
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Translation complete! Saved to: {output_json_path}")
            print("=" * 80)
            return True
        
        except Exception as e:
            print(f"❌ Translation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _analyze_content_style(self, sentences):
        """Analyze the overall tone and style of the video"""
        # Sample first 5 and last 2 lines
        sample_texts = [s.get("text", "").strip() for s in sentences[:5]]
        sample_texts += [s.get("text", "").strip() for s in sentences[-2:]]
        sample = "\n".join([f"{i+1}. {t}" for i, t in enumerate(sample_texts) if t])
        
        prompt = f"""Analyze this video transcript sample and identify:

SAMPLE TEXT:
{sample}

Provide a brief analysis (2-3 sentences):
1. Content type (e.g. comedy, educational, narrative, etc.)
2. Tone and style (formal, casual, humorous, etc.)
3. Any special traits (wordplay, technical terms, etc.)

Keep it concise:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a content analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            analysis = response.choices[0].message.content.strip()
            print(f"\n📊 Content Analysis:\n{analysis}\n")
            return {"analysis": analysis}
        except Exception as e:
            print(f"⚠️ Analysis failed: {e}")
            return {"analysis": "General video content."}
    
    def _translate_full_script(self, sentences, style_info, source_lang, target_lang):
        """Translate the entire transcript while keeping timestamp structure"""
        # Combine full script
        full_script = []
        for i, s in enumerate(sentences):
            text = s.get("text", "").strip()
            if text:
                full_script.append(f"{i+1}. {text}")
        script_text = "\n".join(full_script)
        
        style_context = style_info.get("analysis", "")
        
        prompt = f"""You are translating a video transcript from {source_lang} to {target_lang}.

CONTENT ANALYSIS:
{style_context}

FULL TRANSCRIPT:
{script_text}

TRANSLATION REQUIREMENTS:
1. Translate naturally and fluently as if originally written in {target_lang}.
2. Keep the same tone, humor, and emotion.
3. Output numbered sentences exactly as in the input (1., 2., 3., ...).
4. Only return the translated lines — do not repeat the {source_lang} text.

Begin translation:"""
        
        try:
            print("\n🤖 Translating...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator for video subtitles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            translation = response.choices[0].message.content.strip()
            lines = []
            for line in translation.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Remove numbering (supports 1., 1), 1、 etc.)
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = self._clean_text(line)
                if line and len(line) > 1:
                    lines.append(line)
            
            print(f"✅ Successfully translated {len(lines)} sentences\n")
            
            # Preview translation
            print("Translation Preview:")
            print("-" * 80)
            for i in range(min(5, len(lines))):
                print(f"{i+1}. {lines[i]}")
            if len(lines) > 5:
                print(f"... ({len(lines)-5} more)")
            print("-" * 80)
            
            return lines
        except Exception as e:
            print(f"❌ Translation failed: {e}")
            return []
    
    def _clean_text(self, text):
        """Clean translation text"""
        # Remove Chinese characters
        text = re.sub(r'[\u4e00-\u9fff]+', '', text)
        # Remove Chinese punctuation
        text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
        # Normalize spaces
        text = ' '.join(text.split())
        return text.strip()
    
    def _refine_translation_globally(self, sentences, translations, style_info, target_lang):
        """Globally polish translation (preserving humor and rhythm) — optional"""
        print("\n🎭 Performing global refinement (keeping humor and rhythm)...")
        
        style_context = style_info.get("analysis", "")
        
        # Create bilingual comparison text
        paired_lines = []
        for i, s in enumerate(sentences):
            orig = s.get("text", "").strip()
            trans = translations[i] if i < len(translations) else ""
            if orig and trans:
                paired_lines.append(f"{i+1}. {orig}\n→ {trans}")
        paired_text = "\n".join(paired_lines)
        
        prompt = f"""
You are a bilingual humor script editor.
Below is a bilingual translation of a video narration.

Your task:
1. Polish the {target_lang} translation as a whole so it reads naturally, witty, and rhythmic.
2. Preserve all jokes, humor, and comedic timing.
3. Keep the meaning faithful to the original.
4. Keep numbering (1., 2., 3., ...). One line per number.
5. Do NOT output the original text, only the improved and refined {target_lang}.

CONTENT STYLE:
{style_context}

TRANSLATION DRAFT:
{paired_text}

Now rewrite the {target_lang} lines according to these rules.
Output format:
1. ...
2. ...
"""
        
        try:
            print("🤖 LLM performing global refinement...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a witty, natural-sounding {target_lang} script editor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )
            
            refined_text = response.choices[0].message.content.strip()
            refined_lines = []
            for line in refined_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Remove numbering
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = self._clean_text(line)
                if line:
                    refined_lines.append(line)
            
            print(f"✅ Globally refined {len(refined_lines)} sentences")
            print("Refinement Preview:")
            print("-" * 80)
            for i in range(min(5, len(refined_lines))):
                print(f"{i+1}. {refined_lines[i]}")
            if len(refined_lines) > 5:
                print(f"... ({len(refined_lines)-5} more)")
            print("-" * 80)
            
            return refined_lines
        
        except Exception as e:
            print(f"⚠️ Global refinement failed: {e}")
            return translations
    
    def _get_language_name(self, lang_code):
        """Get readable language name from code"""
        language_names = {
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
            "ar": "Arabic",
            "hi": "Hindi"
        }
        return language_names.get(lang_code, "English")