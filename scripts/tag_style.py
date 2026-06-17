"""
Emotion / Style Tagging Stage.

Classifies the speaking style / emotion of transcripts using a single,
parallelized, optimized Sarvam LLM call (sarvam-30b) with reasoning disabled.
Does NOT modify or rewrite the transcript text.
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

# Valid style labels
VALID_STYLES = {
    "conversational", "formal", "informative", "educational", "storytelling",
    "interview", "discussion", "motivational", "humorous", "analytical",
    "excited", "happy", "sad", "angry", "neutral"
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

def tag_style_with_retry(text):
    """
    Query Sarvam-30b to tag speaking style.
    Uses exponential backoff for retries on rate limits or failures.
    Returns (style, confidence, retries_used, duration, success).
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Warning: SARVAM_API_KEY is not set.")
        return "neutral", 1.0, 0, 0.0, False
        
    client = SarvamAI(api_subscription_key=api_key)
    
    prompt = f"""You are a speech dataset annotator.

Classify the speaking style of the transcript.

Do not rewrite, correct, normalize, translate, or modify the transcript.

Choose exactly one label:
* conversational
* formal
* informative
* educational
* storytelling
* interview
* discussion
* motivational
* humorous
* analytical
* excited
* happy
* sad
* angry
* neutral

Return ONLY JSON:
{{
"style": "chosen_style",
"confidence": 0.95
}}

Input:
{text}
Output:"""

    backoffs = [1.0, 2.0, 4.0]
    retries_used = 0
    start_time = time.time()
    
    for attempt in range(4):  # attempt 0 is initial try, 1-3 are retries
        try:
            response = client.chat.completions(
                model="sarvam-30b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100,
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
            style = data.get("style", "neutral").lower().strip()
            confidence = float(data.get("confidence", 1.0))
            
            if style not in VALID_STYLES:
                style = "neutral"
                
            duration = time.time() - start_time
            return style, confidence, retries_used, duration, True
            
        except Exception as e:
            err_str = str(e).lower()
            is_retryable = any(status in err_str for status in ["429", "500", "503", "rate limit", "timeout", "busy", "remote"]) or "timeout" in err_str
            
            if is_retryable and attempt < 3:
                sleep_time = backoffs[attempt]
                retries_used += 1
                time.sleep(sleep_time)
            else:
                duration = time.time() - start_time
                return "neutral", 1.0, retries_used, duration, False

def process_record_task(record, idx, tracker):
    """Worker task that processes a single segment record."""
    transcript = record.get("transcript", "")
    style, confidence, retries_used, duration, success = tag_style_with_retry(transcript)
    
    if success:
        tracker.record_success(duration, style, retries_used)
    else:
        tracker.record_failure(duration, retries_used)
        
    # Store style and style_confidence as requested
    record["style"] = style
    record["style_confidence"] = confidence
    
    # Store emotion and emotion_confidence for compatibility
    record["emotion"] = style
    record["emotion_confidence"] = confidence
    
    return record

def main():
    global_start = time.time()
    
    input_path = ROOT_DIR / "data" / "segments_metadata_filtered.jsonl"
    output_path = ROOT_DIR / "data" / "segments_metadata_emotions.jsonl"
    
    if not input_path.exists():
        print(f"Error: Filtered metadata file does not exist: {input_path}")
        print("Please run Quality Filtering step first.")
        return
        
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total_segments = len(records)
    print(f"\n=== Speaking Style & Emotion Tagging Stage ===")
    print(f"Processing {total_segments} segments concurrently using 2 workers...")
    
    tracker = ProgressTracker(total_segments)
    
    # Process segments in parallel (MAX_WORKERS = 2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_record_task, record, idx, tracker) for idx, record in enumerate(records)]
        updated_records = [future.result() for future in futures]
        
    style_distribution = defaultdict(int)
    for r in updated_records:
        style = r.get("style", "neutral")
        style_distribution[style] += 1
        
    # Save output metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in updated_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    # Generate statistics JSON
    stats = {
        "total_segments": total_segments,
        "style_distribution": dict(style_distribution)
    }
    stats_path = ROOT_DIR / "data" / "tagging_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
        
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

if __name__ == "__main__":
    main()
