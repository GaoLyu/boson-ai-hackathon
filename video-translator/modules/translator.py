"""
翻译模块
使用 Boson AI API 将文本翻译成目标语言
"""

import os
import json
import time
import re
from openai import OpenAI


class Translator:
    """文本翻译器 - 使用 Boson AI"""
    
    def __init__(self, api_key=None, api_base=None, model=None):
        """
        初始化翻译器
        
        Args:
            api_key: API密钥
            api_base: API基础URL
            model: 模型名称
        """
        self.api_key = api_key or os.getenv("BOSON_API_KEY", "bai-C8daJQcbo2sMbwgr9aTNmCZM4C1zliRyWLPNA3cRGGksCagH")
        self.api_base = api_base or "https://hackathon.boson.ai/v1"
        self.model = model or "Qwen3-32B-non-thinking-Hackathon"
        self.client = None
    
    def _init_client(self):
        """初始化API客户端"""
        if self.client is not None:
            return
        
        print(f"🔄 初始化 Boson AI 客户端...")
        
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            print("✅ 客户端初始化完成")
        
        except Exception as e:
            print(f"❌ 客户端初始化失败: {e}")
            raise
    
    def translate(self, input_json_path, output_json_path, target_lang="en"):
        """
        翻译JSON文件中的所有句子
        
        Args:
            input_json_path: 输入JSON文件路径
            output_json_path: 输出JSON文件路径
            target_lang: 目标语言代码
        
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(input_json_path):
            print(f"❌ 输入文件不存在: {input_json_path}")
            return False
        
        try:
            # 初始化客户端
            self._init_client()
            
            # 读取输入文件
            with open(input_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list) or len(data) == 0:
                print("❌ 无效的JSON格式")
                return False
            
            result = data[0]
            sentences = result.get("sentence_info", [])
            total = len(sentences)
            
            print(f"🌍 开始翻译 {total} 个句子...")
            
            # 第一步：分析内容风格
            style_info = self._analyze_content_style(sentences, target_lang)
            
            # 第二步：整段翻译
            translations = self._translate_full_script(sentences, style_info, target_lang)
            
            if not translations:
                print("❌ 翻译失败")
                return False
            
            # 第三步：长度调整
            adjusted = self._adjust_by_length(sentences, translations, target_lang)
            
            # 构建输出
            translated_sentences = []
            for i, s in enumerate(sentences):
                trans_text = adjusted[i] if i < len(adjusted) else ""
                translated_sentences.append({
                    "text": s.get("text", ""),
                    "text_en" if target_lang == "en" else "text_translated": trans_text,
                    "start": s.get("start", 0),
                    "end": s.get("end", 0)
                })
            
            # 更新数据
            data[0]["sentence_info"] = translated_sentences
            
            # 保存结果
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 已保存: {output_json_path}")
            return True
        
        except Exception as e:
            print(f"❌ 翻译失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _analyze_content_style(self, sentences, target_lang):
        """分析视频内容风格"""
        print("\n🔍 分析内容风格...")
        
        # 抽样分析
        sample_texts = [s.get("text", "").strip() for s in sentences[:5]]
        sample_texts += [s.get("text", "").strip() for s in sentences[-2:]]
        sample = "\n".join([f"{i+1}. {t}" for i, t in enumerate(sample_texts) if t])
        
        lang_name = self._get_language_name(target_lang)
        
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
            print(f"📊 分析结果: {analysis[:100]}...")
            return {"analysis": analysis}
        except Exception as e:
            print(f"⚠️ 分析失败: {e}")
            return {"analysis": "General video content."}
    
    def _translate_full_script(self, sentences, style_info, target_lang):
        """整段翻译"""
        print(f"\n📝 正在翻译全文...")
        
        full_script = []
        for i, s in enumerate(sentences):
            text = s.get("text", "").strip()
            if text:
                full_script.append(f"{i+1}. {text}")
        script_text = "\n".join(full_script)
        
        style_context = style_info.get("analysis", "")
        lang_name = self._get_language_name(target_lang)
        
        prompt = f"""You are translating a video transcript to {lang_name}.

CONTENT ANALYSIS:
{style_context}

FULL TRANSCRIPT:
{script_text}

TRANSLATION REQUIREMENTS:
1. Translate naturally and fluently as if it were originally in {lang_name}.
2. Keep the same tone, humor, and emotional style.
3. Output numbered sentences exactly as in the input (1., 2., 3., ...).
4. Only return the translated lines — do not repeat the original text.

Begin translation:"""
        
        try:
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
                # 去掉序号
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = self._clean_text(line)
                if line and len(line) > 1:
                    lines.append(line)
            
            print(f"✅ 成功翻译 {len(lines)} 句")
            return lines
        except Exception as e:
            print(f"❌ 翻译失败: {e}")
            return []
    
    def _adjust_by_length(self, sentences, translations, target_lang):
        """调整翻译长度"""
        print(f"\n✏️  调整翻译长度...")
        
        adjusted = []
        lang_name = self._get_language_name(target_lang)
        
        for i, sent in enumerate(sentences):
            if i >= len(translations):
                continue
            
            text_orig = sent.get("text", "")
            text_trans = translations[i]
            
            target_words = max(3, len(text_orig) // 3)
            current_words = len(text_trans.split())
            
            print(f"  [{i+1}/{len(sentences)}] 词数: {current_words} → 目标: {target_words}", end="\r")
            
            if abs(current_words - target_words) <= 3:
                adjusted_text = text_trans
            else:
                try:
                    prompt = f"""Adjust this {lang_name} sentence so that its length (word count) is close to {target_words} words.
Keep the same meaning, tone, and fluency.
Sentence: "{text_trans}"
Output only the adjusted sentence."""
                    
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"You are a fluent {lang_name} editor."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.4,
                        max_tokens=100
                    )
                    adjusted_text = self._clean_text(response.choices[0].message.content.strip())
                    if not adjusted_text:
                        adjusted_text = text_trans
                except Exception as e:
                    adjusted_text = text_trans
                
                time.sleep(0.2)
            
            adjusted.append(adjusted_text)
        
        print(f"\n✅ 长度调整完成")
        return adjusted
    
    def _clean_text(self, text):
        """清理翻译文本"""
        # 移除中文字符
        text = re.sub(r'[\u4e00-\u9fff]+', '', text)
        # 移除中文标点
        text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
        # 清理空格
        text = ' '.join(text.split())
        return text.strip()
    
    def _get_language_name(self, lang_code):
        """获取语言名称"""
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