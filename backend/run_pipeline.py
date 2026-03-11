"""
run_pipeline.py — Orchestrate the Dragon Ocean Analyzer 3-stage pipeline.

Usage:
    python run_pipeline.py [--input-dir PATH] [--skip-stage1] [--skip-stage2] [--skip-stage3]

Stages:
    1. analyze_marine_audio.py   → Band analysis + spectrograms  (output/)
    2. cascade_classifier.py     → YAMNet + Multispecies + Humpback (output2/)
    3. rank_biological_importance.py → 7-dim scoring             (output2/)

Post-processing:
    generate_clean_spectrograms.py → Crop heatmaps for frontend audio overlay
"""

import argparse
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = BACKEND_DIR / "pipeline"


def run_script(script_name, label):
    """Run a pipeline script and check for errors."""
    script_path = PIPELINE_DIR / script_name
    if not script_path.exists():
        print(f"  SKIP: {script_path} not found")
        return False
    print(f"\n{'='*60}")
    print(f"  Stage: {label}")
    print(f"  Script: {script_path.name}")
    print(f"{'='*60}\n")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BACKEND_DIR),
    )
    if result.returncode != 0:
        print(f"\n  ERROR: {label} failed (exit code {result.returncode})")
        return False
    print(f"\n  OK: {label} completed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Dragon Ocean Analyzer Pipeline")
    parser.add_argument("--skip-stage1", action="store_true", help="Skip band analysis")
    parser.add_argument("--skip-stage2", action="store_true", help="Skip cascade classifier")
    parser.add_argument("--skip-stage3", action="store_true", help="Skip ranking")
    parser.add_argument("--skip-clean", action="store_true", help="Skip clean spectrogram generation")
    args = parser.parse_args()

    print("Dragon Ocean Analyzer Pipeline")
    print(f"Backend: {BACKEND_DIR}\n")

    if not args.skip_stage1:
        run_script("analyze_marine_audio.py", "Band Analysis + Spectrograms")

    if not args.skip_stage2:
        run_script("cascade_classifier.py", "Cascade Classifier (YAMNet → Multispecies → Humpback)")

    if not args.skip_stage3:
        run_script("rank_biological_importance.py", "Biological Importance Ranking")

    if not args.skip_clean:
        clean_script = BACKEND_DIR / "generate_clean_spectrograms.py"
        if clean_script.exists():
            print(f"\n{'='*60}")
            print(f"  Post-processing: Clean Spectrograms")
            print(f"{'='*60}\n")
            subprocess.run([sys.executable, str(clean_script)], cwd=str(BACKEND_DIR))

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
