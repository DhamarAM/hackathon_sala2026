"""
backend/utils/generate_spectrogram.py — On-the-fly spectrogram generation.

Called by the Vite dev server to generate spectrogram PNGs from WAV files.
Outputs PNG binary to stdout (captured by Node.js execSync).

Usage:
    python generate_spectrogram.py <wav_path> --mode full|bands|clean
"""

import sys
from pathlib import Path

# Add parent dirs to path so we can import acoustic_data
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acoustic_data import load_audio, highpass_filter, render_spectrogram_png, render_spectrogram_bands_png, render_clean_spectrogram_png


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate spectrogram PNG from WAV")
    parser.add_argument("wav_path", type=Path, help="Path to WAV file")
    parser.add_argument("--mode", choices=["full", "bands", "clean"], default="full",
                        help="Spectrogram type: full (single plot), bands (ecological bands), clean (bare heatmap)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Max seconds to process (None = full file)")
    args = parser.parse_args()

    if not args.wav_path.exists():
        print(f"File not found: {args.wav_path}", file=sys.stderr)
        sys.exit(1)

    audio, sr = load_audio(args.wav_path, duration_s=args.duration)
    audio = highpass_filter(audio, sr, cutoff_hz=50)

    title = args.wav_path.stem

    if args.mode == "full":
        png_bytes = render_spectrogram_png(audio, sr, title=title)
    elif args.mode == "bands":
        png_bytes = render_spectrogram_bands_png(audio, sr, title_prefix=f"{title} — ")
    elif args.mode == "clean":
        png_bytes = render_clean_spectrogram_png(audio, sr)

    # Write binary PNG to stdout
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), 0x8000)  # O_BINARY
    sys.stdout.buffer.write(png_bytes)


if __name__ == "__main__":
    main()
