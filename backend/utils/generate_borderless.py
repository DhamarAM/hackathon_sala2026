"""
Generate borderless mel spectrograms from WAV clips.

Produces clean heatmap PNGs (no axes, no borders, no whitespace)
using librosa mel spectrogram — same method as stage2_cascade.py.

Usage:
    python generate_borderless.py            # Process all clips in outputs/clips/
    python generate_borderless.py <wav_path>  # Process a single file, output PNG to stdout
"""

import sys
import io
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_borderless_mel(wav_path, n_mels=128, n_fft=2048, hop_length=512,
                          figsize=(14, 3), cmap="magma"):
    """Render a borderless mel spectrogram heatmap as PNG bytes."""
    y, sr = sf.read(str(wav_path), dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)

    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels,
                                       n_fft=n_fft, hop_length=hop_length)
    S_db = librosa.power_to_db(S, ref=np.max)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    librosa.display.specshow(S_db, sr=sr, hop_length=hop_length,
                             x_axis=None, y_axis=None, ax=ax, cmap=cmap)
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def main():
    ROOT = Path(__file__).resolve().parent.parent.parent  # hackathon_sala2026/
    CLIPS_DIR = ROOT / "outputs" / "clips"
    OUT_DIR = ROOT / "outputs" / "spectrograms_clean"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Single file mode: output to stdout
    if len(sys.argv) > 1:
        wav_path = Path(sys.argv[1])
        if not wav_path.exists():
            print(f"File not found: {wav_path}", file=sys.stderr)
            sys.exit(1)
        png_bytes = render_borderless_mel(wav_path)
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), 0x8000)
        sys.stdout.buffer.write(png_bytes)
        return

    # Batch mode: process all clips
    wavs = sorted(CLIPS_DIR.glob("*.wav"))
    if not wavs:
        print(f"No WAV files found in {CLIPS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Generating borderless mel spectrograms for {len(wavs)} clips...")
    for i, wav in enumerate(wavs, 1):
        out_path = OUT_DIR / f"{wav.stem}.png"
        if out_path.exists():
            print(f"  [{i}/{len(wavs)}] {wav.stem} — already exists, skipping")
            continue
        print(f"  [{i}/{len(wavs)}] {wav.stem}...", end=" ", flush=True)
        png_bytes = render_borderless_mel(wav)
        out_path.write_bytes(png_bytes)
        print(f"done ({len(png_bytes) / 1024:.0f} KB)")

    print(f"\nAll borderless spectrograms saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
