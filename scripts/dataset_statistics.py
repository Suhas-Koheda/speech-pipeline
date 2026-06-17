"""
Dataset Statistics & Reporting

Generates comprehensive statistics about the TTS training dataset.

Reports:
- Total videos processed
- Segment counts at each stage
- Duration statistics
- Language distribution
- Emotion distribution
- Quality metrics
"""

import json
from pathlib import Path
from collections import defaultdict
import numpy as np


def load_metadata(file_path):
    """Load JSONL metadata file."""
    records = []
    
    if not Path(file_path).exists():
        print(f"Warning: File not found: {file_path}")
        return records
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    
    return records


def calculate_statistics(
    raw_segments_path="../data/segments_metadata.jsonl",
    filtered_segments_path="../data/segments_metadata_filtered.jsonl",
    final_segments_path="../data/segments_metadata_final.jsonl",
    output_path="../data/statistics.json",
):
    """
    Calculate comprehensive statistics about the dataset.
    
    Args:
        raw_segments_path: Path to raw VAD segments
        filtered_segments_path: Path to quality-filtered segments
        final_segments_path: Path to final manually-reviewed segments
        output_path: Path to save statistics JSON
    """
    
    print(f"\n=== Calculating Dataset Statistics ===\n")
    
    # Load metadata files
    print("Loading metadata files...")
    raw_segments = load_metadata(raw_segments_path)
    filtered_segments = load_metadata(filtered_segments_path)
    final_segments = load_metadata(final_segments_path)
    
    print(f"Raw segments: {len(raw_segments)}")
    print(f"Filtered segments: {len(filtered_segments)}")
    print(f"Final segments: {len(final_segments)}")
    
    # Use final segments if available, else fall back to raw
    segments_to_analyze = final_segments if final_segments else raw_segments
    
    # Initialize statistics dictionary
    stats = {
        "metadata": {
            "generated_at": str(Path.cwd()),
            "total_files_analyzed": 3,
        },
        "processing_summary": {
            "raw_segments_generated": len(raw_segments),
            "segments_after_filtering": len(filtered_segments),
            "final_segments_accepted": len(final_segments),
        },
        "segment_statistics": {},
        "duration_statistics": {},
        "language_distribution": {},
        "emotion_distribution": {},
        "speaker_distribution": {},
        "quality_metrics": {},
    }
    
    # ===== Segment Statistics =====
    if segments_to_analyze:
        total_segments = len(segments_to_analyze)
        
        stats["segment_statistics"] = {
            "total": total_segments,
            "unique_videos": len(set(s.get("video_id") for s in segments_to_analyze)),
            "unique_channels": len(set(s.get("channel") for s in segments_to_analyze)),
        }
        
        # ===== Duration Statistics =====
        durations = [s.get("duration", 0) for s in segments_to_analyze]
        
        stats["duration_statistics"] = {
            "total_minutes": round(sum(durations) / 60, 2),
            "total_hours": round(sum(durations) / 3600, 2),
            "mean_seconds": round(np.mean(durations), 2),
            "median_seconds": round(np.median(durations), 2),
            "min_seconds": round(min(durations), 2),
            "max_seconds": round(max(durations), 2),
            "std_dev": round(np.std(durations), 2),
        }
        
        # ===== Language Distribution =====
        language_stats = defaultdict(lambda: {"count": 0, "duration": 0})
        
        for segment in segments_to_analyze:
            language = segment.get("language", "unknown")
            language_stats[language]["count"] += 1
            language_stats[language]["duration"] += segment.get("duration", 0)
        
        for lang, data in language_stats.items():
            stats["language_distribution"][lang] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
            }
        
        # ===== Emotion Distribution =====
        emotion_stats = defaultdict(lambda: {"count": 0, "duration": 0, "confidence": []})
        
        for segment in segments_to_analyze:
            emotion = segment.get("emotion", "unknown")
            emotion_stats[emotion]["count"] += 1
            emotion_stats[emotion]["duration"] += segment.get("duration", 0)
            
            conf = segment.get("emotion_confidence", 0)
            if conf > 0:
                emotion_stats[emotion]["confidence"].append(conf)
        
        for emotion, data in emotion_stats.items():
            avg_confidence = (
                round(np.mean(data["confidence"]), 2)
                if data["confidence"]
                else 0.0
            )
            
            stats["emotion_distribution"][emotion] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
                "avg_confidence": avg_confidence,
            }
        
        # ===== Speaker Distribution =====
        speaker_stats = defaultdict(lambda: {"count": 0, "duration": 0})
        
        for segment in segments_to_analyze:
            speaker = segment.get("dominant_speaker", "UNKNOWN")
            speaker_stats[speaker]["count"] += 1
            speaker_stats[speaker]["duration"] += segment.get("duration", 0)
        
        for speaker, data in speaker_stats.items():
            stats["speaker_distribution"][speaker] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
            }
        
        # ===== Quality Metrics =====
        quality_scores = [s.get("quality_score", 1.0) for s in segments_to_analyze]
        
        stats["quality_metrics"] = {
            "average_quality_score": round(np.mean(quality_scores), 3),
            "median_quality_score": round(np.median(quality_scores), 3),
            "min_quality_score": round(np.min(quality_scores), 3),
            "perfect_quality_segments": sum(1 for s in quality_scores if s == 1.0),
        }
        
        # Count issues
        issue_counts = defaultdict(int)
        for segment in raw_segments:
            issues = segment.get("quality_issues", [])
            for issue in issues:
                issue_counts[issue] += 1
        
        if issue_counts:
            stats["quality_metrics"]["issue_breakdown"] = dict(issue_counts)
    
    # Save statistics
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Statistics Summary ===\n")
    print_statistics(stats)
    print(f"\nSaved to: {output_path}")
    
    return stats


def print_statistics(stats):
    """Pretty print statistics."""
    
    print("PROCESSING SUMMARY:")
    summary = stats.get("processing_summary", {})
    print(f"  Raw segments generated: {summary.get('raw_segments_generated', 0)}")
    print(f"  After filtering: {summary.get('segments_after_filtering', 0)}")
    print(f"  Final (accepted): {summary.get('final_segments_accepted', 0)}")
    
    print("\nSEGMENT STATISTICS:")
    seg_stats = stats.get("segment_statistics", {})
    print(f"  Total segments: {seg_stats.get('total', 0)}")
    print(f"  Unique videos: {seg_stats.get('unique_videos', 0)}")
    print(f"  Unique channels: {seg_stats.get('unique_channels', 0)}")
    
    print("\nDURATION STATISTICS:")
    dur_stats = stats.get("duration_statistics", {})
    print(f"  Total duration: {dur_stats.get('total_minutes', 0)} minutes")
    print(f"  ({dur_stats.get('total_hours', 0)} hours)")
    print(f"  Mean duration: {dur_stats.get('mean_seconds', 0)} seconds")
    print(f"  Median duration: {dur_stats.get('median_seconds', 0)} seconds")
    print(f"  Min-Max: {dur_stats.get('min_seconds', 0)}-{dur_stats.get('max_seconds', 0)} seconds")
    
    print("\nLANGUAGE DISTRIBUTION:")
    lang_dist = stats.get("language_distribution", {})
    for lang in sorted(lang_dist.keys()):
        data = lang_dist[lang]
        print(f"  {lang.upper():5s}: {data.get('segments', 0):4d} segments, "
              f"{data.get('duration_minutes', 0):6.1f} min "
              f"({data.get('percentage', 0):5.1f}%)")
    
    print("\nEMOTION DISTRIBUTION:")
    emotion_dist = stats.get("emotion_distribution", {})
    for emotion in sorted(emotion_dist.keys()):
        data = emotion_dist[emotion]
        conf = data.get('avg_confidence', 0)
        print(f"  {emotion:15s}: {data.get('segments', 0):4d} segments, "
              f"{data.get('duration_minutes', 0):6.1f} min, "
              f"confidence: {conf:.2f}")
    
    print("\nQUALITY METRICS:")
    quality = stats.get("quality_metrics", {})
    print(f"  Average quality score: {quality.get('average_quality_score', 0):.3f}")
    print(f"  Perfect quality segments: {quality.get('perfect_quality_segments', 0)}")
    
    if "issue_breakdown" in quality:
        print("  Quality issues:")
        for issue, count in sorted(quality["issue_breakdown"].items()):
            print(f"    {issue}: {count}")


def generate_html_report(
    stats,
    output_path="../data/statistics.html",
):
    """Generate an HTML report from statistics."""
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>TTS Dataset Statistics</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .summary { background-color: #e7f3fe; padding: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>TTS Training Dataset - Statistics Report</h1>
    
    <div class="summary">
        <h3>Dataset Summary</h3>
"""
    
    summary = stats.get("processing_summary", {})
    duration = stats.get("duration_statistics", {})
    
    html_content += f"""
        <p><strong>Total Segments:</strong> {summary.get('final_segments_accepted', 0)}</p>
        <p><strong>Total Duration:</strong> {duration.get('total_hours', 0):.1f} hours ({duration.get('total_minutes', 0):.0f} minutes)</p>
        <p><strong>Languages:</strong> {', '.join(stats.get('language_distribution', {}).keys())}</p>
    </div>
    
    <h2>Processing Pipeline</h2>
    <table>
        <tr>
            <th>Stage</th>
            <th>Segment Count</th>
        </tr>
        <tr>
            <td>Raw segments generated</td>
            <td>{summary.get('raw_segments_generated', 0)}</td>
        </tr>
        <tr>
            <td>After quality filtering</td>
            <td>{summary.get('segments_after_filtering', 0)}</td>
        </tr>
        <tr>
            <td>Final (manually reviewed)</td>
            <td>{summary.get('final_segments_accepted', 0)}</td>
        </tr>
    </table>
    
    <h2>Language Distribution</h2>
    <table>
        <tr>
            <th>Language</th>
            <th>Segments</th>
            <th>Duration (min)</th>
            <th>Percentage</th>
        </tr>
"""
    
    for lang in sorted(stats.get("language_distribution", {}).keys()):\n        data = stats["language_distribution"][lang]
        html_content += f"""
        <tr>
            <td>{lang.upper()}</td>
            <td>{data.get('segments', 0)}</td>
            <td>{data.get('duration_minutes', 0):.1f}</td>
            <td>{data.get('percentage', 0):.1f}%</td>
        </tr>
"""
    
    html_content += """
    </table>
    
    <h2>Emotion Distribution</h2>
    <table>
        <tr>
            <th>Emotion</th>
            <th>Segments</th>
            <th>Duration (min)</th>
            <th>Avg Confidence</th>
        </tr>
"""
    
    for emotion in sorted(stats.get("emotion_distribution", {}).keys()):
        data = stats["emotion_distribution"][emotion]
        html_content += f"""
        <tr>
            <td>{emotion}</td>
            <td>{data.get('segments', 0)}</td>
            <td>{data.get('duration_minutes', 0):.1f}</td>
            <td>{data.get('avg_confidence', 0):.2f}</td>
        </tr>
"""
    
    html_content += """
    </table>
    
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Generated HTML report: {output_path}")


if __name__ == "__main__":
    stats = calculate_statistics()
    generate_html_report(stats)
