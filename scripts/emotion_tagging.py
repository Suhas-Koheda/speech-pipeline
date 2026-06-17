"""
Emotion/Style Tagging Pipeline

Applies emotion recognition to audio segments using pre-trained models.

Supported emotions:
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
from pathlib import Path
import numpy as np
import torch
import torchaudio
from transformers import pipeline

# Emotion labels mapping
EMOTION_LABELS = {
    "neutral": "neutral",
    "conversational": "conversational",
    "formal": "formal",
    "excited": "excited",
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "questioning": "questioning",
    "serious": "serious",
}

SAMPLING_RATE = 16000


class EmotionTagger:
    """Speech emotion recognition wrapper."""
    
    def __init__(self, model_name="speechbrain/emotion-recognition-wav2vec2-IEMOCAP"):
        """
        Initialize emotion tagger with pre-trained model.
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Loading emotion model: {model_name}")
        print(f"Using device: {self.device}")
        
        try:
            # Load emotion classification pipeline
            self.classifier = pipeline(
                "audio-classification",
                model=model_name,
                device=self.device if self.device == "cuda" else -1
            )
            print("Emotion model loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load model {model_name}: {e}")
            self.classifier = None
    
    def predict(self, audio_path, top_k=1):
        """
        Predict emotion for audio segment.
        
        Args:
            audio_path: Path to audio file
            top_k: Number of top predictions
        
        Returns:
            Tuple of (emotion_label, confidence)
        """
        if self.classifier is None:
            return "neutral", 0.5  # Default if model not loaded
        
        try:
            # Load audio
            wav, sr = torchaudio.load(audio_path)
            
            # Resample if needed
            if sr != SAMPLING_RATE:
                resampler = torchaudio.transforms.Resample(sr, SAMPLING_RATE)
                wav = resampler(wav)
            
            # Convert to mono
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0)
            
            # Inference
            outputs = self.classifier(wav.numpy(), top_k=top_k)
            
            if isinstance(outputs, list) and len(outputs) > 0:
                # Get top prediction
                emotion = outputs[0]["label"]
                confidence = float(outputs[0]["score"])
            else:
                emotion = "neutral"
                confidence = 0.5
            
            # Map to standardized emotion labels
            emotion = emotion.lower().strip()
            if emotion not in EMOTION_LABELS:
                emotion = "neutral"
            
            return emotion, confidence
        
        except Exception as e:
            print(f"Error predicting emotion for {audio_path}: {e}")
            return "neutral", 0.0
    
    def batch_predict(self, records, audio_dir=None):
        """
        Predict emotions for multiple records.
        
        Args:
            records: List of segment records
            audio_dir: Optional base directory for audio paths
        
        Returns:
            Updated records with emotion field
        """
        total = len(records)
        
        print(f"\n=== Emotion Tagging ===")
        print(f"Processing {total} segments...")
        
        for idx, record in enumerate(records, start=1):
            try:
                audio_path = record.get("segment_path", "")
                
                # Predict emotion
                emotion, confidence = self.predict(audio_path)
                
                record["emotion"] = emotion
                record["emotion_confidence"] = float(confidence)
                
                if idx % 50 == 0 or idx == 1:
                    print(f"[{idx}/{total}] {emotion} ({confidence:.2f})")
            
            except Exception as e:
                print(f"Error processing segment {idx}: {e}")
                record["emotion"] = "neutral"
                record["emotion_confidence"] = 0.0
        
        return records


def tag_emotions(
    input_path="../data/segments_metadata_filtered.jsonl",
    output_path="../data/segments_metadata_emotions.jsonl",
    model_name="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
):
    """
    Apply emotion tagging to filtered segments.
    
    Args:
        input_path: Path to filtered segments metadata
        output_path: Path to save emotions metadata
        model_name: HuggingFace model to use
    """
    # Load records
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
    
    # Initialize emotion tagger
    tagger = EmotionTagger(model_name)
    
    # Batch predict
    records = tagger.batch_predict(records)
    
    # Calculate emotion distribution
    emotion_counts = {}
    for record in records:
        emotion = record.get("emotion", "unknown")
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n=== Emotion Tagging Summary ===")
    print(f"Total segments tagged: {total}")
    print("\nEmotion Distribution:")
    for emotion in sorted(EMOTION_LABELS.keys()):
        count = emotion_counts.get(emotion, 0)
        percentage = 100 * count / total
        print(f"  {emotion:15s}: {count:4d} ({percentage:5.1f}%)")
    
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    tag_emotions()
