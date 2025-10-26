"""
翻译模块
使用 Boson AI API 将文本翻译成目标语言（增强版 - 支持风格分析和对比输出）
"""

import os
import json
import time
import re
from openai import OpenAI


class Translator:
    """文本翻译器 - 使用 Boson AI（增强版）"""
    
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
            
            print("=" * 80)
            print(f"🎬 Step 2: 文本翻译")
            print("=" * 80)
            print(f"✅ 加载 {total} 个句子")
            
            # 获取语言名称
            source_lang = "Chinese"  # 假设源语言是中文
            target_lang_name = self._get_language_name(target_lang)
            print(f"🌍 翻译方向: {source_lang} → {target_lang_name}")
            
            # ===== 步骤1: 分析内容风格 =====
            print("\n" + "=" * 80)
            print("🔍 步骤 1/3: 分析视频内容风格")
            print("=" * 80)
            style_info = self._analyze_content_style(sentences)
            
            # ===== 步骤2: 整段翻译 =====
            print("\n" + "=" * 80)
            print(f"📝 步骤 2/3: 整段翻译 ({source_lang} → {target_lang_name})")
            print("=" * 80)
            translations = self._translate_full_script(sentences, style_info, source_lang, target_lang_name)
            
            if not translations:
                print("❌ 翻译失败")
                return False
            
            # ===== 步骤2.5: 整体润色（可选 - 默认关闭）=====
            # 如果需要更自然的翻译，取消下面的注释
            # print("\n" + "=" * 80)
            # print("🎭 步骤 2.5/3: 整体润色（可选）")
            # print("=" * 80)
            # translations = self._refine_translation_globally(sentences, translations, style_info, target_lang_name)
            
            # ===== 步骤3: 输出翻译对比 =====
            print("\n" + "=" * 80)
            print("✏️  步骤 3/3: 翻译对比")
            print("=" * 80)
            
            # 显示详细的翻译对比
            print("\n翻译对比:")
            print("-" * 80)
            for i in range(min(len(sentences), len(translations))):
                orig = sentences[i].get("text", "")
                trans = translations[i]
                orig_words = len(orig)
                trans_words = len(trans.split())
                
                print(f"\n[{i+1}/{total}] 原文: {orig}")
                print(f"     译文: {trans}")
                print(f"     词数: 中文{orig_words}字 → 英文{trans_words}词")
            
            if len(sentences) > 5:
                print(f"\n... (仅显示前5句，共{total}句)")
            print("-" * 80)
            
            # 构建输出
            translated_sentences = []
            for i, s in enumerate(sentences):
                trans_text = translations[i] if i < len(translations) else ""
                
                # 根据目标语言决定字段名
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
            
            # 更新数据
            data[0]["sentence_info"] = translated_sentences
            
            # 保存结果
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 翻译完成，结果已保存至: {output_json_path}")
            print("=" * 80)
            return True
        
        except Exception as e:
            print(f"❌ 翻译失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _analyze_content_style(self, sentences):
        """分析视频内容风格"""
        # 抽样分析：取前5句和后2句
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
            print(f"\n📊 内容分析:\n{analysis}\n")
            return {"analysis": analysis}
        except Exception as e:
            print(f"⚠️ 分析失败: {e}")
            return {"analysis": "General video content."}
    
    def _translate_full_script(self, sentences, style_info, source_lang, target_lang):
        """整段翻译（保留时间戳结构）"""
        # 构建完整脚本
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
1. Translate naturally and fluently as if it were originally in {target_lang}.
2. Keep the same tone, humor, and emotional style.
3. Output numbered sentences exactly as in the input (1., 2., 3., ...).
4. Only return the translated lines — do not repeat the {source_lang} text.

Begin translation:"""
        
        try:
            print("\n🤖 正在翻译中...")
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
                # 去掉序号（支持 1. / 1) / 1、等）
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = self._clean_text(line)
                if line and len(line) > 1:
                    lines.append(line)
            
            print(f"✅ 成功翻译 {len(lines)} 句\n")
            
            # 显示翻译预览
            print("翻译预览:")
            print("-" * 80)
            for i in range(min(5, len(lines))):
                print(f"{i+1}. {lines[i]}")
            if len(lines) > 5:
                print(f"... (还有 {len(lines)-5} 句)")
            print("-" * 80)
            
            return lines
        except Exception as e:
            print(f"❌ 翻译失败: {e}")
            return []
    
    def _clean_text(self, text):
        """清理翻译文本"""
        # 移除中文字符
        text = re.sub(r'[\u4e00-\u9fff]+', '', text)
        # 移除中文标点
        text = re.sub(r'[，。！？、；：""''《》【】（）]', '', text)
        # 标准化空格
        text = ' '.join(text.split())
        return text.strip()
    
    def _refine_translation_globally(self, sentences, translations, style_info, target_lang):
        """整体润色（保持幽默与节奏感）- 可选功能"""
        print("\n🎭 正在进行整体润色（保持幽默与节奏感）...")
        
        style_context = style_info.get("analysis", "")
        
        # 构造中英对照文本
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
2. Preserve all jokes, humor, and comedic pacing.
3. Keep the meaning faithful to the original.
4. Keep the numbering (1., 2., 3., ...). One line per number.
5. Do NOT output the original text, only the improved {target_lang}.

CONTENT STYLE:
{style_context}

TRANSLATION DRAFT:
{paired_text}

Now rewrite the {target_lang} lines according to the above requirements.
Output format:
1. ...
2. ...
"""
        
        try:
            print("🤖 LLM 正在整体润色...")
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
                # 去掉序号
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = self._clean_text(line)
                if line:
                    refined_lines.append(line)
            
            print(f"✅ 成功整体优化 {len(refined_lines)} 句")
            print("润色预览:")
            print("-" * 80)
            for i in range(min(5, len(refined_lines))):
                print(f"{i+1}. {refined_lines[i]}")
            if len(refined_lines) > 5:
                print(f"... (还有 {len(refined_lines)-5} 句)")
            print("-" * 80)
            
            return refined_lines
        
        except Exception as e:
            print(f"⚠️ 整体润色失败: {e}")
            return translations
    
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