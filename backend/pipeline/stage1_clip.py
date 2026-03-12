"""
backend/stage0_clip.py — Stage 0: clips WAVs to segments with activity.

Supports 16-bit and 24-bit PCM WAV. Removes silence before downstream
models process the audio, improving signal-to-noise ratio.

Usage:
    from backend.pipeline.stage1_clip import AudioClipper

    clipper = AudioClipper(source_dir=Path("data/raw"), output_dir=Path("outputs/clips"))
    clip_paths = clipper.run()
"""

import logging
import shutil
import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np

from backend.config import (
    SILENCE_THRESHOLD, CHUNK_FRAMES, PADDING_S,
    MERGE_GAP_S, MIN_SEGMENT_S, MAX_CLIP_S, CLIPS_DIR,
    MULTISPECIES_MIN_S,
)

logger = logging.getLogger(__name__)


class AudioClipper:
    """
    Iterates over a folder of WAVs, detects active segments by RMS
    and writes precise clips to output_dir.

    Supports 16-bit and 24-bit PCM. Processes files of any sample rate.
    """

    def __init__(
        self,
        source_dir: Path,
        output_dir: Path = CLIPS_DIR,
        threshold: float = SILENCE_THRESHOLD,
        chunk_s: float = 1.0,
        padding_s: float = PADDING_S,
        merge_gap_s: float = MERGE_GAP_S,
        min_segment_s: float = MIN_SEGMENT_S,
        clean_output: bool = True,
    ) -> None:
        self.source_dir   = Path(source_dir)
        self.output_dir   = Path(output_dir)
        self.threshold    = threshold
        self.chunk_s      = chunk_s
        self.padding_s    = padding_s
        self.merge_gap_s  = merge_gap_s
        self.min_segment_s = min_segment_s
        self.clean_output = clean_output

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> List[Path]:
        """Processes all WAVs in source_dir. Returns list of written clips."""
        if self.clean_output and self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        wav_files = sorted(self.source_dir.rglob("*.wav"))
        wav_files = [f for f in wav_files if f.stat().st_size > 1000
                     and not f.is_relative_to(self.output_dir)]
        if not wav_files:
            logger.warning("No .wav files found in: %s", self.source_dir)
            return []

        logger.info("Stage 0 — clipping %d file(s) from %s", len(wav_files), self.source_dir)
        all_clips: List[Path] = []
        for wav_path in wav_files:
            try:
                clips = self._clip_file(wav_path)
                all_clips.extend(clips)
                logger.info("  %s → %d clip(s)", wav_path.name, len(clips))
            except Exception as exc:
                logger.error("  SKIP %s: %s", wav_path.name, exc)

        logger.info("Stage 0 done — %d total clip(s) in %s", len(all_clips), self.output_dir)
        return all_clips

    # ── Internal ──────────────────────────────────────────────────────────────

    def _clip_file(self, wav_path: Path) -> List[Path]:
        with wave.open(str(wav_path), "rb") as wf:
            sr         = wf.getframerate()
            n_frames   = wf.getnframes()
            sample_width = wf.getsampwidth()

        chunk_frames = max(1, int(self.chunk_s * sr))
        rms_list     = self._scan_rms(wav_path, chunk_frames, sample_width)
        segments     = self._find_segments(rms_list, n_frames, sr, chunk_frames)

        if not segments:
            logger.debug("  No active segments: %s", wav_path.name)
            return []

        written: List[Path] = []
        # Preserve sub-folder structure under source_dir
        rel = wav_path.relative_to(self.source_dir)
        clip_dir = self.output_dir / rel.parent
        clip_dir.mkdir(parents=True, exist_ok=True)

        with wave.open(str(wav_path), "rb") as src:
            for idx, (start_frame, n_seg_frames) in enumerate(segments, 1):
                clip_name = f"{wav_path.stem}_seg{idx:03d}.wav"
                dst = clip_dir / clip_name
                self._write_clip(src, start_frame, n_seg_frames, dst)
                written.append(dst)

        return written

    def _scan_rms(self, path: Path, chunk_frames: int, sample_width: int) -> List[float]:
        rms_list: List[float] = []
        with wave.open(str(path), "rb") as wf:
            n_channels = wf.getnchannels()
            while True:
                raw = wf.readframes(chunk_frames)
                if not raw:
                    break
                samples = self._decode(raw, sample_width, n_channels)
                rms_list.append(float(np.sqrt(np.mean(samples ** 2))))
        return rms_list

    @staticmethod
    def _decode(raw: bytes, sample_width: int, n_channels: int) -> np.ndarray:
        if sample_width == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        elif sample_width == 3:
            # 24-bit little-endian → int32 with sign extension
            b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            sign = np.where(b[:, 2] >= 128, np.uint8(0xFF), np.uint8(0x00)).reshape(-1, 1)
            i32  = np.concatenate([b, sign], axis=1)
            samples = i32.view(np.int32).astype(np.float32)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width * 8}-bit")
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)
        return samples

    def _find_segments(
        self, rms_list: List[float], total_frames: int, sr: int, chunk_frames: int
    ) -> List[Tuple[int, int]]:
        total_chunks = len(rms_list)
        if not total_chunks:
            return []

        pad     = max(1, round(self.padding_s    * sr / chunk_frames))
        gap     = max(0, round(self.merge_gap_s  * sr / chunk_frames))
        min_len = max(1, round(self.min_segment_s * sr / chunk_frames))

        active = [i for i, r in enumerate(rms_list) if r > self.threshold]
        if not active:
            return []

        # Group into consecutive runs
        runs: List[Tuple[int, int]] = []
        s = e = active[0]
        for i in active[1:]:
            if i == e + 1:
                e = i
            else:
                runs.append((s, e)); s = e = i
        runs.append((s, e))

        # Padding + clamp
        padded = [(max(0, s - pad), min(total_chunks - 1, e + pad)) for s, e in runs]

        # Merge
        merged = [padded[0]]
        for s, e in padded[1:]:
            ms, me = merged[-1]
            if s <= me + gap + 1:
                merged[-1] = (ms, max(me, e))
            else:
                merged.append((s, e))

        # Filter short segments and convert to frames
        segments: List[Tuple[int, int]] = []
        for s, e in merged:
            if (e - s + 1) < min_len:
                continue
            start_frame = s * chunk_frames
            end_frame   = min((e + 1) * chunk_frames, total_frames)
            n            = end_frame - start_frame
            if n > 0:
                segments.append((start_frame, n))

        # Split segments longer than MAX_CLIP_S into sub-clips
        max_frames = int(MAX_CLIP_S * sr)
        split: List[Tuple[int, int]] = []
        for start_frame, n in segments:
            if n <= max_frames:
                split.append((start_frame, n))
            else:
                pos = start_frame
                remaining = n
                while remaining >= int(MIN_SEGMENT_S * sr):
                    chunk = min(max_frames, remaining)
                    split.append((pos, chunk))
                    pos += chunk
                    remaining -= chunk
        return split

    @staticmethod
    def _write_clip(src: wave.Wave_read, start_frame: int, n_frames: int, dst: Path) -> None:
        sr           = src.getframerate()
        n_channels   = src.getnchannels()
        sample_width = src.getsampwidth()

        src.setpos(start_frame)
        raw = src.readframes(n_frames)

        # Pad with zeros if the clip is shorter than the multispecies model minimum
        min_frames = int(MULTISPECIES_MIN_S * sr)
        if n_frames < min_frames:
            pad_frames = min_frames - n_frames
            raw += b'\x00' * (pad_frames * n_channels * sample_width)

        with wave.open(str(dst), "wb") as out:
            out.setnchannels(n_channels)
            out.setsampwidth(sample_width)
            out.setframerate(sr)
            out.writeframes(raw)
