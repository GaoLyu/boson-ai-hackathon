"""
Speech Recognition Module
Uses FunASR for speech-to-text transcription with timestamps
"""

import os
import json
import re


class Transcriber:
    """Speech recognizer"""
    
    def __init__(self):
        """Initialize the recognizer"""
        self.model = None
    
    def _load_model(self):
        """Lazy-load the ASR model"""
        if self.model is None:
            print("🔄 Loading FunASR model...")
            try:
                from funasr import AutoModel
                self.model = AutoModel(
                    model="paraformer-zh",
                    vad_model="fsmn-vad",
                    punc_model="ct-punc",
                    alignment_model="fa-zh",
                    disable_update=True
                )
                print("✅ Model loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load model: {e}")
                raise
    
    def transcribe(self, audio_path, output_json_path):
        """
        Perform speech recognition
        
        Args:
            audio_path: Path to the input audio file
            output_json_path: Path to save the output JSON file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return False
        
        try:
            # Load the model
            self._load_model()
            
            # Perform recognition
            print("🎤 Starting speech recognition...")
            res = self.model.generate(
                input=[audio_path],
                batch_size_s=300,
                return_raw_text=False,
                sentence_timestamp=True,
            )
            
            # Process results
            if isinstance(res, list) and len(res) > 0:
                result = res[0]
                
                # Case 1: sentence_info already provided
                if "sentence_info" in result:
                    print(f"✅ Detected {len(result['sentence_info'])} sentences")
                    
                    # Convert timestamps (milliseconds → seconds)
                    for sentence in result["sentence_info"]:
                        if "start" in sentence:
                            sentence["start"] = sentence["start"] / 1000
                        if "end" in sentence:
                            sentence["end"] = sentence["end"] / 1000
                
                # Case 2: need to manually construct sentence_info
                elif "timestamp" in result and "text" in result:
                    print("⚠️ Manually constructing sentence_info...")
                    result["sentence_info"] = self._build_sentence_info(
                        result["text"],
                        result["timestamp"]
                    )
                    print(f"✅ Constructed {len(result['sentence_info'])} sentences")
                
                else:
                    print("❌ Unable to extract sentence information")
                    return False
                
                # Save results
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
                
                print(f"💾 Transcription saved to: {output_json_path}")
                return True
            
            else:
                print("❌ Empty recognition result")
                return False
        
        except Exception as e:
            print(f"❌ Speech recognition failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _build_sentence_info(self, text, timestamps):
        """Manually construct sentence_info"""
        # Split sentences by punctuation marks
        sentences = re.split(r'([。！？.!?])', text)
        sentences = [s1 + s2 for s1, s2 in zip(sentences[0::2], sentences[1::2])]
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Build sentence_info
        sentence_info = []
        char_idx = 0
        
        for sentence in sentences:
            if not sentence:
                continue
            
            # Determine the character range of this sentence
            start_char = char_idx
            end_char = char_idx + len(sentence)
            
            # Get timestamps (milliseconds → seconds)
            if start_char < len(timestamps):
                start_time = timestamps[start_char][0] / 1000
            else:
                start_time = 0
            
            if end_char - 1 < len(timestamps):
                end_time = timestamps[end_char - 1][1] / 1000
            else:
                end_time = start_time + 1
            
            sentence_info.append({
                "text": sentence,
                "start": start_time,
                "end": end_time
            })
            
            char_idx = end_char
        
        return sentence_info