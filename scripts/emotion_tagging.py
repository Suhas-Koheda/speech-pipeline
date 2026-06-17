"""
Emotion/Style Tagging Pipeline

Applies emotion and style recognition to audio segments using an LLM-based classifier
over transcripts and audio metadata, falling back to a rule-based heuristic classifier.

Allowed labels:
- neutral
- conversational
- formal
- excited
- happy
- sad
- angry
- questioning
- serious
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Allowed emotion labels
EMOTION_LABELS = [
    "neutral",
    "conversational",
    "formal",
    "excited",
    "happy",
    "sad",
    "angry",
    "questioning",
    "serious"
]


def query_groq(prompt):
    """Query Groq API for emotion classification."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-specdec",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        print(f"Groq API error: {e}")
        return None


def query_gemini(prompt):
    """Query Gemini API for emotion classification."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None


def query_sarvam(prompt):
    """Query Sarvam LLM API for emotion classification."""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return None
    url = "https://api.sarvam.ai/chat/completions"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "model": "sarvam-2b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
    except Exception as e:
        print(f"Sarvam LLM API error: {e}")
        return None


def heuristic_classify(transcript, title, channel, duration):
    """
    Fallback heuristic classifier based on transcript keywords and metadata.
    """
    text = transcript.lower().strip()
    title_lower = title.lower()
    channel_lower = channel.lower()
    
    # 1. Questioning
    if text.endswith("?") or any(w in text for w in ["ఏంటి", "ఎందుకు", "ఎలా", "ఎవరు", "ఎప్పుడు", "ఏది", "what", "why", "how", "who", "when", "which", "where"]):
        return "questioning", 0.85
        
    # 2. Angry
    if text.endswith("!") or "!!" in text or any(w in text for w in ["శాపం", "కోపం", "అన్యాయం", "shout", "fight", "angry", "kill", "hate"]):
        return "angry", 0.75
        
    # 3. Excited
    if any(w in text for w in ["అద్భుతం", "సూపర్", "ఆనందం", "happy", "excited", "wow", "great", "awesome", "love", "smile"]):
        return "excited", 0.80
        
    # 4. Sad
    if any(w in text for w in ["బాధ", "కన్నీళ్లు", "సంతాపం", "sad", "cry", "loss", "sorry", "death", "die"]):
        return "sad", 0.80
        
    # 5. Conversational
    if any(w in channel_lower or w in title_lower for w in ["podcast", "raw talks", "interview", "conversation", "chat", "vlog"]):
        return "conversational", 0.85
        
    # 6. Formal
    if any(w in channel_lower or w in title_lower for w in ["news", "tv", "press", "speech", "lecture", "formal", "academic", "analysis"]):
        return "formal", 0.85
        
    # Default fallback
    return "neutral", 0.70


class LLMEmotionTagger:
    """LLM-based classifier for speech emotion and style."""
    
    def predict(self, record):
        """
        Predict emotion for record using LLM or heuristic fallback.
        """
        transcript = record.get("transcript", "")
        title = record.get("title", "")
        channel = record.get("channel", "")
        duration = record.get("duration", 0.0)
        
        if not transcript:
            return "neutral", 1.0
            
        prompt = f"""You are an expert Speech Emotion and Style Classifier.
Classify the following speech segment transcript and metadata into exactly one of these allowed labels:
- neutral (standard speech without strong emotion)
- conversational (casual, friendly, relaxed conversation, e.g., podcasts)
- formal (lectures, news reporting, formal speeches, academic interviews)
- excited (high energy, enthusiastic, cheering)
- happy (joyful, cheerful, laughing)
- sad (gloomy, sorrowful, crying)
- angry (annoyed, hostile, shouting, arguing)
- questioning (asking a query, curious tone, asking questions)
- serious (grave, solemn, concerned, warning)

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
        # Try Gemini
        res = query_gemini(prompt)
        if res and isinstance(res, dict) and "emotion" in res:
            emotion = res["emotion"].lower().strip()
            confidence = float(res.get("confidence", 0.90))
            if emotion in EMOTION_LABELS:
                return emotion, confidence
                
        # Try Groq
        res = query_groq(prompt)
        if res and isinstance(res, dict) and "emotion" in res:
            emotion = res["emotion"].lower().strip()
            confidence = float(res.get("confidence", 0.85))
            if emotion in EMOTION_LABELS:
                return emotion, confidence
                
        # Try Sarvam
        res = query_sarvam(prompt)
        if res and isinstance(res, dict) and "emotion" in res:
            emotion = res["emotion"].lower().strip()
            confidence = float(res.get("confidence", 0.80))
            if emotion in EMOTION_LABELS:
                return emotion, confidence
                
        # Fallback to heuristic
        return heuristic_classify(transcript, title, channel, duration)


def tag_emotions(
    input_path="../data/segments_metadata_filtered.jsonl",
    output_path="../data/segments_metadata_emotions.jsonl",
):
    """
    Apply LLM emotion tagging to filtered segments.
    """
    records = []
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        print("Using segments_metadata.jsonl instead...")
        input_path = "../data/segments_metadata.jsonl"
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    
    total = len(records)
    
    if total == 0:
        print("No records found!")
        return
    
    # Initialize tagger
    tagger = LLMEmotionTagger()
    
    print(f"\n=== Emotion Tagging (LLM-based) ===")
    print(f"Processing {total} segments...")
    
    emotion_counts = {}
    for idx, record in enumerate(records, start=1):
        try:
            emotion, confidence = tagger.predict(record)
            
            record["emotion"] = emotion
            record["emotion_confidence"] = float(confidence)
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            if idx % 20 == 0 or idx == 1:
                print(f"[{idx}/{total}] Tagged: '{record.get('transcript', '')[:30]}' -> {emotion} ({confidence:.2f})")
                
        except Exception as e:
            print(f"Error processing segment {idx}: {e}")
            record["emotion"] = "neutral"
            record["emotion_confidence"] = 0.5
            emotion_counts["neutral"] = emotion_counts.get("neutral", 0) + 1
            
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n=== Emotion Tagging Summary ===")
    print(f"Total segments tagged: {total}")
    print("\nEmotion Distribution:")
    for emotion in EMOTION_LABELS:
        count = emotion_counts.get(emotion, 0)
        percentage = 100 * count / total if total > 0 else 0.0
        print(f"  {emotion:15s}: {count:4d} ({percentage:5.1f}%)")
        
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    tag_emotions()
