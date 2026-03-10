"""
Analyze Music Soundtrap Pilot WAV files for marine species sound detection.
Generates mel spectrograms, classifies audio content, and produces annotations
about potential marine biological sounds found in each recording.

Uses multiprocessing with max 2 workers for parallel processing.

Usage:
    python3 -u analyze_marine_audio.py
"""

import json
import multiprocessing as mp
import sys
import traceback
from pathlib import Path

import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal as scipy_signal

INPUT_DIR = Path("Music_Soundtrap_Pilot")
OUTPUT_DIR = Path("output")
SPECTROGRAMS_DIR = OUTPUT_DIR / "spectrograms"
ANNOTATIONS_DIR = OUTPUT_DIR / "annotations"
RESULTS_FILE = OUTPUT_DIR / "analysis_results.json"

MAX_WORKERS = 2

# Frequency bands relevant to marine species (Hz)
MARINE_BANDS = {
    "infrasonic_whales": (10, 100),       # Blue/fin whale calls
    "low_freq_fish": (50, 500),           # Fish choruses, drumming
    "mid_freq_dolphins": (500, 5000),     # Dolphin whistles, some whale calls
    "high_freq_clicks": (5000, 24000),    # Echolocation clicks, snapping shrimp
}


def compute_band_energy(S_db, freqs, fmin, fmax):
    """Compute mean energy in a frequency band."""
    band_mask = (freqs >= fmin) & (freqs <= fmax)
    if not band_mask.any():
        return -80.0, np.zeros(S_db.shape[1])
    band_data = S_db[band_mask, :]
    mean_energy = float(np.mean(band_data))
    temporal_profile = band_data.mean(axis=0)
    return mean_energy, temporal_profile


def detect_transient_events(temporal_profile, threshold_std=2.5):
    """Detect transient sound events (clicks, pulses) above background."""
    if len(temporal_profile) < 10:
        return 0, []
    median_val = np.median(temporal_profile)
    std_val = np.std(temporal_profile)
    if std_val < 0.5:
        return 0, []
    threshold = median_val + threshold_std * std_val
    above = temporal_profile > threshold
    # Count event groups (consecutive frames above threshold)
    events = []
    in_event = False
    start = 0
    for i, v in enumerate(above):
        if v and not in_event:
            in_event = True
            start = i
        elif not v and in_event:
            in_event = False
            events.append((start, i))
    if in_event:
        events.append((start, len(above)))
    return len(events), events


def detect_tonal_signals(S_db, freqs, sr, fmin=500, fmax=15000):
    """Detect sustained tonal signals (whistles, calls) via spectral flatness."""
    band_mask = (freqs >= fmin) & (freqs <= fmax)
    if not band_mask.any():
        return False, 0.0
    band_data = S_db[band_mask, :]
    # Convert back to linear for flatness calculation
    band_linear = librosa.db_to_power(band_data)
    # Spectral flatness per frame: geometric mean / arithmetic mean
    geo_mean = np.exp(np.mean(np.log(band_linear + 1e-10), axis=0))
    arith_mean = np.mean(band_linear, axis=0)
    flatness = geo_mean / (arith_mean + 1e-10)
    # Low flatness = tonal content (not flat/noisy)
    tonal_frames = np.sum(flatness < 0.1)
    tonal_ratio = tonal_frames / len(flatness) if len(flatness) > 0 else 0
    return tonal_ratio > 0.05, float(tonal_ratio)


def analyze_single_file(wav_path):
    """Analyze a single WAV file for marine biological sounds.
    Returns (filename, result_dict) or (filename, error_dict)."""
    fname = wav_path.name
    try:
        # Load audio
        y, sr = librosa.load(str(wav_path), sr=None)
        duration = len(y) / sr

        # Basic stats
        rms = float(np.sqrt(np.mean(y ** 2)))
        peak = float(np.max(np.abs(y)))

        if rms < 1e-7:
            return fname, {
                "filename": fname,
                "duration_s": duration,
                "sample_rate": sr,
                "status": "silent",
                "has_biological_interest": False,
                "annotations": ["File is silent (RMS ≈ 0)"],
            }

        # Compute mel spectrogram
        n_fft = 2048
        hop_length = 512
        S = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=128, n_fft=n_fft,
            hop_length=hop_length, fmax=sr / 2
        )
        S_db = librosa.power_to_db(S, ref=np.max)

        # Get mel frequency centers
        mel_freqs = librosa.mel_frequencies(n_mels=128, fmax=sr / 2)

        # Analyze each marine-relevant frequency band
        band_results = {}
        annotations = []

        for band_name, (fmin, fmax) in MARINE_BANDS.items():
            actual_fmax = min(fmax, sr / 2)
            if fmin >= sr / 2:
                band_results[band_name] = {"energy_db": -80, "events": 0, "note": "above Nyquist"}
                continue

            energy, temporal = compute_band_energy(S_db, mel_freqs, fmin, actual_fmax)
            n_events, event_spans = detect_transient_events(temporal)
            temporal_std = float(np.std(temporal))

            band_results[band_name] = {
                "freq_range_hz": [fmin, actual_fmax],
                "mean_energy_db": round(energy, 2),
                "temporal_std": round(temporal_std, 2),
                "transient_events": n_events,
            }

            # Annotate findings per band
            if band_name == "infrasonic_whales" and energy > -50 and temporal_std > 3:
                annotations.append(f"Low-frequency energy ({fmin}-{actual_fmax}Hz) with temporal variation — possible baleen whale vocalizations or vessel noise")
            if band_name == "low_freq_fish" and energy > -45 and n_events > 3:
                annotations.append(f"Pulsed low-frequency events ({fmin}-{actual_fmax}Hz, {n_events} events) — possible fish chorus or drumming")
            if band_name == "mid_freq_dolphins" and energy > -45 and temporal_std > 4:
                annotations.append(f"Mid-frequency activity ({fmin}-{actual_fmax}Hz) with high variation — possible dolphin whistles or marine mammal calls")
            if band_name == "high_freq_clicks" and n_events > 5:
                annotations.append(f"High-frequency transients ({fmin}-{actual_fmax}Hz, {n_events} events) — possible echolocation clicks or snapping shrimp")

        # Detect tonal signals (whistles)
        has_tonal, tonal_ratio = detect_tonal_signals(S_db, mel_freqs, sr)
        if has_tonal:
            annotations.append(f"Tonal signals detected (tonal ratio: {tonal_ratio:.3f}) — possible marine mammal whistles or fish calls")

        # Overall classification
        upper_bands = S_db[20:, :]
        upper_event_ratio = float(np.sum(upper_bands.max(axis=0) > -50) / upper_bands.shape[1]) if upper_bands.shape[1] > 0 else 0
        upper_std = float(np.std(upper_bands.mean(axis=0)))
        has_meaningful = upper_event_ratio > 0.005 or upper_std > 3.0

        # Determine biological interest
        has_bio = len(annotations) > 0

        if not annotations:
            if has_meaningful:
                annotations.append("Audio contains energy but no clear marine biological signatures detected — may contain ambient ocean noise, vessel noise, or weather")
            else:
                annotations.append("Low energy recording — likely ambient background noise or quiet period")

        # Generate spectrogram image
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

        # Main spectrogram
        img = librosa.display.specshow(
            S_db, sr=sr, x_axis="time", y_axis="mel",
            ax=axes[0], hop_length=hop_length
        )
        axes[0].set_title(f"{fname} — {'BIOLOGICAL INTEREST' if has_bio else 'NO BIO SIGNATURES'}", fontsize=12)
        fig.colorbar(img, ax=axes[0], format="%+2.0f dB")

        # Add frequency band overlays
        colors = {'infrasonic_whales': 'red', 'low_freq_fish': 'orange',
                  'mid_freq_dolphins': 'cyan', 'high_freq_clicks': 'lime'}
        for band_name, (fmin, fmax) in MARINE_BANDS.items():
            actual_fmax = min(fmax, sr / 2)
            if fmin < sr / 2:
                axes[0].axhline(y=fmin, color=colors[band_name], alpha=0.4, linewidth=0.8, linestyle='--')
                axes[0].axhline(y=actual_fmax, color=colors[band_name], alpha=0.4, linewidth=0.8, linestyle='--')

        # Temporal energy plot
        times = librosa.frames_to_time(np.arange(S_db.shape[1]), sr=sr, hop_length=hop_length)
        for band_name, (fmin, fmax) in MARINE_BANDS.items():
            actual_fmax = min(fmax, sr / 2)
            if fmin < sr / 2:
                _, temporal = compute_band_energy(S_db, mel_freqs, fmin, actual_fmax)
                axes[1].plot(times[:len(temporal)], temporal, color=colors[band_name],
                           alpha=0.7, linewidth=0.8, label=band_name.replace('_', ' '))

        axes[1].set_xlabel("Time (s)")
        axes[1].set_ylabel("Energy (dB)")
        axes[1].set_title("Band Energy Over Time")
        axes[1].legend(loc='upper right', fontsize=7)
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        spec_path = SPECTROGRAMS_DIR / f"{wav_path.stem}_spectrogram.png"
        fig.savefig(str(spec_path), dpi=120)
        plt.close(fig)

        result = {
            "filename": fname,
            "duration_s": round(duration, 2),
            "sample_rate": sr,
            "bit_depth": 24,
            "rms": round(rms, 8),
            "peak": round(peak, 6),
            "status": "analyzed",
            "has_meaningful_audio": has_meaningful,
            "has_biological_interest": has_bio,
            "upper_event_ratio": round(upper_event_ratio, 4),
            "upper_temporal_std": round(upper_std, 2),
            "tonal_ratio": round(tonal_ratio, 4),
            "band_analysis": band_results,
            "annotations": annotations,
            "spectrogram": str(spec_path.name),
        }

        # Save individual annotation file
        ann_path = ANNOTATIONS_DIR / f"{wav_path.stem}_annotation.json"
        with open(str(ann_path), "w") as f:
            json.dump(result, f, indent=2)

        return fname, result

    except Exception as e:
        tb = traceback.format_exc()
        return fname, {
            "filename": fname,
            "status": "error",
            "error": str(e),
            "traceback": tb,
            "has_biological_interest": False,
            "annotations": [f"Processing error: {e}"],
        }


def main():
    # Setup output dirs
    SPECTROGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Find all WAV files
    wav_files = sorted(INPUT_DIR.glob("*.wav"))
    wav_files = [f for f in wav_files if f.stat().st_size > 1000]

    print(f"Found {len(wav_files)} WAV files in {INPUT_DIR}/")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"Workers: {MAX_WORKERS}")
    print("=" * 70)

    if not wav_files:
        print("No files to process.")
        return

    # Process in parallel with 2 workers
    all_results = {}
    with mp.Pool(processes=MAX_WORKERS) as pool:
        for i, (fname, result) in enumerate(pool.imap_unordered(analyze_single_file, wav_files)):
            all_results[fname] = result
            status = result.get("status", "?")
            bio = "BIO" if result.get("has_biological_interest") else "---"
            n_ann = len(result.get("annotations", []))
            print(f"  [{i+1}/{len(wav_files)}] [{bio}] {fname}: {status}, {n_ann} annotation(s)")
            sys.stdout.flush()

    # Summary
    bio_files = [r for r in all_results.values() if r.get("has_biological_interest")]
    meaningful_files = [r for r in all_results.values() if r.get("has_meaningful_audio")]
    error_files = [r for r in all_results.values() if r.get("status") == "error"]

    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total processed: {len(all_results)}")
    print(f"  With meaningful audio: {len(meaningful_files)}")
    print(f"  With biological interest: {len(bio_files)}")
    print(f"  Errors: {len(error_files)}")

    if bio_files:
        print(f"\n  FILES WITH BIOLOGICAL INTEREST:")
        for r in sorted(bio_files, key=lambda x: x["filename"]):
            print(f"    + {r['filename']}")
            for ann in r["annotations"]:
                print(f"        {ann}")

    # Save consolidated results
    summary = {
        "input_dir": str(INPUT_DIR),
        "total_files": len(all_results),
        "with_meaningful_audio": len(meaningful_files),
        "with_biological_interest": len(bio_files),
        "errors": len(error_files),
        "files": {k: v for k, v in sorted(all_results.items())},
    }
    with open(str(RESULTS_FILE), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results: {RESULTS_FILE}")
    print(f"  Spectrograms: {SPECTROGRAMS_DIR}/")
    print(f"  Annotations: {ANNOTATIONS_DIR}/")


if __name__ == "__main__":
    main()