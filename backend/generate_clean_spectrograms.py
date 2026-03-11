"""
Generate clean spectrogram images from existing composite spectrograms.

Detects the matplotlib axes frame per-image using the gray(212)/black(0)
border pattern and crops to the inner heatmap content, removing titles,
axis tick labels, colorbars, and subsidiary charts.

The resulting images have the time axis mapped edge-to-edge,
suitable for synchronized audio playback overlays in the frontend.

Usage:
    python generate_clean_spectrograms.py
"""

from pathlib import Path
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent

BASIC_SPEC_DIR = REPO_ROOT / "output" / "spectrograms"
CASCADE_SPEC_DIR = REPO_ROOT / "output2" / "spectrograms"
CLEAN_DIR = REPO_ROOT / "output" / "spectrograms_clean"

# Expected image sizes
BASIC_SIZE = (1680, 960)
CASCADE_SIZE = (1920, 1680)


def _is_gray_border(pixel, tol=15):
    """Check if pixel matches matplotlib's gray axes border (~212,212,212)."""
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    return abs(r - 212) < tol and abs(g - 212) < tol and abs(b - 212) < tol


def _is_black(pixel, tol=5):
    """Check if pixel is black (axes line)."""
    return int(pixel[0]) < tol and int(pixel[1]) < tol and int(pixel[2]) < tol


def find_heatmap_box(arr, max_bottom_y):
    """Find the inner heatmap content area of the top subplot.

    Matplotlib axes have a consistent border pattern:
        white → gray(212) → black(0) → heatmap content
    We scan for this pattern on each edge to find the content boundary.

    Returns (left, top, right, bottom) — the crop box for just the heatmap.
    """
    h, w = arr.shape[:2]

    # Use a scan row at ~40% of the expected spectrogram height
    scan_y = max_bottom_y * 2 // 5

    # --- LEFT boundary ---
    # Scan from left: find gray→black→color transition
    left = 0
    for x in range(w // 3):
        if _is_gray_border(arr[scan_y, x]):
            # Next pixel should be black, then heatmap
            if x + 2 < w and _is_black(arr[scan_y, x + 1]):
                left = x + 2  # First heatmap pixel
                break

    # --- RIGHT boundary ---
    # Scan from right: find gray→black transitions. The first one from the right
    # may be the colorbar's outer frame (narrow ~32px strip). Skip it and find
    # the heatmap's actual right edge.
    right = w
    x = w - 1
    while x > w // 2:
        if _is_gray_border(arr[scan_y, x]) and x - 1 > 0 and _is_black(arr[scan_y, x - 1]):
            # Found a gray→black boundary. Check if content to the left is narrow (colorbar).
            content_start = x - 2
            while content_start > w // 2 and not _is_black(arr[scan_y, content_start]):
                content_start -= 1
            content_width = (x - 2) - content_start
            if content_width < 80:
                # Narrow strip — this is the colorbar. Skip past it.
                x = content_start - 1
                continue
            else:
                right = x - 1
                break
        x -= 1

    # --- TOP boundary ---
    # Scan downward at horizontal center of the heatmap
    mid_x = (left + right) // 2
    top = 0
    # We need to find the LAST gray→black transition going down (skip title lines)
    last_transition_y = 0
    for y in range(max_bottom_y // 2):
        if _is_gray_border(arr[y, mid_x]):
            if y + 2 < h and _is_black(arr[y + 1, mid_x]):
                last_transition_y = y + 2
    top = last_transition_y if last_transition_y > 0 else 0

    # --- BOTTOM boundary ---
    # Scan upward from max expected position
    bottom = max_bottom_y
    for y in range(max_bottom_y, max(0, max_bottom_y - 150), -1):
        if _is_gray_border(arr[y, mid_x]):
            if y - 1 >= 0 and _is_black(arr[y - 1, mid_x]):
                bottom = y - 1  # black line; heatmap ends at y-2+1 = y-1
                break

    return left, top, right, bottom


def crop_spectrograms(src_dir, expected_size, max_bottom_y, suffix):
    """Crop all spectrogram PNGs in src_dir, extracting just the heatmap."""
    if not src_dir.exists():
        print(f"  Skipping {src_dir} (not found)")
        return 0

    exp_w, exp_h = expected_size
    count = 0
    for png_file in sorted(src_dir.glob("*.png")):
        try:
            img = Image.open(png_file)
            w, h = img.size
            if w != exp_w or h != exp_h:
                print(f"  SKIP {png_file.name} — unexpected size {w}x{h}")
                continue

            arr = np.array(img)
            left, top, right, bottom = find_heatmap_box(arr, max_bottom_y)

            if right <= left or bottom <= top:
                print(f"  SKIP {png_file.name} — invalid box ({left},{top},{right},{bottom})")
                continue

            cropped = img.crop((left, top, right, bottom))

            stem = png_file.stem
            out_path = CLEAN_DIR / f"{stem}_clean.png"
            cropped.save(out_path, optimize=True)
            count += 1
        except Exception as e:
            print(f"  ERROR {png_file.name}: {e}")

    return count


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {CLEAN_DIR}")
    print()

    # Basic: 2 panels [3:1], top spectrogram ends around y=607
    print("Cropping basic spectrograms...")
    n1 = crop_spectrograms(BASIC_SPEC_DIR, BASIC_SIZE, max_bottom_y=620, suffix="spectrogram")
    print(f"  {n1} files processed")

    # Cascade: 4 panels [3:1:1:1], top spectrogram ends around y=688
    print("Cropping cascade spectrograms...")
    n2 = crop_spectrograms(CASCADE_SPEC_DIR, CASCADE_SIZE, max_bottom_y=700, suffix="cascade")
    print(f"  {n2} files processed")

    print(f"\nDone. {n1 + n2} clean spectrograms in {CLEAN_DIR}")


if __name__ == "__main__":
    main()
