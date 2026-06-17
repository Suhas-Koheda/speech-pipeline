"""
Generate HTML Review Application

Reads segments metadata and generates:
- review/data.json (for data compliance)
- review/index.html (self-contained, premium-styled, file:// openable UI)
"""

import json
import os
from pathlib import Path

def generate_app():
    print("=== Generating HTML Review App ===")
    
    # Resolve project root based on script location
    ROOT_DIR = Path(__file__).resolve().parent.parent
    
    # 1. Discover segments metadata file
    metadata_paths = [
        ROOT_DIR / "data" / "segments_metadata_validated.jsonl",
        ROOT_DIR / "data" / "segments_metadata_emotions.jsonl",
        ROOT_DIR / "data" / "segments_metadata_filtered.jsonl",
        ROOT_DIR / "data" / "segments_metadata.jsonl"
    ]
    
    selected_path = None
    records = []
    
    for p in metadata_paths:
        if p.exists():
            selected_path = p
            break
            
    if not selected_path:
        print("Error: No segments metadata file found in data/ directory.")
        print("Please run VAD segment generation and transcription steps first.")
        return
        
    print(f"Loading segments from: {selected_path}")
    with open(selected_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total = len(records)
    print(f"Loaded {total} segments.")
    
    # 2. Create review directory at project root
    review_dir = ROOT_DIR / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Save review/data.json
    data_json_path = review_dir / "data.json"
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Generated data file: {data_json_path}")
    
    # 4. Generate review/index.html (with pre-embedded data to bypass local CORS blocks)
    embedded_data_js = json.dumps(records, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS Dataset Human Review Tool</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --success-hover: #059669;
            --danger: #ef4444;
            --danger-hover: #dc2626;
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
            padding: 24px;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            display: flex;
            justify-content: center;
        }}
        
        .container {{
            width: 100%;
            max-width: 1000px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
        }}
        
        h1 {{
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(to right, #a5b4fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header-actions {{
            display: flex;
            gap: 12px;
            align-items: center;
        }}
        
        /* Filters and Tabs */
        .filters {{
            display: flex;
            background: rgba(255, 255, 255, 0.04);
            padding: 4px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        
        .filter-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 14px;
            font-family: inherit;
            font-size: 0.85rem;
            font-weight: 500;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .filter-btn.active {{
            background: var(--primary);
            color: var(--text-main);
        }}
        
        .btn {{
            padding: 8px 16px;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn-primary {{
            background: var(--primary);
            color: var(--text-main);
        }}
        
        .btn-primary:hover {{
            background: var(--primary-hover);
        }}
        
        /* Dashboard Layout */
        .progress-section {{
            display: flex;
            align-items: center;
            gap: 16px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 18px;
        }}
        
        .progress-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
            min-width: 130px;
        }}
        
        .progress-bar-container {{
            flex-grow: 1;
            height: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(to right, #6366f1, #10b981);
            width: 0%;
            transition: width 0.3s ease;
        }}
        
        .main-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            padding-bottom: 12px;
        }}
        
        .segment-index {{
            font-size: 1.1rem;
            font-weight: 600;
        }}
        
        .status-badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-unreviewed {{
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
        }}
        
        .status-approved {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        
        .status-rejected {{
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        
        /* Grid Split */
        .workspace {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 24px;
        }}
        
        .player-panel {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .audio-wrapper {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        
        audio {{
            width: 100%;
        }}
        
        .autoplay-control {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        
        .transcript-box {{
            background: rgba(99, 102, 241, 0.04);
            border-left: 4px solid var(--primary);
            border-radius: 0 12px 12px 0;
            padding: 16px;
            font-size: 1.1rem;
            line-height: 1.6;
            min-height: 100px;
        }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        
        .meta-item {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .meta-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        
        .meta-value {{
            font-size: 0.95rem;
            font-weight: 600;
        }}
        
        /* Right Annotation Panel */
        .decision-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            border-left: 1px solid rgba(255, 255, 255, 0.04);
            padding-left: 24px;
        }}
        
        .decision-buttons {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        
        .dec-btn {{
            padding: 16px;
            font-size: 1rem;
            border-radius: 12px;
            font-weight: 700;
            border: 2px solid transparent;
        }}
        
        .btn-approve {{
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.3);
            color: #34d399;
        }}
        
        .btn-approve:hover, .btn-approve.active {{
            background: var(--success);
            color: #fff;
            border-color: var(--success);
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
        }}
        
        .btn-reject {{
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.3);
            color: #f87171;
        }}
        
        .btn-reject:hover, .btn-reject.active {{
            background: var(--danger);
            color: #fff;
            border-color: var(--danger);
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
        }}
        
        .input-group {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        select, textarea {{
            background: #161c2d;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            border-radius: 8px;
            padding: 10px;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s ease;
        }}
        
        select:focus, textarea:focus {{
            border-color: var(--primary);
        }}
        
        textarea {{
            resize: vertical;
            min-height: 80px;
        }}
        
        /* Navigation and Footer */
        .footer-nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 16px;
        }}
        
        .nav-buttons {{
            display: flex;
            gap: 12px;
        }}
        
        .keyboard-legend {{
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            gap: 16px;
        }}
        
        .key-pill {{
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 1px 6px;
            font-family: monospace;
            color: var(--text-main);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>TTS Dataset Human Review</h1>
            </div>
            <div class="header-actions">
                <div class="filters">
                    <button class="filter-btn active" id="filter-all" onclick="setFilter('all')">All</button>
                    <button class="filter-btn" id="filter-unreviewed" onclick="setFilter('unreviewed')">Unreviewed</button>
                    <button class="filter-btn" id="filter-approved" onclick="setFilter('approved')">Approved</button>
                    <button class="filter-btn" id="filter-rejected" onclick="setFilter('rejected')">Rejected</button>
                </div>
                <button class="btn btn-primary" onclick="exportCSV()">Export Reviews (CSV)</button>
            </div>
        </header>
        
        <!-- Progress Bar -->
        <div class="progress-section">
            <span class="progress-label" id="progress-text">Progress: 0 / 0</span>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" id="progress-fill"></div>
            </div>
        </div>
        
        <!-- Main Panel -->
        <div class="main-card">
            <div class="card-header">
                <span class="segment-index" id="segment-title">Segment 0 of 0</span>
                <span class="status-badge status-unreviewed" id="status-badge">Unreviewed</span>
            </div>
            
            <div class="workspace">
                <!-- Left Panel -->
                <div class="player-panel">
                    <div class="audio-wrapper">
                        <audio id="audio-player" controls></audio>
                        <div class="autoplay-control">
                            <input type="checkbox" id="autoplay-cb" checked>
                            <label for="autoplay-cb" style="text-transform:none; font-weight:normal; font-size:0.8rem; cursor:pointer;">Autoplay next segment</label>
                        </div>
                    </div>
                    
                    <div class="transcript-box" id="transcript-text">
                        Transcript loading...
                    </div>
                    
                    <div class="meta-grid">
                        <div class="meta-item">
                            <div class="meta-label">Language</div>
                            <div class="meta-value" id="meta-lang">N/A</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Emotion / Style</div>
                            <div class="meta-value" id="meta-emotion">N/A</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Speaker</div>
                            <div class="meta-value" id="meta-speaker">N/A</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Duration</div>
                            <div class="meta-value" id="meta-duration">N/A</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Quality Score</div>
                            <div class="meta-value" id="meta-quality">N/A</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Speaker Purity</div>
                            <div class="meta-value" id="meta-purity">N/A</div>
                        </div>
                    </div>
                </div>
                
                <!-- Right Panel -->
                <div class="decision-panel">
                    <div class="input-group">
                        <label>Review Decision</label>
                        <div class="decision-buttons">
                            <button class="btn dec-btn btn-approve" id="btn-dec-approve" onclick="approveCurrent()">Approve (A)</button>
                            <button class="btn dec-btn btn-reject" id="btn-dec-reject" onclick="rejectCurrent()">Reject (R)</button>
                        </div>
                    </div>
                    
                    <div class="input-group" id="rejection-reason-group" style="display:none;">
                        <label for="rejection-select">Rejection Reason</label>
                        <select id="rejection-select" onchange="onRejectionReasonChange()">
                            <option value="">-- Choose Reason --</option>
                            <option value="background_music">background_music</option>
                            <option value="transcript_error">transcript_error</option>
                            <option value="overlapping_speakers">overlapping_speakers</option>
                            <option value="clipping">clipping</option>
                            <option value="low_volume">low_volume</option>
                            <option value="noise">noise</option>
                            <option value="wrong_emotion">wrong_emotion</option>
                            <option value="other">other</option>
                        </select>
                    </div>
                    
                    <div class="input-group">
                        <label for="notes-textarea">Notes</label>
                        <textarea id="notes-textarea" placeholder="Add optional annotation notes here..." oninput="onNotesChange()"></textarea>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer-nav">
                <div class="keyboard-legend">
                    <span><span class="key-pill">A</span> Approve</span>
                    <span><span class="key-pill">R</span> Reject</span>
                    <span><span class="key-pill">←</span> Prev</span>
                    <span><span class="key-pill">→</span> Next</span>
                </div>
                <div class="nav-buttons">
                    <button class="btn btn-primary" onclick="prevSegment()">Previous</button>
                    <button class="btn btn-primary" onclick="nextSegment()">Next</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Data embedded directly via python generator
        const allSegments = {embedded_data_js};
        
        // App State
        let currentFilter = 'all'; // all, unreviewed, approved, rejected
        let filteredIndices = [];
        let currentIndex = 0; // index in the filtered list
        
        // Decisions cache: segment_path -> {{ approved: boolean, rejection_reason: string, notes: string }}
        let decisions = {{}};
        
        // Load decisions from localStorage
        function loadFromLocalStorage() {{
            const stored = localStorage.getItem('tts_review_decisions');
            if (stored) {{
                try {{
                    decisions = JSON.parse(stored);
                }} catch (e) {{
                    console.error("Failed to parse storage:", e);
                }}
            }}
        }}
        
        // Save decisions to localStorage
        function saveToLocalStorage() {{
            localStorage.setItem('tts_review_decisions', JSON.stringify(decisions));
        }}
        
        // Apply filter to allSegments and compute filtered list
        function updateFilteredList() {{
            filteredIndices = [];
            
            allSegments.forEach((segment, index) => {{
                const path = segment.segment_path;
                const dec = decisions[path];
                
                if (currentFilter === 'all') {{
                    filteredIndices.push(index);
                }} else if (currentFilter === 'unreviewed') {{
                    if (!dec) filteredIndices.push(index);
                }} else if (currentFilter === 'approved') {{
                    if (dec && dec.approved === true) filteredIndices.push(index);
                }} else if (currentFilter === 'rejected') {{
                    if (dec && dec.approved === false) filteredIndices.push(index);
                }}
            }});
            
            // Adjust current index if it goes out of bounds
            if (currentIndex >= filteredIndices.length) {{
                currentIndex = Math.max(0, filteredIndices.length - 1);
            }}
            
            updateProgress();
            updateFilterTabs();
        }}
        
        function updateFilterTabs() {{
            // Count states
            let total = allSegments.length;
            let unreviewed = 0;
            let approved = 0;
            let rejected = 0;
            
            allSegments.forEach(segment => {{
                const dec = decisions[segment.segment_path];
                if (!dec) unreviewed++;
                else if (dec.approved === true) approved++;
                else if (dec.approved === false) rejected++;
            }});
            
            document.getElementById('filter-all').innerText = `All (${{total}})`;
            document.getElementById('filter-unreviewed').innerText = `Unreviewed (${{unreviewed}})`;
            document.getElementById('filter-approved').innerText = `Approved (${{approved}})`;
            document.getElementById('filter-rejected').innerText = `Rejected (${{rejected}})`;
            
            // Active class
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`filter-${{currentFilter}}`).classList.add('active');
        }}
        
        function updateProgress() {{
            let total = allSegments.length;
            let reviewed = 0;
            allSegments.forEach(s => {{
                if (decisions[s.segment_path]) reviewed++;
            }});
            
            document.getElementById('progress-text').innerText = `Reviewed Progress: ${{reviewed}} / ${{total}} (${{Math.round(100*reviewed/total)}}%)`;
            document.getElementById('progress-fill').style.width = `${{100*reviewed/total}}%`;
        }}
        
        function setFilter(filterType) {{
            currentFilter = filterType;
            currentIndex = 0;
            updateFilteredList();
            renderCurrent();
        }}
        
        function renderCurrent() {{
            if (filteredIndices.length === 0) {{
                // Empty view state
                document.getElementById('segment-title').innerText = "No segments match filter";
                document.getElementById('status-badge').innerText = "N/A";
                document.getElementById('status-badge').className = "status-badge status-unreviewed";
                document.getElementById('audio-player').src = "";
                document.getElementById('transcript-text').innerText = "No transcripts to show.";
                document.getElementById('meta-lang').innerText = "N/A";
                document.getElementById('meta-emotion').innerText = "N/A";
                document.getElementById('meta-speaker').innerText = "N/A";
                document.getElementById('meta-duration').innerText = "N/A";
                document.getElementById('meta-quality').innerText = "N/A";
                document.getElementById('meta-purity').innerText = "N/A";
                
                // Clear active decision buttons
                document.getElementById('btn-dec-approve').classList.remove('active');
                document.getElementById('btn-dec-reject').classList.remove('active');
                document.getElementById('rejection-reason-group').style.display = 'none';
                document.getElementById('rejection-select').value = "";
                document.getElementById('notes-textarea').value = "";
                return;
            }}
            
            const originalIndex = filteredIndices[currentIndex];
            const segment = allSegments[originalIndex];
            
            // Set title
            document.getElementById('segment-title').innerText = `Segment ${{currentIndex + 1}} of ${{filteredIndices.length}} (ID: ${{segment.video_id}})`;
            
            // Audio Path configuration
            // Audio path is stored as relative to workspace root (e.g. "../segments/...")
            // If running review app directly from file, index.html is in "review/" directory,
            // so we can resolve the path directly.
            let audioSrc = "../" + segment.segment_path.replace(/^\.\.\//, "");
            
            const player = document.getElementById('audio-player');
            player.src = audioSrc;
            
            // Auto play if checkbox checked
            if (document.getElementById('autoplay-cb').checked) {{
                player.play().catch(e => console.log("Autoplay blocked:", e));
            }}
            
            // Metadata
            document.getElementById('transcript-text').innerText = segment.transcript || "--- (No Transcript) ---";
            document.getElementById('meta-lang').innerText = segment.language || "unknown";
            document.getElementById('meta-emotion').innerText = segment.emotion || "neutral";
            document.getElementById('meta-speaker').innerText = segment.dominant_speaker || segment.speaker_id || "UNKNOWN";
            
            const duration = segment.duration || 0.0;
            document.getElementById('meta-duration').innerText = `${{duration.toFixed(2)}}s`;
            
            const qScore = segment.quality_score !== undefined ? segment.quality_score : 1.0;
            document.getElementById('meta-quality').innerText = qScore.toFixed(2);
            
            const purity = segment.speaker_purity_score !== undefined ? segment.speaker_purity_score : 1.0;
            document.getElementById('meta-purity').innerText = purity.toFixed(2);
            
            // Render Decision
            const dec = decisions[segment.segment_path];
            const badge = document.getElementById('status-badge');
            
            // Reset state
            document.getElementById('btn-dec-approve').classList.remove('active');
            document.getElementById('btn-dec-reject').classList.remove('active');
            document.getElementById('rejection-reason-group').style.display = 'none';
            document.getElementById('rejection-select').value = "";
            document.getElementById('notes-textarea').value = "";
            
            if (!dec) {{
                badge.innerText = "Unreviewed";
                badge.className = "status-badge status-unreviewed";
            }} else {{
                if (dec.approved === true) {{
                    badge.innerText = "Approved";
                    badge.className = "status-badge status-approved";
                    document.getElementById('btn-dec-approve').classList.add('active');
                }} else {{
                    badge.innerText = "Rejected";
                    badge.className = "status-badge status-rejected";
                    document.getElementById('btn-dec-reject').classList.add('active');
                    document.getElementById('rejection-reason-group').style.display = 'block';
                    document.getElementById('rejection-select').value = dec.rejection_reason || "";
                }}
                document.getElementById('notes-textarea').value = dec.notes || "";
            }}
        }}
        
        function approveCurrent() {{
            if (filteredIndices.length === 0) return;
            const originalIndex = filteredIndices[currentIndex];
            const segment = allSegments[originalIndex];
            
            decisions[segment.segment_path] = {{
                approved: true,
                rejection_reason: "",
                notes: document.getElementById('notes-textarea').value
            }};
            
            saveToLocalStorage();
            updateFilteredList();
            renderCurrent();
        }}
        
        function rejectCurrent() {{
            if (filteredIndices.length === 0) return;
            const originalIndex = filteredIndices[currentIndex];
            const segment = allSegments[originalIndex];
            
            decisions[segment.segment_path] = {{
                approved: false,
                rejection_reason: document.getElementById('rejection-select').value,
                notes: document.getElementById('notes-textarea').value
            }};
            
            saveToLocalStorage();
            updateFilteredList();
            renderCurrent();
        }}
        
        function onRejectionReasonChange() {{
            if (filteredIndices.length === 0) return;
            const originalIndex = filteredIndices[currentIndex];
            const segment = allSegments[originalIndex];
            
            if (decisions[segment.segment_path]) {{
                decisions[segment.segment_path].rejection_reason = document.getElementById('rejection-select').value;
                saveToLocalStorage();
            }}
        }}
        
        function onNotesChange() {{
            if (filteredIndices.length === 0) return;
            const originalIndex = filteredIndices[currentIndex];
            const segment = allSegments[originalIndex];
            
            if (decisions[segment.segment_path]) {{
                decisions[segment.segment_path].notes = document.getElementById('notes-textarea').value;
                saveToLocalStorage();
            }}
        }}
        
        function prevSegment() {{
            if (currentIndex > 0) {{
                currentIndex--;
                renderCurrent();
            }}
        }}
        
        function nextSegment() {{
            if (currentIndex < filteredIndices.length - 1) {{
                currentIndex++;
                renderCurrent();
            }}
        }}
        
        // Export to CSV Function
        function exportCSV() {{
            // Columns required: segment_path, approved, rejection_reason, notes
            let csvContent = "segment_path,approved,rejection_reason,notes\\r\\n";
            
            allSegments.forEach(segment => {{
                const path = segment.segment_path;
                const dec = decisions[path];
                
                let approvedStr = "false";
                let reason = "";
                let notes = "";
                
                if (dec) {{
                    approvedStr = dec.approved ? "true" : "false";
                    reason = dec.rejection_reason || "";
                    notes = dec.notes || "";
                }}
                
                // Escape quotes and wrap values
                const escapedPath = `"${{path.replace(/"/g, '""')}}"`;
                const escapedApproved = `"${{approvedStr.replace(/"/g, '""')}}"`;
                const escapedReason = `"${{reason.replace(/"/g, '""')}}"`;
                const escapedNotes = `"${{notes.replace(/"/g, '""')}}"`;
                
                csvContent += `${{escapedPath}},${{escapedApproved}},${{escapedReason}},${{escapedNotes}}\\r\\n`;
            }});
            
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", "review_results.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
        
        // Keyboard shortcuts listener
        document.addEventListener('keydown', (e) => {{
            // Prevent shortcuts triggering when typing in notes textarea
            if (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'SELECT') {{
                return;
            }}
            
            const key = e.key.toLowerCase();
            if (key === 'a') {{
                approveCurrent();
            }} else if (key === 'r') {{
                rejectCurrent();
            }} else if (e.key === 'ArrowLeft') {{
                prevSegment();
                e.preventDefault();
            }} else if (e.key === 'ArrowRight') {{
                nextSegment();
                e.preventDefault();
            }}
        }});
        
        // Initialize
        loadFromLocalStorage();
        updateFilteredList();
        renderCurrent();
    </script>
</body>
</html>
"""
    
    html_path = review_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Generated self-contained HTML Review App at: {html_path}")
    print("\nInstructions:")
    print(f"1. Open the file {html_path.resolve()} directly in Google Chrome or any browser.")
    print("2. Review segments using the interactive UI.")
    print("3. Click 'Export Reviews (CSV)' to download review_results.csv.")
    print("4. Place the downloaded review_results.csv in the data/ directory.")
    print("5. Run: python scripts/apply_review.py to generate final and rejected metadata files.")


def main():
    generate_app()

# if __name__ == "__main__":
#     main()
