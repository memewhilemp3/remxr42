"""
Circular Spectrogram & Vinyl Synthesis Engine
Provides:
1. Bidirectional transformations:
   Audio <--> Linear Spectrogram <--> Circular Polar Vinyl Disc
2. Photorealistic Vinyl Record Generation with:
   - Polar time-frequency spectrogram mapping
   - Concentric micro-groove texture
   - Anisotropic specular sheen reflections
   - Center spindle hole & 8-bit Kirby Pinball label art
3. Griffin-Lim iterative phase retrieval for audio reconstruction from vinyl spectrograms.
4. Audio source streaming (YouTube via yt-dlp + PyAV, URLs, local files).
"""

import os
import io
import re
import urllib.request
import numpy as np
import scipy.signal as sig
from scipy.spatial import cKDTree
import scipy.ndimage as ndi
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

# ---------------------------------------------------------------------------
# COLORMAP & INVERSION DEFINITIONS
# ---------------------------------------------------------------------------
SOX_HEX_PALETTE = [
    (0.00, "#000000"),
    (0.12, "#000080"),
    (0.25, "#0000ff"),
    (0.38, "#0080ff"),
    (0.50, "#00ffff"),
    (0.62, "#00ff80"),
    (0.75, "#ffff00"),
    (0.88, "#ff8000"),
    (1.00, "#ffffff")
]

KIRBY_PINBALL_PALETTE = [
    (44, 24, 52),     # #2c1834 Deep plum / vinyl black
    (196, 59, 120),   # #c43b78 Kirby magenta
    (248, 140, 176),  # #f88cb0 Kirby pastel pink
    (255, 244, 212)   # #fff4d4 Dreamland cream
]

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def build_sox_colormap(n_colors=256):
    ctrl_pts = [(pos, hex_to_rgb(c)) for pos, c in SOX_HEX_PALETTE]
    ctrl_pts.sort(key=lambda x: x[0])
    cmap = np.zeros((n_colors, 3), dtype=np.uint8)
    for i in range(n_colors):
        t = i / (n_colors - 1)
        if t <= ctrl_pts[0][0]:
            cmap[i] = ctrl_pts[0][1]
        elif t >= ctrl_pts[-1][0]:
            cmap[i] = ctrl_pts[-1][1]
        else:
            for j in range(len(ctrl_pts) - 1):
                t0, c0 = ctrl_pts[j]
                t1, c1 = ctrl_pts[j+1]
                if t0 <= t <= t1:
                    alpha = (t - t0) / (t1 - t0) if t1 > t0 else 0
                    cmap[i] = [
                        int(c0[k] + alpha * (c1[k] - c0[k]))
                        for k in range(3)
                    ]
                    break
    return cmap

GLOBAL_SOX_CMAP = build_sox_colormap(256)
GLOBAL_SOX_TREE = cKDTree(GLOBAL_SOX_CMAP.astype(float))


# ---------------------------------------------------------------------------
# AUDIO <--> LINEAR SPECTROGRAM
# ---------------------------------------------------------------------------
def compute_stft_magnitude(audio, sr=44100, n_fft=1024, hop_length=256):
    """Computes STFT magnitude matrix from audio numpy array."""
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.astype(np.float32)
    f, t, Zxx = sig.stft(audio, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length, window='hann')
    mag = np.abs(Zxx)
    return mag, f, t

def magnitude_to_db(mag, top_db=96.0):
    """Converts linear magnitude to decibels clamped to top_db dynamic range."""
    eps = 1e-6
    mag_max = np.max(mag) if np.max(mag) > 0 else 1.0
    mag_db = 20.0 * np.log10(np.maximum(mag / mag_max, eps))
    mag_db = np.clip(mag_db, -top_db, 0.0)
    return mag_db

def db_to_colored_image(mag_db, colormap="sox", top_db=96.0):
    """Converts a 2D matrix of decibels to an RGB PIL Image."""
    norm = (mag_db + top_db) / top_db  # 0.0 to 1.0
    norm = np.clip(norm, 0.0, 1.0)
    norm = np.flipud(norm)  # High frequencies on top for standard display
    idx = (norm * 255).astype(np.uint8)

    if colormap == "sox":
        rgb = GLOBAL_SOX_CMAP[idx]
    else:
        # Plasma-like purple to yellow
        r = np.clip(norm * 2.2 - 0.2, 0, 1)
        g = np.clip(norm * 1.5 - 0.5, 0, 1)
        b = np.clip(1.0 - norm * 1.2, 0, 1)
        rgb = (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)
    return Image.fromarray(rgb, mode='RGB')


# ---------------------------------------------------------------------------
# POLAR (CIRCULAR VINYL) FORWARD & INVERSE TRANSFORMATIONS
# ---------------------------------------------------------------------------
def linear_to_circular_polar(img_linear, size=600, r_inner_ratio=0.30, r_outer_ratio=0.48):
    """
    Transforms a rectangular linear spectrogram (W=time, H=freq) into a circular polar disc.
    Time wraps clockwise from 12 o'clock around 360 degrees.
    Frequency maps from r_inner (low freq) to r_outer (high freq).
    Uses high-speed vectorized NumPy + Scipy map_coordinates interpolation.
    """
    arr = np.array(img_linear)
    h_lin, w_lin = arr.shape[:2]
    
    # Target grid
    cx, cy = size / 2.0, size / 2.0
    r_inner = size * r_inner_ratio
    r_outer = size * r_outer_ratio

    y_grid, x_grid = np.mgrid[0:size, 0:size]
    dx = x_grid - cx
    dy = y_grid - cy
    dist = np.sqrt(dx**2 + dy**2)

    # Angle clockwise starting from top (-pi/2)
    angle = np.arctan2(dy, dx) + np.pi / 2.0
    angle = np.mod(angle, 2.0 * np.pi)

    # Normalized coordinates
    u = angle / (2.0 * np.pi)  # 0 to 1 (Time)
    v = (dist - r_inner) / (r_outer - r_inner)  # 0 to 1 (Freq: low -> high)

    # Mask of active vinyl groove area
    active_mask = (dist >= r_inner) & (dist <= r_outer)

    # Map to linear image indices (note: arr rows: 0 is high freq, h_lin-1 is low freq or vice versa)
    # In arr (standard flipped), row 0 is high freq, row h_lin-1 is low freq
    # Here v=0 corresponds to low freq (row h_lin-1), v=1 is high freq (row 0)
    mapped_y = (1.0 - v) * (h_lin - 1)
    mapped_x = u * (w_lin - 1)

    coords = np.array([mapped_y, mapped_x])

    out_channels = []
    num_channels = arr.shape[2] if arr.ndim == 3 else 1
    for ch in range(num_channels):
        src = arr[:, :, ch] if arr.ndim == 3 else arr
        interpolated = ndi.map_coordinates(src, coords, order=1, mode='wrap')
        interpolated = np.where(active_mask, interpolated, 0)
        out_channels.append(interpolated.astype(np.uint8))

    if num_channels == 3:
        out_arr = np.stack(out_channels, axis=-1)
    else:
        out_arr = out_channels[0]

    return Image.fromarray(out_arr), active_mask, (cx, cy, r_inner, r_outer)


def circular_polar_to_linear(img_circular, out_w=800, out_h=513, r_inner_ratio=0.30, r_outer_ratio=0.48):
    """
    Unwraps a circular vinyl spectrogram disc back into a rectangular linear spectrogram (W, H).
    Returns PIL Image of reconstructed rectangular spectrogram.
    """
    arr = np.array(img_circular)
    size = arr.shape[0]
    cx, cy = size / 2.0, size / 2.0
    r_inner = size * r_inner_ratio
    r_outer = size * r_outer_ratio

    # Linear grid: x is time (0..out_w-1), y is freq (0..out_h-1, 0=high freq, out_h-1=low freq)
    v_norm, u_norm = np.mgrid[0:out_h, 0:out_w]
    u = u_norm / (out_w - 1)  # 0 to 1
    # v=0 is high freq (r_outer), v=1 is low freq (r_inner)
    v_freq = 1.0 - (v_norm / (out_h - 1))  # 0 to 1

    r = r_inner + v_freq * (r_outer - r_inner)
    theta = u * 2.0 * np.pi - np.pi / 2.0  # Counter-clockwise offset back to image space

    mapped_x = cx + r * np.cos(theta)
    mapped_y = cy + r * np.sin(theta)

    coords = np.array([mapped_y, mapped_x])

    out_channels = []
    num_channels = arr.shape[2] if arr.ndim == 3 else 1
    for ch in range(num_channels):
        src = arr[:, :, ch] if arr.ndim == 3 else arr
        unwrapped = ndi.map_coordinates(src, coords, order=1, mode='nearest')
        out_channels.append(unwrapped.astype(np.uint8))

    if num_channels == 3:
        out_arr = np.stack(out_channels, axis=-1)
    else:
        out_arr = out_channels[0]

    return Image.fromarray(out_arr)


# ---------------------------------------------------------------------------
# PHOTOREALISTIC VINYL RECORD COMPOSITING
# ---------------------------------------------------------------------------
def composite_vinyl_record(polar_spec_img, center_art_img=None, size=600, r_inner_ratio=0.30, r_outer_ratio=0.48):
    """
    Composites the circular spectrogram into a realistic physical vinyl record:
    - Deep vinyl black outer lead-in and lead-out dead wax
    - Micro-groove circular spiral ridges
    - Anisotropic vinyl specular reflections
    - Center label with Kirby 8-bit art or track art
    - Center spindle hole with brass grommet
    """
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx, cy = size / 2.0, size / 2.0
    r_disc = size * 0.495
    r_outer = size * r_outer_ratio
    r_inner = size * r_inner_ratio
    r_label = size * 0.28
    r_spindle = size * 0.025

    # 1. Base Vinyl Disc Body (Dark sheen with subtle outer rim)
    draw = ImageDraw.Draw(disc)
    draw.ellipse([cx - r_disc, cy - r_disc, cx + r_disc, cy + r_disc], fill=(18, 16, 22, 255), outline=(45, 42, 50, 255), width=2)

    # 2. Draw Dead Wax / Run-out groove area
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(12, 10, 15, 255))
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=(14, 12, 18, 255))

    # 3. Micro-groove & Specular Texture Shader (NumPy vectorized)
    y_grid, x_grid = np.mgrid[0:size, 0:size]
    dx = x_grid - cx
    dy = y_grid - cy
    dist = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)

    # Concentric micro-groove modulation
    groove_mod = 0.82 + 0.18 * np.sin(dist * 1.5)
    
    # Anisotropic specular butterfly sheen (two reflection flares across the vinyl)
    sheen = np.abs(np.cos(angle - 0.7)) ** 12 * 0.28 + np.abs(np.cos(angle + 0.9)) ** 12 * 0.18

    # Blend Polar Spectrogram with Vinyl Grooves
    spec_rgb = np.array(polar_spec_img.convert("RGB")).astype(float)
    spec_mask = (dist >= r_inner) & (dist <= r_outer)

    # Apply groove modulation and sheen to spectrogram
    groove_spec = spec_rgb * groove_mod[:, :, None] * (1.0 + sheen[:, :, None])
    groove_spec = np.clip(groove_spec, 0, 255).astype(np.uint8)

    # Outside active spectrogram, add subtle vinyl groove sheen
    idle_mask = (dist > r_label) & (dist < r_disc) & (~spec_mask)
    vinyl_idle = np.zeros_like(spec_rgb)
    base_idle = (20 * groove_mod + sheen * 60).clip(0, 80)
    vinyl_idle[:, :, 0] = base_idle * 0.9
    vinyl_idle[:, :, 1] = base_idle * 0.8
    vinyl_idle[:, :, 2] = base_idle * 1.1

    final_rgb = np.where(spec_mask[:, :, None], groove_spec, vinyl_idle)
    alpha_mask = np.where(dist <= r_disc, 255, 0).astype(np.uint8)

    rgba_arr = np.clip(np.dstack([final_rgb, alpha_mask]), 0, 255).astype(np.uint8)
    vinyl_layer = Image.fromarray(rgba_arr, mode="RGBA")
    disc.alpha_composite(vinyl_layer)

    # 4. Center Label Area
    draw = ImageDraw.Draw(disc)
    # Paper label background
    draw.ellipse([cx - r_label, cy - r_label, cx + r_label, cy + r_label], fill=(240, 230, 215, 255), outline=(60, 50, 70, 255), width=2)

    # If center art provided, circular crop and paste
    if center_art_img is not None:
        art_size = int(r_label * 1.85)
        art_resized = center_art_img.resize((art_size, art_size), Image.Resampling.LANCZOS)
        # Circular mask for center art
        mask = Image.new("L", (art_size, art_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse([0, 0, art_size, art_size], fill=255)
        disc.paste(art_resized, (int(cx - art_size / 2), int(cy - art_size / 2)), mask)

    # 5. Spindle Hole & Center Brass Grommet
    draw = ImageDraw.Draw(disc)
    draw.ellipse([cx - r_spindle - 2, cy - r_spindle - 2, cx + r_spindle + 2, cy + r_spindle + 2], outline=(180, 160, 110, 255), width=2)
    draw.ellipse([cx - r_spindle, cy - r_spindle, cx + r_spindle, cy + r_spindle], fill=(0, 0, 0, 255))

    return disc


# ---------------------------------------------------------------------------
# GRIFFIN-LIM PHASE RETRIEVAL & CONVERSION PIPELINE
# ---------------------------------------------------------------------------
def griffin_lim(magnitude, n_iter=32, hop_length=256, n_fft=1024):
    """
    Griffin-Lim phase retrieval: estimates time-domain audio from magnitude STFT matrix.
    """
    angles = np.exp(2j * np.pi * np.random.rand(*magnitude.shape))
    stft_matrix = magnitude * angles

    for _ in range(n_iter):
        _, audio = sig.istft(stft_matrix, nperseg=n_fft, noverlap=n_fft - hop_length, window='hann')
        _, _, stft_matrix = sig.stft(audio, nperseg=n_fft, noverlap=n_fft - hop_length, window='hann')
        # Preserve target magnitude while updating phase
        stft_matrix = magnitude * np.exp(1j * np.angle(stft_matrix))

    _, audio = sig.istft(stft_matrix, nperseg=n_fft, noverlap=n_fft - hop_length, window='hann')
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    return audio.astype(np.float32)


def audio_to_circular_spectrogram(audio_data, size=600, colormap="sox", top_db=96.0, center_art=None):
    """
    Full pipeline: Audio (samples, sr) -> STFT -> Polar warping -> Realistic Vinyl Composite.
    Returns: PIL Image (RGBA) of the vinyl record with circular spectrogram.
    """
    if isinstance(audio_data, tuple):
        audio, sr = audio_data
    else:
        audio, sr = audio_data, 44100

    mag, _, _ = compute_stft_magnitude(audio, sr=sr, n_fft=1024, hop_length=256)
    mag_db = magnitude_to_db(mag, top_db=top_db)
    lin_img = db_to_colored_image(mag_db, colormap=colormap, top_db=top_db)

    polar_img, _, _ = linear_to_circular_polar(lin_img, size=size)
    vinyl_disc = composite_vinyl_record(polar_img, center_art_img=center_art, size=size)
    return vinyl_disc


def circular_spectrogram_to_audio(circular_img, sample_rate=22050, n_iter=24, target_duration_sec=8.0):
    """
    Full pipeline: Circular Vinyl Spectrogram Image -> Polar Unwarp -> Colormap Inversion -> Griffin-Lim -> Audio (samples, sr).
    """
    if isinstance(circular_img, str):
        if circular_img.startswith("http://") or circular_img.startswith("https://"):
            req = urllib.request.Request(circular_img, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                circular_img = Image.open(io.BytesIO(resp.read()))
        else:
            circular_img = Image.open(circular_img)

    # 1. Unwarp circular disc to linear spectrogram
    linear_img = circular_polar_to_linear(circular_img, out_w=800, out_h=513)

    # 2. Invert colormap to decibels
    arr_rgb = np.array(linear_img.convert("RGB"))
    h, w, _ = arr_rgb.shape
    flat_rgb = arr_rgb.reshape(-1, 3)

    _, indices = GLOBAL_SOX_TREE.query(flat_rgb)
    norm_vals = indices.reshape(h, w).astype(float) / 255.0
    norm_vals = np.flipud(norm_vals)  # Low freq at bottom row 0

    top_db = 96.0
    mag_db = (norm_vals * top_db) - top_db
    mag = 10.0 ** (mag_db / 20.0)

    # Adjust columns to match target duration
    n_fft = 1024
    hop_length = 256
    expected_frames = int((target_duration_sec * sample_rate) / hop_length)
    if expected_frames > 0 and expected_frames != w:
        coords_x = np.linspace(0, w - 1, expected_frames)
        coords_y = np.arange(h)
        grid_y, grid_x = np.meshgrid(coords_y, coords_x, indexing='ij')
        mag = ndi.map_coordinates(mag, [grid_y, grid_x], order=1)

    # 3. Griffin-Lim Phase Retrieval
    audio = griffin_lim(mag, n_iter=n_iter, hop_length=hop_length, n_fft=n_fft)
    return audio, sample_rate


# ---------------------------------------------------------------------------
# 8-BIT KIRBY PINBALL VINYL ART GENERATOR
# ---------------------------------------------------------------------------
def get_8bit_kirby_art(image_source=None, size=140):
    """
    Creates an authentic 8-bit Kirby's Pinball Land Game Boy style center vinyl label badge.
    Downsamples to 48x48 pixel grid, quantizes to 4-color GB palette, composites vinyl label.
    """
    if image_source is None:
        # Generate default Kirby avatar
        img = Image.new("RGB", (48, 48), (248, 140, 176))
        d = ImageDraw.Draw(img)
        # Kirby body
        d.ellipse([6, 6, 42, 42], fill=(248, 140, 176), outline=(196, 59, 120))
        # Eyes
        d.rectangle([18, 14, 21, 24], fill=(44, 24, 52))
        d.rectangle([27, 14, 30, 24], fill=(44, 24, 52))
        d.rectangle([19, 15, 20, 18], fill=(255, 244, 212))
        d.rectangle([28, 15, 29, 18], fill=(255, 244, 212))
        # Cheeks
        d.ellipse([11, 24, 16, 28], fill=(196, 59, 120))
        d.ellipse([32, 24, 37, 28], fill=(196, 59, 120))
        # Smile
        d.arc([20, 24, 28, 30], 0, 180, fill=(44, 24, 52))
    else:
        try:
            if isinstance(image_source, str) and (image_source.startswith("http://") or image_source.startswith("https://")):
                req = urllib.request.Request(image_source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    img = Image.open(io.BytesIO(resp.read())).convert("RGB")
            elif isinstance(image_source, str) and os.path.exists(image_source):
                img = Image.open(image_source).convert("RGB")
            elif isinstance(image_source, Image.Image):
                img = image_source.convert("RGB")
            else:
                img = Image.new("RGB", (48, 48), (248, 140, 176))
        except Exception:
            img = Image.new("RGB", (48, 48), (248, 140, 176))

    # Downsample to 48x48
    img_tiny = img.resize((48, 48), Image.Resampling.BILINEAR)

    # Dither-quantize to Kirby Pinball 4-Color Palette
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in KIRBY_PINBALL_PALETTE:
        flat_palette.extend(rgb)
    flat_palette.extend([0] * (768 - len(flat_palette)))
    pal_img.putpalette(flat_palette)

    quantized = img_tiny.convert("RGB").quantize(palette=pal_img, dither=Image.Dither.FLOYDSTEINBERG)
    quantized_rgb = quantized.convert("RGB")

    # Upscale with Nearest-Neighbor for razor-sharp pixel aesthetic
    upscaled = quantized_rgb.resize((size, size), Image.Resampling.NEAREST)

    # Circular mask with vintage paper label border
    label_disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    d_mask = ImageDraw.Draw(mask)
    d_mask.ellipse([2, 2, size - 2, size - 2], fill=255)

    label_disc.paste(upscaled, (0, 0), mask)
    d = ImageDraw.Draw(label_disc)
    d.ellipse([2, 2, size - 2, size - 2], outline=(196, 59, 120, 255), width=3)
    d.ellipse([size * 0.45, size * 0.45, size * 0.55, size * 0.55], fill=(0, 0, 0, 255), outline=(255, 244, 212, 255), width=1)

    return label_disc


def get_remxr42_label_art(image_source=None, size=150, side="A", title="REMXR42"):
    """
    Generates an authentic Teenage Engineering industrial design vinyl record center label.
    Palette: Warm Bone (#eae7de), Basalt (#1c1d20), Safety Orange (#ff4800), Forest Green (#0a3d31).
    Features precision concentric rings, crosshair marks, technical telemetry, and 33 1/3 RPM logotype.
    """
    label_disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(label_disc)
    cx, cy = size / 2.0, size / 2.0

    # 1. Warm bone matte finish disc
    d.ellipse([2, 2, size - 3, size - 3], fill=(234, 231, 222, 255), outline=(30, 32, 34, 255), width=2)

    # 2. Concentric calibrated hairline rings
    d.ellipse([size * 0.08, size * 0.08, size * 0.92, size * 0.92], outline=(190, 186, 175, 255), width=1)
    d.ellipse([size * 0.16, size * 0.16, size * 0.84, size * 0.84], outline=(205, 201, 190, 255), width=1)

    # 3. Accent indicator block (Safety orange for Deck A, Racing Green for Deck B)
    accent_color = (255, 72, 0, 255) if str(side).upper() == "A" else (10, 61, 49, 255)
    d.pieslice([size * 0.10, size * 0.10, size * 0.90, size * 0.90], 215, 245, fill=accent_color)

    # 4. Inset circular window for thumbnail or technical graphic
    thumb_box = [int(size * 0.26), int(size * 0.26), int(size * 0.74), int(size * 0.74)]
    thumb_w = thumb_box[2] - thumb_box[0]

    t_img = None
    if image_source:
        try:
            if isinstance(image_source, str) and (image_source.startswith("http://") or image_source.startswith("https://")):
                req = urllib.request.Request(image_source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    t_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
            elif isinstance(image_source, str) and os.path.exists(image_source):
                t_img = Image.open(image_source).convert("RGB")
            elif isinstance(image_source, Image.Image):
                t_img = image_source.convert("RGB")
        except Exception:
            t_img = None

    if t_img:
        # Transform thumbnail into Backlit Amber-Orange on Black Display
        t_gray = t_img.convert("L").resize((thumb_w, thumb_w), Image.Resampling.BILINEAR)
        enh = ImageEnhance.Contrast(t_gray).enhance(1.85)
        arr = np.array(enh, dtype=np.float32) / 255.0
        out = np.zeros((thumb_w, thumb_w, 3), dtype=np.uint8)
        out[:, :, 0] = np.clip(arr * 255, 8, 255).astype(np.uint8)
        out[:, :, 1] = np.clip(arr * 135, 4, 160).astype(np.uint8)
        out[:, :, 2] = np.clip(arr * 8, 0, 18).astype(np.uint8)
        out[1::2, :] = (out[1::2, :].astype(np.float32) * 0.70).astype(np.uint8)
        t_crop = Image.fromarray(out, 'RGB')

        t_mask = Image.new("L", (thumb_w, thumb_w), 0)
        t_draw = ImageDraw.Draw(t_mask)
        t_draw.ellipse([1, 1, thumb_w - 2, thumb_w - 2], fill=255)
        label_disc.paste(t_crop, (thumb_box[0], thumb_box[1]), t_mask)
        d.ellipse(thumb_box, outline=(255, 140, 0, 255), width=2)
    else:
        d.ellipse(thumb_box, fill=(20, 12, 4, 255), outline=(255, 120, 0, 255), width=2)

    # 5. Technical Crosshairs & Dial Ticks
    for deg in [0, 90, 180, 270]:
        rad = np.radians(deg)
        r1, r2 = size * 0.38, size * 0.44
        x1, y1 = cx + r1 * np.cos(rad), cy + r1 * np.sin(rad)
        x2, y2 = cx + r2 * np.cos(rad), cy + r2 * np.sin(rad)
        d.line([x1, y1, x2, y2], fill=(30, 32, 34, 255), width=1)

    # 6. Typography text marks
    font = ImageFont.load_default()
    d.text((cx - 20, size * 0.12), "remxr42", font=font, fill=(30, 32, 34, 255))
    d.text((cx - 32, size * 0.78), f"SIDE {str(side).upper()} / 33 RPM", font=font, fill=(80, 82, 85, 255))

    # 7. Spindle hole with brass bushing ring
    spindle_r = int(size * 0.065)
    d.ellipse([cx - spindle_r - 2, cy - spindle_r - 2, cx + spindle_r + 2, cy + spindle_r + 2], fill=(210, 180, 120, 255), outline=(100, 80, 50, 255), width=1)
    d.ellipse([cx - spindle_r, cy - spindle_r, cx + spindle_r, cy + spindle_r], fill=(10, 10, 10, 255), outline=(234, 231, 222, 255), width=1)

    return label_disc


def render_grid_compass_display(image_source=None, width=280, height=180, title="TRACK THUMBNAIL", sub_label="REMXR-42 // OPTICAL MON"):
    """
    Renders a thumbnail in the form of a backlit orange on black electroluminescent display (ELD),
    featuring:
    - Deep charcoal/black magnesium bezel
    - Backlit amber-orange phosphor pixel grid (320x240 style)
    - Electroluminescent scanlines & dot matrix
    - Phosphor glow & contrast expansion
    - High-contrast amber typography
    """
    t_img = None
    if image_source:
        try:
            if isinstance(image_source, str) and (image_source.startswith("http://") or image_source.startswith("https://")):
                req = urllib.request.Request(image_source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    t_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
            elif isinstance(image_source, str) and os.path.exists(image_source):
                t_img = Image.open(image_source).convert("RGB")
            elif isinstance(image_source, Image.Image):
                t_img = image_source.convert("RGB")
        except Exception:
            t_img = None

    bezel_pad_x = 10
    bezel_pad_y = 10
    screen_w = width - (bezel_pad_x * 2)
    screen_h = height - (bezel_pad_y * 2) - 18

    if t_img:
        img_gray = t_img.convert("L")
    else:
        # Create a default technical oscilloscope / synthesizer wave for the screen
        img_gray = Image.new("L", (screen_w, screen_h), 15)
        d_synth = ImageDraw.Draw(img_gray)
        pts = [(x, int(screen_h/2 + 25 * np.sin(x * 0.08) * np.cos(x * 0.03))) for x in range(screen_w)]
        d_synth.line(pts, fill=220, width=2)
        d_synth.text((10, 10), "REMXR-42 SYNTH WAVE", fill=180)

    # Scale to screen size and enhance contrast
    img_screen = img_gray.resize((screen_w, screen_h), Image.Resampling.BILINEAR)
    enh = ImageEnhance.Contrast(img_screen).enhance(1.85)
    arr = np.array(enh, dtype=np.float32) / 255.0

    # Map to Electroluminescent Amber-Orange on Pitch Black
    out = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    out[:, :, 0] = np.clip(arr * 255, 8, 255).astype(np.uint8)     # Red
    out[:, :, 1] = np.clip(arr * 135, 4, 160).astype(np.uint8)     # Green -> Amber
    out[:, :, 2] = np.clip(arr * 8, 0, 18).astype(np.uint8)        # Blue (almost zero)

    # Electroluminescent horizontal scanlines & dot matrix
    out[1::2, :] = (out[1::2, :].astype(np.float32) * 0.68).astype(np.uint8)
    out[:, 1::2] = (out[:, 1::2].astype(np.float32) * 0.90).astype(np.uint8)

    screen_img = Image.fromarray(out, 'RGB')

    # Magnesium dark chassis unit
    unit = Image.new('RGBA', (width, height), (16, 14, 13, 255))
    d = ImageDraw.Draw(unit)

    # Outer beveled bezel
    d.rectangle([0, 0, width-1, height-1], outline=(60, 55, 50, 255), width=2)
    d.rectangle([bezel_pad_x-2, bezel_pad_y-2, bezel_pad_x + screen_w + 1, bezel_pad_y + screen_h + 1], outline=(8, 6, 4, 255), width=2)

    # Paste screen
    unit.paste(screen_img, (bezel_pad_x, bezel_pad_y))

    # Header & Footer lettering in amber phosphor
    font = ImageFont.load_default()
    d.text((bezel_pad_x, height - 16), sub_label[:28], fill=(255, 140, 0, 255), font=font)
    d.text((width - 92, height - 16), "AMBER 320x240", fill=(210, 110, 0, 255), font=font)

    return unit


def render_backlit_waveform_display(audio, sr=44100, width=320, height=80, title="REMXR-42 // WAVEFORM", color_theme="amber"):
    """
    Renders an audio waveform in the form of a backlit electroluminescent amber or mint
    oscilloscope display on a pitch-black chassis with scanlines and level metrics.
    """
    if audio is None or len(audio) == 0:
        audio = np.sin(np.linspace(0, 100 * np.pi, 2048)) * 0.5

    max_val = float(np.max(np.abs(audio)))
    norm_audio = audio / max_val if max_val > 0 else audio

    bezel_pad_x = 8
    bezel_pad_y = 8
    screen_w = width - (bezel_pad_x * 2)
    screen_h = height - (bezel_pad_y * 2) - 14

    bg_color = (12, 10, 8) if color_theme == "amber" else (6, 14, 10)
    screen_img = Image.new("RGB", (screen_w, screen_h), bg_color)
    d_screen = ImageDraw.Draw(screen_img)

    # Technical grid
    grid_col = (45, 30, 10) if color_theme == "amber" else (15, 45, 30)
    for gx in range(0, screen_w, max(10, int(screen_w / 8))):
        d_screen.line([(gx, 0), (gx, screen_h)], fill=grid_col, width=1)
    center_y = screen_h // 2
    d_screen.line([(0, center_y), (screen_w, center_y)], fill=(80, 50, 15) if color_theme == "amber" else (25, 75, 50), width=1)

    # Bin waveform into columns
    step = max(1, len(norm_audio) // screen_w)
    glow_col = (255, 140, 0) if color_theme == "amber" else (0, 255, 157)
    core_col = (255, 220, 120) if color_theme == "amber" else (220, 255, 240)

    for x in range(screen_w):
        chunk = norm_audio[x * step : (x + 1) * step]
        if len(chunk) > 0:
            c_min = float(np.min(chunk))
            c_max = float(np.max(chunk))
        else:
            c_min, c_max = 0.0, 0.0
        y_top = int(center_y + c_min * (center_y - 3))
        y_bot = int(center_y + c_max * (center_y - 3))
        if y_top > y_bot:
            y_top, y_bot = y_bot, y_top
        if y_bot - y_top < 2:
            y_top = center_y - 1
            y_bot = center_y + 1
        d_screen.line([(x, y_top), (x, y_bot)], fill=glow_col, width=1)
        if y_bot - y_top > 4:
            d_screen.line([(x, y_top + 2), (x, y_bot - 2)], fill=core_col, width=1)

    # Electroluminescent scanlines
    arr = np.array(screen_img, dtype=np.uint8)
    arr[1::2, :] = (arr[1::2, :].astype(np.float32) * 0.72).astype(np.uint8)
    screen_img = Image.fromarray(arr, 'RGB')

    # Magnesium chassis
    unit = Image.new('RGBA', (width, height), (16, 14, 13, 255))
    d = ImageDraw.Draw(unit)
    d.rectangle([0, 0, width-1, height-1], outline=(55, 50, 45, 255), width=2)
    d.rectangle([bezel_pad_x-2, bezel_pad_y-2, bezel_pad_x + screen_w + 1, bezel_pad_y + screen_h + 1], outline=(8, 6, 4, 255), width=2)
    unit.paste(screen_img, (bezel_pad_x, bezel_pad_y))

    font = ImageFont.load_default()
    d.text((bezel_pad_x, height - 14), title[:28], fill=(255, 140, 0, 255) if color_theme == "amber" else (0, 255, 157, 255), font=font)
    dur_sec = len(audio) / float(sr) if sr > 0 else 0
    d.text((width - 80, height - 14), f"{dur_sec:.1f}s • 0dB", fill=(180, 120, 40, 255) if color_theme == "amber" else (0, 180, 110, 255), font=font)

    return unit


# ---------------------------------------------------------------------------
# AUDIO SOURCE LOADERS (YOUTUBE, URL, LOCAL, SYNTH)
# ---------------------------------------------------------------------------
def is_youtube_url(url_or_path):
    if not isinstance(url_or_path, str):
        return False
    s = url_or_path.strip()
    return bool(re.search(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+', s))

def extract_youtube_id(url):
    m = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return m.group(1) if m else None

def load_audio_from_source(source, target_sr=22050, max_duration_sec=24.0):
    """
    Loads audio from a YouTube URL, remote HTTP link, or local file.
    Returns: (audio_numpy_array, sample_rate, title_string, thumbnail_url_or_path)
    """
    source_str = str(source).strip()

    if is_youtube_url(source_str):
        import yt_dlp
        import tempfile
        import glob
        import av

        with tempfile.TemporaryDirectory() as tmpdir:
            out_tmpl = os.path.join(tmpdir, 'yt_audio.%(ext)s')
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': out_tmpl,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source_str, download=True)
                title = info.get('title', 'YouTube Audio')
                thumbnail = info.get('thumbnail', None)

            downloaded = glob.glob(os.path.join(tmpdir, 'yt_audio.*'))
            if not downloaded:
                raise RuntimeError("Failed to download YouTube audio file")

            container = av.open(downloaded[0])
            audio_stream = next(s for s in container.streams if s.type == 'audio')
            frames = []
            src_sr = audio_stream.codec_context.sample_rate or 44100
            total_samples = 0
            max_samples = int(max_duration_sec * src_sr)

            for frame in container.decode(audio_stream):
                arr = frame.to_ndarray()
                if arr.ndim > 1:
                    arr = np.mean(arr, axis=0)
                if arr.dtype == np.int16:
                    arr = arr.astype(np.float32) / 32768.0
                elif arr.dtype == np.int32:
                    arr = arr.astype(np.float32) / 2147483648.0
                else:
                    arr = arr.astype(np.float32)
                frames.append(arr)
                total_samples += len(arr)
                if total_samples >= max_samples:
                    break
            container.close()

            audio = np.concatenate(frames)
            if src_sr != target_sr:
                audio = sig.resample(audio, int(len(audio) * float(target_sr) / src_sr))
            return audio.astype(np.float32), target_sr, title, thumbnail

    elif source_str.startswith("http://") or source_str.startswith("https://"):
        req = urllib.request.Request(source_str, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        buf = io.BytesIO(data)
        audio, sr = sf.read(buf)
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        if len(audio) > int(max_duration_sec * sr):
            audio = audio[:int(max_duration_sec * sr)]
        if sr != target_sr:
            audio = sig.resample(audio, int(len(audio) * float(target_sr) / sr))
        name = os.path.basename(source_str).split('?')[0]
        return audio.astype(np.float32), target_sr, name, None

    elif os.path.exists(source_str):
        audio, sr = sf.read(source_str)
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        if len(audio) > int(max_duration_sec * sr):
            audio = audio[:int(max_duration_sec * sr)]
        if sr != target_sr:
            audio = sig.resample(audio, int(len(audio) * float(target_sr) / sr))
        name = os.path.basename(source_str)
        return audio.astype(np.float32), target_sr, name, None

    else:
        raise ValueError(f"Unsupported or non-existent audio source: {source_str}")


def search_youtube(query: str, max_results: int = 4):
    """
    Fast YouTube track search using yt-dlp flat extraction.
    Returns list of dicts: [
        {
            'id': str,
            'title': str,
            'uploader': str,
            'duration_sec': int,
            'duration_str': str,
            'url': str,
            'thumbnail': str
        }, ...
    ]
    """
    if not query or not str(query).strip():
        return []
    import yt_dlp
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'skip_download': True
    }
    q = str(query).strip()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{max_results}:{q}", download=False)
            entries = res.get('entries', []) or []
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []

    results = []
    for e in entries:
        if not e:
            continue
        vid_id = e.get('id')
        if not vid_id:
            continue
        title = e.get('title', 'Unknown Title')
        uploader = e.get('uploader') or e.get('channel') or 'YouTube'
        dur = e.get('duration') or 0
        if dur:
            mins = int(dur) // 60
            secs = int(dur) % 60
            dur_str = f"{mins}:{secs:02d}"
        else:
            dur_str = "--:--"

        thumbs = e.get('thumbnails', [])
        thumb_url = thumbs[-1].get('url') if thumbs else f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"

        results.append({
            'id': vid_id,
            'title': title,
            'uploader': uploader,
            'duration_sec': dur,
            'duration_str': dur_str,
            'url': f"https://www.youtube.com/watch?v={vid_id}",
            'thumbnail': thumb_url
        })
    return results
