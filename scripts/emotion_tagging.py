"""
Emotion/Style Tagging Pipeline

Applies emotion and style recognition to audio segments using the official Sarvam AI SDK.
If classification fails, the emotion is set to null.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from sarvamai import SarvamAI

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()

# Allowed emotion labels
EMOTION_LABELS = [
    "neutral",
    "conversational",
    "formal",
    "excited",
    "sad",
    "angry"
]

def query_sarvam_llm(prompt):
    """Query Sarvam LLM for emotion classification using the official SDK."""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Warning: SARVAM_API_KEY is not set.")
        return None
        
    try:
        client = SarvamAI(api_subscription_key=api_key)
        response = client.chat.completions(
            messages=[{"role": "user", "content": prompt}],
            model="sarvam-m",
            temperature=0.1
        )
        
        content = ""
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
        elif isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
            
        if not content:
            return None
            
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content.strip())
    except Exception as e:
        print(f"Sarvam LLM API error: {e}")
        return None

class LLMEmotionTagger:
    """SDK-based classifier for speech emotion and style."""
    
    def predict(self, record):
        """
        Predict emotion for record using Sarvam LLM. Returns (emotion, confidence).
        If classification fails, returns (None, 0.0).
        """
        transcript = record.get("transcript", "")
        title = record.get("title", "")
        channel = record.get("channel", "")
        duration = record.get("duration", 0.0)
        
        if not transcript:
            return None, 1.0
            
        prompt = f"""You are an expert Speech Emotion and Style Classifier.
Classify the following speech segment transcript and metadata into exactly one of these allowed labels:
- neutral (standard speech without strong emotion)
- conversational (casual, friendly, relaxed conversation, e.g., podcasts)
- formal (lectures, news reporting, formal speeches, academic interviews)
- excited (high energy, enthusiastic, cheering, happy)
- sad (gloomy, sorrowful, crying)
- angry (annoyed, hostile, shouting, arguing)

Input:
Transcript: "{transcript}"
Video Title: "{title}"
Channel: "{channel}"
Duration: {duration} seconds

Return a JSON object with exactly these keys:
{{
  "emotion": "<one of the allowed labels listed above>",
  "confidence": <float between 0.0 and 1.0 representing classification confidence>
}}
"""
        res = query_sarvam_llm(prompt)
        if res and isinstance(res, dict) and "emotion" in res:
            emotion = res["emotion"].lower().strip()
            confidence = float(res.get("confidence", 0.80))
            if emotion in EMOTION_LABELS:
                return emotion, confidence
                
        # If classification fails, return None (null) and 0.0 confidence
        return None, 0.0

def tag_emotions(input_path=None, output_path=None):
    """
    Apply LLM emotion tagging to filtered segments.
    """
    if input_path is None:
        input_path = ROOT_DIR / "data" / "segments_metadata_filtered.jsonl"
    else:
        input_path = Path(input_path)
        
    if output_path is None:
        output_path = ROOT_DIR / "data" / "segments_metadata_emotions.jsonl"
    else:
        output_path = Path(output_path)
        
    records = []
    
    if not input_path.exists():
        print(f"Warning: Filtered metadata file not found at: {input_path}")
        print("Using segments_metadata.jsonl instead...")
        input_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
        
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    total = len(records)
    if total == 0:
        print("No records found to process.")
        return
        
    tagger = LLMEmotionTagger()
    
    print(f"\n=== Emotion Tagging (Sarvam SDK LLM) ===")
    print(f"Processing {total} segments...")
    
    emotion_counts = {}
    for idx, record in enumerate(records, start=1):
        try:
            emotion, confidence = tagger.predict(record)
            
            record["emotion"] = emotion
            record["emotion_confidence"] = float(confidence)
            
            emotion_key = emotion if emotion is not None else "null"
            emotion_counts[emotion_key] = emotion_counts.get(emotion_key, 0) + 1
            
            if idx % 10 == 0 or idx == 1:
                print(f"[{idx}/{total}] Tagged: '{record.get('transcript', '')[:30]}' -> {emotion_key} ({confidence:.2f})")
                
        except Exception as e:
            print(f"Error processing segment {idx}: {e}")
            record["emotion"] = None
            record["emotion_confidence"] = 0.0
            emotion_counts["null"] = emotion_counts.get("null", 0) + 1
            
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n=== Emotion Tagging Summary ===")
    print(f"Total segments tagged: {total}")
    print("\nEmotion Distribution:")
    for emotion in EMOTION_LABELS + ["null"]:
        count = emotion_counts.get(emotion, 0)
        percentage = 100 * count / total if total > 0 else 0.0
        print(f"  {emotion:15s}: {count:4d} ({percentage:5.1f}%)")
        
    print(f"\nSaved to: {output_path}")

def main():
    tag_emotions()

# if __name__ == "__main__":
#     main()
