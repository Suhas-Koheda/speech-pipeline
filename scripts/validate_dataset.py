"""
Dataset Validation & Diagnostics Stage

Applies final quality checks to transcripts, audio, and speakers, producing
validation_report.json and an interactive HTML validation dashboard.
"""

import json
from pathlib import Path
from collections import defaultdict
import numpy as np

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Validation thresholds
REPETITION_THRESHOLD = 0.70
MIN_DURATION = 0.0
MAX_DURATION = 200.0

def calculate_repetition_rate(transcript):
    """
    Calculates the lexical repetition rate of a transcript.
    Lexical repetition = 1.0 - (unique_words / total_words)
    """
    words = transcript.strip().lower().split()
    if not words:
        return 1.0
    return 1.0 - (len(set(words)) / len(words))

def validate_dataset():
    print("=== Running Dataset Validation Stage ===")
    
    input_path = ROOT_DIR / "data" / "segments_metadata_emotions.jsonl"
    if not input_path.exists():
        print(f"Warning: {input_path} not found. Trying filtered metadata...")
        input_path = ROOT_DIR / "data" / "segments_metadata_filtered.jsonl"
        
    if not input_path.exists():
        print(f"Warning: {input_path} not found. Trying raw segments metadata...")
        input_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
        
    if not input_path.exists():
        print(f"Error: No segment metadata files found to validate.")
        return
        
    print(f"Loading data from: {input_path}")
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total_segments = len(records)
    if total_segments == 0:
        print("No segments found for validation.")
        return
        
    # Stats tracking
    durations = []
    speaker_counts = defaultdict(int)
    emotion_counts = defaultdict(int)
    rejection_reasons_counts = defaultdict(int)
    
    validated_records = []
    final_records = []
    rejected_count = 0
    
    for record in records:
        rejection_reasons = []
        
        # 1. Transcript checks
        transcript = record.get("transcript", "").strip()
        if not transcript:
            rejection_reasons.append("EMPTY_TRANSCRIPT")
        elif len(transcript) < 1:
            rejection_reasons.append("SHORT_TRANSCRIPT")
            
        repetition_rate = calculate_repetition_rate(transcript)
        record["repetition_rate"] = round(repetition_rate, 3)
        if repetition_rate > REPETITION_THRESHOLD:
            rejection_reasons.append("HIGH_REPETITION")
            
        # 2. Audio checks
        duration = record.get("duration", 0.0)
        if duration <= 0.0:
            duration = record.get("end", 0.0) - record.get("start", 0.0)
            record["duration"] = duration
            
        durations.append(duration)
        if duration < MIN_DURATION:
            rejection_reasons.append("SHORT_DURATION")
        elif duration > MAX_DURATION:
            rejection_reasons.append("LONG_DURATION")
            
        # 3. Speaker checks
        speaker = record.get("speaker", "unknown")
        if not speaker or speaker == "unknown" or speaker.lower() == "speaker_unknown":
            rejection_reasons.append("UNKNOWN_SPEAKER")
            
        # Compile status
        if rejection_reasons:
            record["validation_status"] = "rejected"
            record["rejection_reasons"] = rejection_reasons
            rejected_count += 1
            for reason in rejection_reasons:
                rejection_reasons_counts[reason] += 1
        else:
            record["validation_status"] = "passed"
            record["rejection_reasons"] = []
            final_records.append(record)
            
        validated_records.append(record)
        
        # Track counts for stats
        sp_name = record.get("speaker", "unknown")
        speaker_counts[sp_name] += 1
        
        em_name = record.get("emotion")
        em_key = em_name if em_name is not None else "null"
        emotion_counts[em_key] += 1
        
    avg_duration = float(np.mean(durations)) if durations else 0.0
    pass_rate = 100 * (total_segments - rejected_count) / total_segments if total_segments > 0 else 0.0
    
    # 4. Generate JSON Report
    report = {
        "total_segments": total_segments,
        "avg_duration": round(avg_duration, 2),
        "speaker_distribution": dict(speaker_counts),
        "emotion_distribution": dict(emotion_counts),
        "rejected_segments": rejected_count,
        "rejection_reasons": dict(rejection_reasons_counts)
    }
    
    report_path = ROOT_DIR / "data" / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"Validation report saved to: {report_path}")
    
    # Write validated metadata file
    validated_path = ROOT_DIR / "data" / "segments_metadata_validated.jsonl"
    with open(validated_path, "w", encoding="utf-8") as f:
        for record in validated_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    # Write final metadata file for downstream tasks
    final_path = ROOT_DIR / "data" / "segments_metadata_final.jsonl"
    with open(final_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"Validated dataset saved. Passed: {len(final_records)} | Rejected: {rejected_count}")
    
    # 5. Generate HTML Dashboard
    generate_dashboard(report, pass_rate, validated_records)

def generate_dashboard(report, pass_rate, records):
    dashboard_path = ROOT_DIR / "data" / "validation_dashboard.html"
    
    # Pre-format rows for the table
    rejected_rows_html = []
    count = 0
    for r in records:
        if r.get("validation_status") == "rejected" and count < 100:
            reasons = ", ".join(r.get("rejection_reasons", []))
            transcript = r.get("transcript", "")
            if len(transcript) > 60:
                transcript = transcript[:57] + "..."
            row = f"""
            <tr>
                <td><code>{r.get('video_id', '')}</code></td>
                <td>{r.get('duration', 0.0):.2f}s</td>
                <td>{r.get('speaker', 'unknown')}</td>
                <td><span class="reason-tag">{reasons}</span></td>
                <td>{transcript}</td>
            </tr>
            """
            rejected_rows_html.append(row)
            count += 1
            
    table_rows = "\n".join(rejected_rows_html)
    
    # Sort dictionaries for charts
    rejection_items = sorted(report["rejection_reasons"].items(), key=lambda x: x[1], reverse=True)
    rejection_bars = []
    for reason, val in rejection_items:
        pct = 100 * val / report["total_segments"] if report["total_segments"] > 0 else 0
        rejection_bars.append(f"""
        <div class="stat-bar-container">
            <div class="stat-bar-label">
                <span>{reason}</span>
                <span>{val} ({pct:.1f}%)</span>
            </div>
            <div class="stat-bar-track">
                <div class="stat-bar-fill fill-red" style="width: {pct}%"></div>
            </div>
        </div>
        """)
        
    speaker_items = sorted(report["speaker_distribution"].items(), key=lambda x: x[1], reverse=True)
    speaker_bars = []
    for sp, val in speaker_items[:8]:  # Top 8
        pct = 100 * val / report["total_segments"] if report["total_segments"] > 0 else 0
        speaker_bars.append(f"""
        <div class="stat-bar-container">
            <div class="stat-bar-label">
                <span>{sp}</span>
                <span>{val} ({pct:.1f}%)</span>
            </div>
            <div class="stat-bar-track">
                <div class="stat-bar-fill fill-indigo" style="width: {pct}%"></div>
            </div>
        </div>
        """)
        
    emotion_items = sorted(report["emotion_distribution"].items(), key=lambda x: x[1], reverse=True)
    emotion_bars = []
    for em, val in emotion_items:
        pct = 100 * val / report["total_segments"] if report["total_segments"] > 0 else 0
        emotion_bars.append(f"""
        <div class="stat-bar-container">
            <div class="stat-bar-label">
                <span>{em}</span>
                <span>{val} ({pct:.1f}%)</span>
            </div>
            <div class="stat-bar-track">
                <div class="stat-bar-fill fill-green" style="width: {pct}%"></div>
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS Dataset Validation Insights</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0b0f19;
            --bg-surface: #151d30;
            --bg-card: #1e2942;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
            --border: #334155;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            padding: 2.5rem 1.5rem;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1280px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 2.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
        }}
        
        h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #a5b4fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{
            color: var(--text-muted);
            font-size: 1rem;
            margin-top: 0.25rem;
        }}
        
        /* Summary Metrics Cards Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        
        .metric-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.25);
        }}
        
        .metric-title {{
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .metric-value {{
            font-size: 2.25rem;
            font-weight: 700;
            margin-top: 0.5rem;
            display: flex;
            align-items: baseline;
        }}
        
        .metric-unit {{
            font-size: 1rem;
            color: var(--text-muted);
            margin-left: 0.25rem;
        }}
        
        .badge {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.25rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 9999px;
        }}
        
        .badge-success {{ background-color: rgba(16, 185, 129, 0.2); color: var(--success); }}
        .badge-error {{ background-color: rgba(239, 68, 68, 0.2); color: var(--error); }}
        
        /* Main Layout */
        .main-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }}
        
        .section-card {{
            background-color: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.75rem;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid var(--primary);
            padding-left: 0.75rem;
        }}
        
        /* Progress bars */
        .stat-bar-container {{
            margin-bottom: 1.25rem;
        }}
        
        .stat-bar-label {{
            display: flex;
            justify-content: space-between;
            font-size: 0.875rem;
            margin-bottom: 0.35rem;
            font-weight: 500;
        }}
        
        .stat-bar-track {{
            height: 8px;
            background-color: #0f172a;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .stat-bar-fill {{
            height: 100%;
            border-radius: 4px;
        }}
        
        .fill-indigo {{ background-color: var(--primary); }}
        .fill-red {{ background-color: var(--error); }}
        .fill-green {{ background-color: var(--success); }}
        
        /* Tables */
        .table-wrapper {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-top: 1.5rem;
            background-color: var(--bg-surface);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }}
        
        th {{
            background-color: var(--bg-card);
            padding: 0.85rem 1rem;
            font-weight: 600;
            color: var(--text-main);
            border-bottom: 1px solid var(--border);
        }}
        
        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border);
            color: var(--text-muted);
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        code {{
            font-family: 'JetBrains Mono', monospace;
            background-color: rgba(0,0,0,0.2);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            color: #f43f5e;
            font-size: 0.8rem;
        }}
        
        .reason-tag {{
            background-color: rgba(239, 68, 68, 0.1);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.2);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }}
        
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TTS Dataset Validation Insights</h1>
            <div class="subtitle">Diagnostics & Quality Summary report for curated Telugu segments</div>
        </header>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <span class="badge badge-success">Evaluated</span>
                <div class="metric-title">Total Evaluated</div>
                <div class="metric-value">{report["total_segments"]} <span class="metric-unit">clips</span></div>
            </div>
            
            <div class="metric-card">
                <span class="badge badge-error">Rejected</span>
                <div class="metric-title">Rejected Clips</div>
                <div class="metric-value" style="color: var(--error);">{report["rejected_segments"]} <span class="metric-unit">clips</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Pass Rate</div>
                <div class="metric-value" style="color: { 'var(--success)' if pass_rate >= 75 else 'var(--warning)' };">{pass_rate:.1f}<span class="metric-unit">%</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Avg Clip Length</div>
                <div class="metric-value">{report["avg_duration"]} <span class="metric-unit">sec</span></div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="section-card">
                <div class="section-title">Rejection Reason Breakdown</div>
                {"".join(rejection_bars) if report["rejection_reasons"] else '<p style="color: var(--text-muted)">No segments rejected! Excellent quality.</p>'}
            </div>
            
            <div class="section-card">
                <div class="section-title">Speaker Distribution</div>
                {"".join(speaker_bars) if report["speaker_distribution"] else '<p style="color: var(--text-muted)">No speaker data available.</p>'}
            </div>
            
            <div class="section-card">
                <div class="section-title">Emotion Distribution</div>
                {"".join(emotion_bars) if report["emotion_distribution"] else '<p style="color: var(--text-muted)">No emotion tags generated.</p>'}
            </div>
        </div>
        
        <div class="section-card" style="grid-column: span 3;">
            <div class="section-title">Validation Failure Details (Top 100 Rejected Clips)</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Video ID</th>
                            <th>Duration</th>
                            <th>Speaker</th>
                            <th>Validation Failures</th>
                            <th>Transcript Slice</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else '<tr><td colspan="5" style="text-align: center; padding: 2rem;">No rejected clips found. Complete dataset passed!</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Interactive dashboard generated at: {dashboard_path}")

def main():
    validate_dataset()

# if __name__ == "__main__":
#     main()
