"""
Dataset Statistics & Reporting

Generates comprehensive statistics and a premium visual report about the TTS dataset.
Reports:
- Processing summary (raw, filtered, final)
- Duration metrics (total duration, mean, median, min, max, std)
- Language distribution (English vs Telugu)
- Emotion/style counts and confidence
- Speaker distribution
- Quality metrics and issue breakdowns
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
                if line.strip():
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
    """
    print(f"\n=== Calculating Dataset Statistics ===")
    
    raw_segments = load_metadata(raw_segments_path)
    filtered_segments = load_metadata(filtered_segments_path)
    final_segments = load_metadata(final_segments_path)
    
    print(f"Raw segments: {len(raw_segments)}")
    print(f"Filtered segments: {len(filtered_segments)}")
    print(f"Final segments: {len(final_segments)}")
    
    # Analyze final segments if they exist, otherwise fall back to filtered, then raw
    if final_segments:
        segments_to_analyze = final_segments
        stage_analyzed = "final (reviewed)"
    elif filtered_segments:
        segments_to_analyze = filtered_segments
        stage_analyzed = "filtered"
    else:
        segments_to_analyze = raw_segments
        stage_analyzed = "raw"
        
    print(f"Analyzing stage: {stage_analyzed} ({len(segments_to_analyze)} segments)")
    
    stats = {
        "metadata": {
            "stage_analyzed": stage_analyzed,
            "total_segments_analyzed": len(segments_to_analyze),
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
    
    if segments_to_analyze:
        total_segments = len(segments_to_analyze)
        
        # 1. Segment Stats
        stats["segment_statistics"] = {
            "total": total_segments,
            "unique_videos": len(set(s.get("video_id") for s in segments_to_analyze if s.get("video_id"))),
            "unique_channels": len(set(s.get("channel") for s in segments_to_analyze if s.get("channel"))),
        }
        
        # 2. Duration Stats
        durations = []
        for s in segments_to_analyze:
            d = s.get("duration", 0.0)
            if d <= 0.0:
                d = s.get("end", 0.0) - s.get("start", 0.0)
            durations.append(d)
            
        if durations:
            stats["duration_statistics"] = {
                "total_minutes": round(sum(durations) / 60, 2),
                "total_hours": round(sum(durations) / 3600, 2),
                "mean_seconds": round(float(np.mean(durations)), 2),
                "median_seconds": round(float(np.median(durations)), 2),
                "min_seconds": round(float(min(durations)), 2),
                "max_seconds": round(float(max(durations)), 2),
                "std_dev": round(float(np.std(durations)), 2),
            }
        else:
            stats["duration_statistics"] = {
                "total_minutes": 0.0,
                "total_hours": 0.0,
                "mean_seconds": 0.0,
                "median_seconds": 0.0,
                "min_seconds": 0.0,
                "max_seconds": 0.0,
                "std_dev": 0.0,
            }
            
        # 3. Language Distribution
        lang_stats = defaultdict(lambda: {"count": 0, "duration": 0})
        for segment, dur in zip(segments_to_analyze, durations):
            lang = segment.get("language", "unknown")
            lang_stats[lang]["count"] += 1
            lang_stats[lang]["duration"] += dur
            
        for lang, data in lang_stats.items():
            stats["language_distribution"][lang] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
            }
            
        # 4. Emotion Distribution
        emotion_stats = defaultdict(lambda: {"count": 0, "duration": 0, "confidence": []})
        for segment, dur in zip(segments_to_analyze, durations):
            emotion = segment.get("emotion", "neutral")
            emotion_stats[emotion]["count"] += 1
            emotion_stats[emotion]["duration"] += dur
            conf = segment.get("emotion_confidence", 1.0)
            emotion_stats[emotion]["confidence"].append(conf)
            
        for emotion, data in emotion_stats.items():
            avg_confidence = float(np.mean(data["confidence"])) if data["confidence"] else 1.0
            stats["emotion_distribution"][emotion] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
                "avg_confidence": round(avg_confidence, 2),
            }
            
        # 5. Speaker Distribution
        speaker_stats = defaultdict(lambda: {"count": 0, "duration": 0})
        for segment, dur in zip(segments_to_analyze, durations):
            speaker = segment.get("dominant_speaker", segment.get("speaker_id", "UNKNOWN"))
            speaker_stats[speaker]["count"] += 1
            speaker_stats[speaker]["duration"] += dur
            
        for speaker, data in speaker_stats.items():
            stats["speaker_distribution"][speaker] = {
                "segments": data["count"],
                "duration_minutes": round(data["duration"] / 60, 2),
                "percentage": round(100 * data["count"] / total_segments, 1),
            }
            
        # 6. Quality Metrics
        quality_scores = [s.get("quality_score", 1.0) for s in segments_to_analyze]
        stats["quality_metrics"] = {
            "average_quality_score": round(float(np.mean(quality_scores)), 3) if quality_scores else 1.0,
            "perfect_quality_segments": sum(1 for s in quality_scores if s >= 1.0),
        }
        
        # Count quality issues in raw files
        issue_counts = defaultdict(int)
        for segment in raw_segments:
            issues = segment.get("quality_issues", [])
            for issue in issues:
                issue_counts[issue] += 1
        if issue_counts:
            stats["quality_metrics"]["issue_breakdown"] = dict(issue_counts)

    # Save to JSON
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
        
    print(f"Saved statistics JSON to: {output_path}")
    return stats


def generate_html_report(stats, output_path="../data/statistics.html"):
    """
    Generate a high-end, premium HTML dashboard report.
    """
    summary = stats.get("processing_summary", {})
    dur_stats = stats.get("duration_statistics", {})
    seg_stats = stats.get("segment_statistics", {})
    quality = stats.get("quality_metrics", {})
    
    total_hours = dur_stats.get("total_hours", 0.0)
    total_mins = dur_stats.get("total_minutes", 0.0)
    
    # Format HTML content with modern CSS layout and dark glassmorphic design
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS Dataset Insights Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.6);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --success: #10b981;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(to right, #a5b4fc, #6366f1, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .badge {{
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.25);
        }}
        
        .card-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .card-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-main);
        }}
        
        .card-sub {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 6px;
        }}
        
        /* Two Column Layout */
        .section-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        h2 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #e5e7eb;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        /* Tables and Bars */
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            text-align: left;
            padding: 12px;
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-color);
        }}
        
        td {{
            padding: 14px 12px;
            font-size: 0.95rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-main);
        }}
        
        .progress-container {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .progress-bar {{
            flex-grow: 1;
            height: 6px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 3px;
            overflow: hidden;
            max-width: 120px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(to right, #6366f1, #3b82f6);
            border-radius: 3px;
        }}
        
        .progress-fill.telugu {{
            background: linear-gradient(to right, #10b981, #059669);
        }}
        
        .progress-fill.english {{
            background: linear-gradient(to right, #3b82f6, #6366f1);
        }}
        
        .progress-value {{
            font-weight: 600;
            font-size: 0.9rem;
            min-width: 45px;
        }}
        
        .tag {{
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #d1d5db;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>TTS Dataset Insights</h1>
                <p style="color: var(--text-muted); margin-top: 4px;">Production Curation Dashboard & Quality Overview</p>
            </div>
            <div class="badge">Stage: {stats.get('metadata', {}).get('stage_analyzed', 'N/A').upper()}</div>
        </header>
        
        <!-- Summary Cards -->
        <div class="stats-grid">
            <div class="card">
                <div class="card-label">Total Duration</div>
                <div class="card-value">{total_hours:.2f} hrs</div>
                <div class="card-sub">{total_mins:.1f} minutes of clean audio</div>
            </div>
            <div class="card">
                <div class="card-label">Clean Segments</div>
                <div class="card-value">{seg_stats.get('total', 0)}</div>
                <div class="card-sub">From {seg_stats.get('unique_videos', 0)} videos / {seg_stats.get('unique_channels', 0)} channels</div>
            </div>
            <div class="card">
                <div class="card-label">Avg Seg Length</div>
                <div class="card-value">{dur_stats.get('mean_seconds', 0.0):.1f}s</div>
                <div class="card-sub">Range: {dur_stats.get('min_seconds', 0.0):.1f}s to {dur_stats.get('max_seconds', 0.0):.1f}s</div>
            </div>
            <div class="card">
                <div class="card-label">Curation Yield</div>
                <div class="card-value">
                    {100*summary.get('final_segments_accepted', 0)/summary.get('raw_segments_generated', 1) if summary.get('raw_segments_generated', 0) > 0 else 0.0:.1f}%
                </div>
                <div class="card-sub">{summary.get('final_segments_accepted', 0)} of {summary.get('raw_segments_generated', 0)} raw segments</div>
            </div>
        </div>
        
        <div class="section-grid">
            <!-- Language Distribution Card -->
            <div class="card">
                <h2>Language Curation</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Language</th>
                            <th>Segments</th>
                            <th>Duration</th>
                            <th>Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for lang, data in sorted(stats.get("language_distribution", {}).items()):
        class_name = "telugu" if "te" in lang.lower() else "english"
        html_content += f"""
                        <tr>
                            <td><strong>{lang.upper()}</strong></td>
                            <td>{data.get('segments', 0)}</td>
                            <td>{data.get('duration_minutes', 0.0):.1f} mins</td>
                            <td>
                                <div class="progress-container">
                                    <div class="progress-bar">
                                        <div class="progress-fill {class_name}" style="width: {data.get('percentage', 0)}%"></div>
                                    </div>
                                    <span class="progress-value">{data.get('percentage', 0)}%</span>
                                </div>
                            </td>
                        </tr>
"""
        
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <!-- Quality & Pipeline Card -->
            <div class="card">
                <h2>Curation Pipeline Funnel</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Pipeline Stage</th>
                            <th>Remaining Segments</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    html_content += f"""
                        <tr>
                            <td>1. Raw segments (VAD)</td>
                            <td><strong>{summary.get('raw_segments_generated', 0)}</strong></td>
                            <td><span class="tag" style="background: rgba(59, 130, 246, 0.15); color: #93c5fd;">Generated</span></td>
                        </tr>
                        <tr>
                            <td>2. Quality filtered</td>
                            <td><strong>{summary.get('segments_after_filtering', 0)}</strong></td>
                            <td><span class="tag" style="background: rgba(16, 185, 129, 0.15); color: #a7f3d0;">Passed</span></td>
                        </tr>
                        <tr>
                            <td>3. Manually Reviewed</td>
                            <td><strong>{summary.get('final_segments_accepted', 0)}</strong></td>
                            <td><span class="tag" style="background: rgba(99, 102, 241, 0.15); color: #c7d2fe;">Approved</span></td>
                        </tr>
    """
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section-grid">
            <!-- Emotion Distribution Card -->
            <div class="card" style="grid-column: span 2;">
                <h2>Emotion & Expression Profiles</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Emotion Tag</th>
                            <th>Segment Count</th>
                            <th>Total Duration</th>
                            <th>Proportion</th>
                            <th>Avg Classifier Confidence</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for emotion, data in sorted(stats.get("emotion_distribution", {}).items()):
        html_content += f"""
                        <tr>
                            <td><span class="tag">{emotion.upper()}</span></td>
                            <td>{data.get('segments', 0)}</td>
                            <td>{data.get('duration_minutes', 0.0):.1f} mins</td>
                            <td>
                                <div class="progress-container">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: {data.get('percentage', 0)}%; background: #6366f1;"></div>
                                    </div>
                                    <span class="progress-value">{data.get('percentage', 0)}%</span>
                                </div>
                            </td>
                            <td><strong>{data.get('avg_confidence', 0.0):.2f}</strong></td>
                        </tr>
    """
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Quality issues breakdown -->
        <div class="card" style="margin-top: 10px;">
            <h2>Rejection Issues Analysis</h2>
            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 15px;">
    """
    
    issue_breakdown = quality.get("issue_breakdown", {})
    if issue_breakdown:
        for issue, count in sorted(issue_breakdown.items()):
            html_content += f"""
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 12px 18px; border-radius: 10px; min-width: 140px;">
                    <div style="font-size: 0.75rem; color: #fca5a5; font-weight: 600; text-transform: uppercase;">{issue}</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #fee2e2; margin-top: 4px;">{count} <span style="font-size: 0.85rem; font-weight: 400; color: var(--text-muted);">segments</span></div>
                </div>
            """
    else:
        html_content += """
            <p style="color: var(--text-muted);">No quality filtering issues recorded.</p>
        """
        
    html_content += """
            </div>
        </div>
        
    </div>
</body>
</html>
    """
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Generated HTML report at: {output_path}")


def main():
    stats = calculate_statistics()
    generate_html_report(stats)

# if __name__ == "__main__":
#     main()
