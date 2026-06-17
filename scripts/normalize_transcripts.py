"""
Transcript Normalization Stage for Telugu-English Code-Mixed Datasets.

Identifies segments containing English words written in Telugu script and
normalizes them back to English script using the Sarvam SDK (sarvam-30b).
Does not use any hardcoded word lists or dictionaries.
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

def needs_normalization_check(text):
    """
    Check if a transcript contains any Telugu characters.
    If it has no Telugu characters, it is pure English/numbers/punctuation and doesn't need normalization.
    This check uses unicode ranges and avoids hardcoded word lists.
    """
    text_clean = text.strip()
    if not text_clean:
        return False
        
    # Telugu unicode range: 0C00 - 0C7F
    has_telugu = any(0x0C00 <= ord(char) <= 0x0C7F for char in text_clean)
    return has_telugu

def normalize_transcript(text):
    """
    Normalize transliterated English words in Telugu script back to English script.
    Uses model sarvam-30b. Returns (normalized_transcript, was_normalized).
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Warning: SARVAM_API_KEY is not set.")
        return text, False
        
    client = SarvamAI(api_subscription_key=api_key)
    
    prompt = f"""You are a transcript normalizer for Telugu speech transcripts.

Your task is to convert English words written in Telugu script (transliterated English) back to standard English script, while preserving Telugu words in Telugu script exactly.

Rules:
1. Keep Telugu words in Telugu script. Do not translate Telugu words.
2. Convert English words written in Telugu script back to English.
3. Do not summarize or rewrite sentences. Preserve punctuation.
4. If a transcript contains no transliterated English, return it exactly as it is.

Return a JSON object with exactly these keys:
{{
  "normalized_transcript": "<the normalized transcript or the original text if no change was needed>",
  "was_normalized": <true if you converted any transliterated English words, false otherwise>
}}

Input:
ఐ విల్ టెల్ యు కేరళ ఇస్ హావింగ్ 20 సీట్స్
Output:
{{"normalized_transcript": "I will tell you Kerala is having 20 seats", "was_normalized": true}}

Input:
ఈ model చాలా powerful గా ఉంది
Output:
{{"normalized_transcript": "ఈ model చాలా powerful గా ఉంది", "was_normalized": false}}

Input:
కేంద్ర ప్రభుత్వం నిర్ణయం తీసుకుంది
Output:
{{"normalized_transcript": "కేంద్ర ప్రభుత్వం నిర్ణయం తీసుకుంది", "was_normalized": false}}

Input:
{text}
Output:"""

    try:
        response = client.chat.completions(
            messages=[{"role": "user", "content": prompt}],
            model="sarvam-30b",
            temperature=0.1
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
        was_norm = data.get("was_normalized", False)
        return norm_text, was_norm
    except Exception as e:
        print(f"Error calling Sarvam LLM in normalization: {e}")
        return text, False

def main():
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
    normalized_count = 0
    unchanged_count = 0
    
    print(f"\n=== Transcript Normalization Stage ===")
    print(f"Processing {total_segments} segments...")
    
    updated_records = []
    for idx, record in enumerate(records, start=1):
        transcript = record.get("transcript", "")
        record["raw_transcript"] = transcript
        
        if needs_normalization_check(transcript):
            print(f"[{idx}/{total_segments}] Checking normalization for: '{transcript[:40]}...'")
            normalized_text, was_normalized = normalize_transcript(transcript)
            if was_normalized:
                print(f"  -> Normalized: '{normalized_text[:40]}...'")
                normalized_count += 1
            else:
                unchanged_count += 1
            record["normalized_transcript"] = normalized_text
            record["was_normalized"] = was_normalized
            record["transcript"] = normalized_text
        else:
            record["normalized_transcript"] = transcript
            record["was_normalized"] = False
            unchanged_count += 1
            
        updated_records.append(record)
        
    # Save output metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in updated_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    # Generate statistics
    stats = {
        "total_segments": total_segments,
        "normalized_segments": normalized_count,
        "unchanged_segments": unchanged_count
    }
    stats_path = ROOT_DIR / "data" / "normalization_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
        
    print(f"\n=== Normalization Summary ===")
    print(f"Total segments:      {total_segments}")
    print(f"Normalized segments: {normalized_count} ({100*normalized_count/total_segments:.1f}%)" if total_segments > 0 else 0)
    print(f"Unchanged segments:  {unchanged_count} ({100*unchanged_count/total_segments:.1f}%)" if total_segments > 0 else 0)
    print(f"Stats saved to:      {stats_path}")
    print(f"Saved normalized metadata to: {output_path}")

# if __name__ == "__main__":
#     main()
