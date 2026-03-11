"""
backend/utils/acoustic_data.py — Marine acoustic data utilities.

Adapted from the hackathon-provided acoustic_data.py helper.
Provides audio loading, spectrogram computation/rendering, timestamp parsing,
and metadata extraction for the SALA 2026 marine bioacoustics platform.

Used by the frontend's on-the-fly processing endpoints.
"""

import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from scipy.signal import butter, sosfilt, spectrogram as sp_spectrogram
except ImportError:
    butter = sosfilt = sp_spectrogram = None


# ============================================================================
# Dataset inventory (3 SoundTrap hydrophone units)
# ============================================================================

UNITS = {
    "5783": {
        "sample_rate": 144_000,
        "pattern": r"^5783\.(\d{12})\.wav$",
        "description": "SoundTrap unit 5783, 144 kHz, 20-min recordings",
    },
    "6478": {
        "sample_rate": 96_000,
        "pattern": r"^6478\.(\d{12})\.wav$",
        "description": "SoundTrap unit 6478, 96 kHz, 10-min recordings",
    },
    "pilot": {
        "sample_rate": 48_000,
        "pattern": r"^(\d{6})_(\d+)\.wav$",
        "description": "Pilot deployment, 48 kHz, ~5-min recordings",
    },
}

_DIR_TO_UNIT = {
    "5783": "5783",
    "6478": "6478",
    "Music_Soundtrap_Pilot": "pilot",
}


# ============================================================================
# Timestamp parsing
# ============================================================================

def parse_soundtrap_timestamp(filename, unit=None):
    """Extract UTC datetime from a SoundTrap WAV filename.

    Supports:
        5783.YYMMDDHHMMSS.wav / 6478.YYMMDDHHMMSS.wav
        YYMMDD_NNNN.wav (Pilot)

    Returns datetime or None.
    """
    name = Path(filename).name

    m = re.match(r"^\d{4}\.(\d{12})\.wav$", name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%y%m%d%H%M%S")
        except ValueError:
            return None

    m = re.match(r"^(\d{6})_(\d+)\.wav$", name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%y%m%d")
        except ValueError:
            return None

    return None


def detect_unit(filename):
    """Detect which hydrophone unit a WAV file belongs to."""
    name = Path(filename).name
    for unit_key, info in UNITS.items():
        if re.match(info["pattern"], name):
            return unit_key
    return None


# ============================================================================
# Dataset discovery
# ============================================================================

def list_recordings(data_dir, unit=None):
    """List all WAV recordings with parsed metadata.

    Returns list of dicts: path, filename, unit, timestamp, sample_rate
    """
    data_dir = Path(data_dir)
    recordings = []

    dirs = _DIR_TO_UNIT.items()
    if unit:
        dirs = [(k, v) for k, v in dirs if v == unit]

    for dirname, unit_key in dirs:
        unit_dir = data_dir / dirname
        if not unit_dir.exists():
            continue

        unit_info = UNITS[unit_key]
        wavs = sorted(p for p in unit_dir.glob("*.wav") if not p.name.startswith("._"))

        for wav_path in wavs:
            ts = parse_soundtrap_timestamp(wav_path.name)
            recordings.append({
                "path": str(wav_path),
                "filename": wav_path.name,
                "unit": unit_key,
                "timestamp": ts.isoformat() if ts else None,
                "sample_rate": unit_info["sample_rate"],
            })

    return recordings


# ============================================================================
# XML metadata
# ============================================================================

def parse_xml_metadata(xml_path):
    """Parse a SoundTrap .log.xml for deployment metadata."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    meta = {}

    for pe in root.findall(".//PROC_EVENT"):
        for child in pe:
            attrs = child.attrib
            if "SamplingStartTimeUTC" in attrs:
                try:
                    meta["start_time"] = datetime.strptime(
                        attrs["SamplingStartTimeUTC"], "%Y-%m-%dT%H:%M:%S"
                    ).isoformat()
                except ValueError:
                    pass
            if "SamplingStopTimeUTC" in attrs:
                try:
                    meta["stop_time"] = datetime.strptime(
                        attrs["SamplingStopTimeUTC"], "%Y-%m-%dT%H:%M:%S"
                    ).isoformat()
                except ValueError:
                    pass
            if "SampleRate" in attrs:
                meta["sample_rate"] = int(attrs["SampleRate"])
            if "Temperature" in attrs:
                meta["temperature_c"] = float(attrs["Temperature"])
            if "BatteryState" in attrs:
                meta["battery_v"] = float(attrs["BatteryState"])
            if "Gain" in attrs:
                meta["gain_db"] = float(attrs["Gain"])

    hw = root.find(".//HARDWARE")
    if hw is not None and "SerialNumber" in hw.attrib:
        meta["hardware_id"] = hw.attrib["SerialNumber"]

    return meta


# ============================================================================
# Audio loading
# ============================================================================

def load_audio(path, duration_s=None, offset_s=0.0, target_sr=None):
    """Load a WAV file as float32 numpy array.

    Returns (audio, sample_rate).
    """
    path = str(path)

    if sf is not None:
        info = sf.info(path)
        sr = info.samplerate
        start_frame = int(offset_s * sr)
        n_frames = int(duration_s * sr) if duration_s is not None else -1
        audio, sr = sf.read(path, start=start_frame, frames=n_frames, dtype="float32")
    else:
        import wave
        with wave.open(path, "rb") as wf:
            sr = wf.getframerate()
            n_channels = wf.getnchannels()
            n_total = wf.getnframes()
            start_frame = int(offset_s * sr)
            if duration_s is not None:
                n_frames = min(int(duration_s * sr), n_total - start_frame)
            else:
                n_frames = n_total - start_frame
            wf.setpos(start_frame)
            raw = wf.readframes(n_frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if target_sr and target_sr != sr:
        try:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
            sr = target_sr
        except ImportError:
            raise ImportError(f"librosa required for resampling ({sr} → {target_sr} Hz)")

    return audio, sr


def highpass_filter(audio, sr, cutoff_hz=50, order=4):
    """Highpass filter to remove DC offset and self-noise below cutoff_hz."""
    if butter is None:
        raise ImportError("scipy is required: pip install scipy")
    sos = butter(order, cutoff_hz, btype="highpass", fs=sr, output="sos")
    return sosfilt(sos, audio).astype(np.float32)


# ============================================================================
# Spectrogram computation
# ============================================================================

def compute_spectrogram(audio, sr, n_fft=2048, hop_length=512, f_min=0, f_max=None):
    """Compute power spectrogram in dB.

    Returns (S_db, freqs, times).
    """
    if sp_spectrogram is None:
        raise ImportError("scipy is required: pip install scipy")

    freqs, times, Sxx = sp_spectrogram(
        audio, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length,
        scaling="spectrum",
    )

    Sxx_db = 10 * np.log10(Sxx + 1e-12)

    f_max = f_max or sr / 2
    freq_mask = (freqs >= f_min) & (freqs <= f_max)

    return Sxx_db[freq_mask, :], freqs[freq_mask], times


# ============================================================================
# Spectrogram rendering (to PNG bytes — for serving via HTTP)
# ============================================================================

def render_spectrogram_png(audio, sr, title=None, f_max=None,
                           n_fft=2048, hop_length=512,
                           figsize=(14, 4), cmap="magma",
                           vmin=None, vmax=None):
    """Render a spectrogram to PNG bytes (in-memory, no file I/O).

    Returns bytes of a PNG image.
    """
    if plt is None:
        raise ImportError("matplotlib is required: pip install matplotlib")

    S_db, freqs, times = compute_spectrogram(
        audio, sr, n_fft=n_fft, hop_length=hop_length, f_max=f_max,
    )

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    im = ax.pcolormesh(times, freqs / 1000, S_db,
                       shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_ylabel("Frequency (kHz)")
    ax.set_xlabel("Time (s)")
    if title:
        ax.set_title(title)
    plt.colorbar(im, ax=ax, label="Power (dB)")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_spectrogram_bands_png(audio, sr, title_prefix="", figsize=(14, 10)):
    """Render 2-3 band spectrograms (LOW/MID/HIGH) to PNG bytes.

    Bands:
      LOW  (50–2000 Hz):  Fish vocalizations, boat noise
      MID  (2–20 kHz):    Snapping shrimp, dolphin whistles
      HIGH (20+ kHz):     Echolocation clicks (only if sr > 48 kHz)

    Returns bytes of a PNG image.
    """
    if plt is None:
        raise ImportError("matplotlib is required: pip install matplotlib")

    nyquist = sr / 2
    bands = [
        ("LOW (50–2000 Hz): fish, boats", 50, 2000, 1024),
        ("MID (2–20 kHz): shrimp, dolphin whistles", 2000, 20000, 2048),
    ]
    if nyquist > 24000:
        bands.append(
            (f"HIGH (20–{nyquist/1000:.0f} kHz): echolocation", 20000, nyquist, 4096)
        )

    fig, axes = plt.subplots(len(bands), 1, figsize=figsize)
    if len(bands) == 1:
        axes = [axes]

    for ax, (label, f_min, f_max_band, nfft) in zip(axes, bands):
        f_max_band = min(f_max_band, nyquist)
        S_db, freqs, times = compute_spectrogram(
            audio, sr, n_fft=nfft, hop_length=nfft // 4, f_min=f_min, f_max=f_max_band,
        )
        im = ax.pcolormesh(times, freqs / 1000, S_db,
                           shading="auto", cmap="magma")
        ax.set_ylabel("Frequency (kHz)")
        ax.set_xlabel("Time (s)")
        ax.set_title(f"{title_prefix}{label}")
        ax.set_ylim(f_min / 1000, f_max_band / 1000)
        plt.colorbar(im, ax=ax, label="Power (dB)")

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_clean_spectrogram_png(audio, sr, f_max=None, n_fft=2048, hop_length=512,
                                  figsize=(14, 3), cmap="magma", vmin=None, vmax=None):
    """Render a bare spectrogram heatmap (no axes, labels, or colorbar).

    Suitable for synchronized audio playback overlays in the frontend.
    Returns bytes of a PNG image.
    """
    if plt is None:
        raise ImportError("matplotlib is required: pip install matplotlib")

    S_db, freqs, times = compute_spectrogram(
        audio, sr, n_fft=n_fft, hop_length=hop_length, f_max=f_max,
    )

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.pcolormesh(times, freqs / 1000, S_db,
                  shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ============================================================================
# Audio metadata (quick info without loading full waveform)
# ============================================================================

def get_audio_info(path):
    """Get duration, sample_rate, channels for a WAV file without loading it fully."""
    path = str(path)
    if sf is not None:
        info = sf.info(path)
        return {
            "duration_s": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "frames": info.frames,
        }
    else:
        import wave
        with wave.open(path, "rb") as wf:
            sr = wf.getframerate()
            frames = wf.getnframes()
            return {
                "duration_s": frames / sr,
                "sample_rate": sr,
                "channels": wf.getnchannels(),
                "frames": frames,
            }
