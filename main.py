#!/usr/bin/env python3
"""
Speech Pipeline Orchestrator

This script coordinates the execution of the entire dataset curation pipeline
from reading links.txt to generating the interactive HTML review tool.
"""

import sys
import subprocess
import time
from pathlib import Path

# ANSI coloring helpers
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

PIPELINE_STEPS = [
    {
        "step": 1,
        "name": "Metadata Ingestion & Audio Download",
        "script": "download_audio.py",
        "description": "Reads links.txt, extracts metadata, and downloads full-length WAV audio files."
    },
    {
        "step": 2,
        "name": "Voice Activity Detection (VAD) Segmentation",
        "script": "generate_segments_vad.py",
        "description": "Slices full-length audio tracks into TTS-optimized segments (5.0s - 20.0s)."
    },
    {
        "step": 3,
        "name": "Sarvam ASR & Speaker Diarization",
        "script": "diarize_audio.py",
        "description": "Identifies speaker turn timestamps and transcribes full audio using Sarvam Batch API."
    },
    {
        "step": 4,
        "name": "Speaker Attribution",
        "script": "attribute_speakers.py",
        "description": "Maps the diarized speaker turn timelines onto the sliced VAD segments."
    },
    {
        "step": 5,
        "name": "Transcript Attribution",
        "script": "attribute_transcripts.py",
        "description": "Attributes the generated full transcript chunks to individual VAD segments."
    },
    {
        "step": 6,
        "name": "TTS Quality Filtering",
        "script": "quality_filter.py",
        "description": "Applies rigorous speaker purity, noise, clipping, and confidence filters."
    },
    {
        "step": 7,
        "name": "Emotion & Style Tagging",
        "script": "emotion_tagging.py",
        "description": "Applies LLM emotion / speaking-style classification to the transcripts."
    },
    {
        "step": 8,
        "name": "HTML Review Tool Generation",
        "script": "generate_review_app.py",
        "description": "Creates the self-contained interactive browser-based review dashboard."
    }
]

def run_step(step_idx, step_info):
    name = step_info["name"]
    script = step_info["script"]
    desc = step_info["description"]
    
    print(f"\n{BLUE}{BOLD}=================================================={RESET}")
    print(f"{BLUE}{BOLD}STEP {step_idx}: {name}{RESET}")
    print(f"{YELLOW}Description: {desc}{RESET}")
    print(f"{BLUE}{BOLD}=================================================={RESET}\n")
    
    start_time = time.time()
    
    try:
        # Execute module.main() via python -c to run the commented main block
        module_name = script.replace(".py", "")
        process = subprocess.Popen(
            [sys.executable, "-c", f"import {module_name}; {module_name}.main()"],
            cwd="scripts",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output in real time
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode != 0:
            print(f"\n{RED}{BOLD}✖ Step {step_idx} ({name}) failed with exit code {process.returncode}{RESET}\n")
            return False
            
    except Exception as e:
        print(f"\n{RED}{BOLD}✖ Failed to execute {script}: {e}{RESET}\n")
        return False
        
    elapsed = time.time() - start_time
    print(f"\n{GREEN}{BOLD}✔ Step {step_idx} completed successfully in {elapsed:.1f}s{RESET}\n")
    return True

def print_help():
    print(f"{BOLD}Speech Pipeline Runner CLI{RESET}")
    print("Usage:")
    print("  python3 main.py          - Run the complete pipeline end-to-end")
    print("  python3 main.py --step N - Run only a specific step (1-8)")
    print("  python3 main.py --from N - Run the pipeline starting from step N")
    print("\nAvailable Pipeline Steps:")
    for step in PIPELINE_STEPS:
        print(f"  {step['step']}. {BOLD}{step['name']}{RESET}")
        print(f"     Script: scripts/{step['script']}")
        print(f"     Desc:   {step['description']}")

def main():
    # Parse CLI arguments
    run_all = True
    start_step = 1
    end_step = len(PIPELINE_STEPS)
    
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_help()
        return
        
    if "--step" in args:
        try:
            idx = args.index("--step")
            step_num = int(args[idx + 1])
            if step_num < 1 or step_num > len(PIPELINE_STEPS):
                raise ValueError()
            start_step = step_num
            end_step = step_num
            run_all = False
        except (ValueError, IndexErr):
            print(f"{RED}Error: --step requires a number between 1 and 8.{RESET}")
            return
            
    elif "--from" in args:
        try:
            idx = args.index("--from")
            step_num = int(args[idx + 1])
            if step_num < 1 or step_num > len(PIPELINE_STEPS):
                raise ValueError()
            start_step = step_num
            run_all = False
        except (ValueError, IndexError):
            print(f"{RED}Error: --from requires a number between 1 and 8.{RESET}")
            return

    # Check that script directory exists
    scripts_dir = Path("scripts")
    if not scripts_dir.exists():
        print(f"{RED}Error: 'scripts' folder not found. Please run this from the project root directory.{RESET}")
        return
        
    # Check that links.txt exists if starting from step 1
    if start_step == 1 and not Path("links.txt").exists():
        print(f"{RED}Error: 'links.txt' not found at project root. Please create it and add YouTube URLs first.{RESET}")
        return

    print(f"\n{GREEN}{BOLD}=================================================={RESET}")
    print(f"{GREEN}{BOLD}       STARTING SPEECH PIPELINE CURATION           {RESET}")
    if run_all:
        print(f"{GREEN}Running all steps (1-{len(PIPELINE_STEPS)}){RESET}")
    else:
        print(f"{GREEN}Running steps {start_step} to {end_step}{RESET}")
    print(f"{GREEN}{BOLD}=================================================={RESET}")
    
    global_start_time = time.time()
    
    for step in PIPELINE_STEPS:
        num = step["step"]
        if num < start_step or num > end_step:
            continue
            
        success = run_step(num, step)
        if not success:
            print(f"{RED}{BOLD}Pipeline execution halted at Step {num} due to errors.{RESET}\n")
            sys.exit(1)
            
    total_elapsed = time.time() - global_start_time
    print(f"{GREEN}{BOLD}=================================================={RESET}")
    print(f"{GREEN}{BOLD}🎉 PIPELINE COMPLETED SUCCESSFULLY IN {total_elapsed/60:.1f} MIN{RESET}")
    print(f"{GREEN}{BOLD}=================================================={RESET}\n")
    
    if end_step == len(PIPELINE_STEPS):
        review_html = Path("review/index.html").resolve()
        print(f"{BOLD}Next Steps for Dataset Curation:{RESET}")
        print(f"1. Open the review tool directly in Chrome:")
        print(f"   {review_html}")
        print(f"2. Audit the segments (Approve/Reject), and click 'Export Reviews (CSV)'.")
        print(f"3. Place the downloaded 'review_results.csv' in the project 'data/' directory.")
        print(f"4. Compile the final approved dataset by running:")
        print(f"   python3 scripts/apply_review.py\n")

if __name__ == "__main__":
    main()
