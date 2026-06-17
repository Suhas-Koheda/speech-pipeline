"""
Transcript Normalization & Emotion/Style Tagging Stage.

Performs Telugu-to-English code-mixed transcript normalization and speaking style
classification in a single, parallelized, optimized Sarvam LLM call (sarvam-30b)
to minimize latency and credit consumption.
"""

import os
import sys
import time
import json
import threading
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from sarvamai import SarvamAI

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()

# Valid style / emotion labels for TTS training annotation
VALID_EMOTIONS = {
    "neutral", "conversational", "formal", "excited", "enthusiastic",
    "happy", "humorous", "storytelling", "informative", "educational",
    "interview", "discussion", "debate", "questioning", "persuasive",
    "motivational", "inspirational", "serious", "analytical", "reflective",
    "emotional", "sad", "angry"
}

class ProgressTracker:
    """Thread-safe progress tracking and reporting."""
    def __init__(self, total):
        self.total = total
        self.lock = threading.Lock()
        self.completed = 0
        self.total_latency = 0.0
        self.successful = 0
        self.failed = 0
        self.retries = 0

    def record_success(self, duration, style, retries_cnt):
        with self.lock:
            self.completed += 1
            self.successful += 1
            self.total_latency += duration
            self.retries += retries_cnt
            avg_time = self.total_latency / self.completed if self.completed > 0 else 0.0
            # Print in the exact requested format:
            # [32/190]
            # style=discussion
            # time=1.8s
            # avg=2.1s/request
            print(f"[{self.completed}/{self.total}]")
            print(f"style={style}")
            print(f"time={duration:.1f}s")
            print(f"avg={avg_time:.1f}s/request")
            sys.stdout.flush()

    def record_failure(self, duration, retries_cnt):
        with self.lock:
            self.completed += 1
            self.failed += 1
            self.total_latency += duration
            self.retries += retries_cnt
            avg_time = self.total_latency / self.completed if self.completed > 0 else 0.0
            print(f"[{self.completed}/{self.total}]")
            print("style=failed")
            print(f"time={duration:.1f}s")
            print(f"avg={avg_time:.1f}s/request")
            sys.stdout.flush()

def normalize_and_tag_with_retry(text):
    """
    Query Sarvam-30b model to perform normalization and emotion/style tagging in a single call.
    Uses exponential backoff for retries on 429, 500, 503, and timeouts.
    Returns (normalized_transcript, style, confidence, was_normalized, retries_used, duration, success).
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Warning: SARVAM_API_KEY is not set.")
        return text, "neutral", 1.0, False, 0, 0.0, False
        
    client = SarvamAI(api_subscription_key=api_key)
    
    prompt = f"""You are an expert speech dataset annotator.

Your task is to:
1. Normalize Telugu-English code-mixed transcripts.
2. Classify speaking style and emotion.

Rules:

Transcript normalization:
* Keep Telugu words in Telugu script.
* Convert English words written in Telugu script back to English.
* Preserve meaning exactly.
* Do not translate Telugu.
* Do not rewrite content.
* Return the cleaned transcript.

Emotion/style classification:
Choose exactly one label from:
- neutral
- conversational
- formal
- excited
- enthusiastic
- happy
- humorous
- storytelling
- informative
- educational
- interview
- discussion
- debate
- questioning
- persuasive
- motivational
- inspirational
- serious
- analytical
- reflective
- emotional
- sad
- angry

Guidelines:
* Podcasts -> conversational, discussion, interview
* News -> informative, formal
* Lectures -> educational, informative
* Personal experiences -> storytelling, reflective
* Technical explanations -> analytical
* Motivational talks -> motivational, inspirational
* Strong positive energy -> enthusiastic or excited
* Arguments -> debate or angry
* Questions directed to audience -> questioning

Return ONLY valid JSON:
{{
  "normalized_transcript": "normalized transcript text",
  "emotion": "chosen_label",
  "emotion_confidence": 0.95
}}

Input:
ఐ విల్ టెల్ యు కేరళ ఇస్ హావింగ్ 20 సీట్స్
Output:
{{"normalized_transcript": "I will tell you Kerala is having 20 seats", "emotion": "conversational", "emotion_confidence": 0.95}}

Input:
ఈ model చాలా powerful గా ఉంది
Output:
{{"normalized_transcript": "ఈ model చాలా powerful గా ఉంది", "emotion": "informative", "emotion_confidence": 0.90}}

Input:
{text}
Output:"""

    backoffs = [1.0, 2.0, 4.0]
    retries_used = 0
    start_time = time.time()
    
    for attempt in range(4):  # attempt 0 is initial try, 1-3 are retries
        try:
            # Explicitly disable reasoning as requested: reasoning_effort=None
            response = client.chat.completions(
                model="sarvam-30b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150,
                reasoning_effort=None
            )
            
            content = ""
            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content
            elif isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            data = json.loads(content.strip())
            norm_text = data.get("normalized_transcript", text)
            emotion = data.get("emotion", "neutral")
            confidence = float(data.get("emotion_confidence", 1.0))
            
            if emotion not in VALID_EMOTIONS:
                emotion = "neutral"
                
            was_normalized = (norm_text.strip() != text.strip())
            duration = time.time() - start_time
            return norm_text, emotion, confidence, was_normalized, retries_used, duration, True
            
        except Exception as e:
            err_str = str(e).lower()
            # Check for retryable conditions
            is_retryable = any(status in err_str for status in ["429", "500", "503", "rate limit", "timeout", "busy", "remote"]) or "timeout" in err_str
            
            if is_retryable and attempt < 3:
                sleep_time = backoffs[attempt]
                retries_used += 1
                time.sleep(sleep_time)
            else:
                duration = time.time() - start_time
                return text, "neutral", 1.0, False, retries_used, duration, False

def process_record_task(record, idx, tracker):
    """Worker task that processes a single segment record."""
    transcript = record.get("transcript", "")
    norm_text, emotion, confidence, was_normalized, retries_used, duration, success = normalize_and_tag_with_retry(transcript)
    
    if success:
        tracker.record_success(duration, emotion, retries_used)
    else:
        tracker.record_failure(duration, retries_used)
        
    # Store formats requested:
    # 1. raw_transcript, transcript, style, style_confidence
    # 2. emotion, emotion_confidence, was_normalized, normalized
    record["raw_transcript"] = record.get("raw_transcript", transcript)
    record["transcript"] = norm_text
    record["style"] = emotion
    record["style_confidence"] = confidence
    record["emotion"] = emotion
    record["emotion_confidence"] = confidence
    record["normalized_transcript"] = norm_text
    record["was_normalized"] = was_normalized
    record["normalized"] = True
    
    return record

def main():
    global_start = time.time()
    
    input_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
    output_path = ROOT_DIR / "data" / "segments_metadata_normalized.jsonl"
    
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return
        
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total_segments = len(records)
    print(f"\n=== Transcript Normalization & Emotion Tagging Stage ===")
    print(f"Processing {total_segments} segments concurrently using 2 workers...")
    
    tracker = ProgressTracker(total_segments)
    
    # Process segments in parallel (MAX_WORKERS = 2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_record_task, record, idx, tracker) for idx, record in enumerate(records)]
        updated_records = [future.result() for future in futures]
        
    # Count final outcomes and statistics
    normalized_count = sum(1 for r in updated_records if r.get("was_normalized", False))
    unchanged_count = total_segments - normalized_count
    
    emotion_distribution = defaultdict(int)
    for r in updated_records:
        style = r.get("style", "neutral")
        emotion_distribution[style] += 1
        
    # Save output metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in updated_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    # Generate statistics JSON
    stats = {
        "total_segments": total_segments,
        "normalized_segments": normalized_count,
        "unchanged_segments": unchanged_count,
        "emotion_distribution": dict(emotion_distribution)
    }
    stats_path = ROOT_DIR / "data" / "normalization_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
        
    # Generate Benchmark Output
    total_runtime_min = (time.time() - global_start) / 60.0
    avg_req_time = tracker.total_latency / total_segments if total_segments > 0 else 0.0
    
    print("\nBenchmark:")
    print(f"Total Segments: {total_segments}")
    print(f"Successful: {tracker.successful}")
    print(f"Failed: {tracker.failed}")
    print(f"Average Request Time: {avg_req_time:.2f} sec")
    print(f"Total Runtime: {total_runtime_min:.2f} min")
    print("Workers: 2")
    print("Reasoning: Disabled")
    sys.stdout.flush()

# if __name__ == "__main__":
#     main()
