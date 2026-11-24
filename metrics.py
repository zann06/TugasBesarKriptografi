"""
metrics.py
Modul Evaluasi Kinerja: Avalanche Effect, MSE, PSNR, dan Perbandingan Blowfish Asli vs Modifikasi.
"""

import math
import time
import numpy as np
from PIL import Image
from modified_blowfish import BlowfishCipher


def calculate_mse_psnr(cover_img: Image.Image, stego_img: Image.Image) -> tuple[float, float]:
    """Menghitung Mean Squared Error (MSE) dan Peak Signal-to-Noise Ratio (PSNR)."""
    c_arr = np.array(cover_img.convert("RGB"), dtype=np.float64)
    s_arr = np.array(stego_img.convert("RGB"), dtype=np.float64)
    if c_arr.shape != s_arr.shape:
        raise ValueError("Dimensi Cover Image dan Stego Image harus sama.")
    mse = float(np.mean((c_arr - s_arr) ** 2))
    if mse == 0:
        psnr = float("inf")
    else:
        psnr = 10.0 * math.log10((255.0 ** 2) / mse)
    return mse, psnr


def format_psnr(psnr: float) -> str:
    """Format nilai PSNR untuk ditampilkan pada antarmuka."""
    if math.isinf(psnr):
        return "Infinity (Identik)"
    return f"{psnr:.2f} dB"


def calculate_image_comparison(
    cover_img: Image.Image,
    stego_img: Image.Image,
) -> dict:
    """
    Membandingkan citra cover dengan citra stego:
    MSE, PSNR, jumlah piksel/subpiksel yang berubah, serta peta selisih.
    Peta selisih menandai setiap piksel yang berubah dengan warna merah.
    """
    c_arr = np.array(cover_img.convert("RGB"), dtype=np.int16)
    s_arr = np.array(stego_img.convert("RGB"), dtype=np.int16)
    if c_arr.shape != s_arr.shape:
        raise ValueError("Dimensi kedua citra harus sama untuk dibandingkan.")

    diff = np.abs(c_arr - s_arr)
    diff_sq = diff.astype(np.float64) ** 2
    mse = float(np.mean(diff_sq))
    psnr = float("inf") if mse == 0 else 10.0 * math.log10((255.0 ** 2) / mse)

    total_pixels = int(c_arr.shape[0] * c_arr.shape[1])
    total_subpixels = total_pixels * 3
    changed_pixels = int(np.count_nonzero(np.any(diff > 0, axis=2)))
    changed_subpixels = int(np.count_nonzero(diff))

    # Peta selisih: piksel yang berubah diberi warna merah, yang sama diberi
    # latar gelap (bukan hitam pekat) supaya panel tetap terbaca sebagai peta
    # walau perubahan piksel sangat sedikit.
    diff_max = diff.max(axis=2)
    changed = diff_max > 0
    diff_vis = np.full(diff.shape, 22, dtype=np.uint8)
    diff_vis[..., 1] = 26
    diff_vis[..., 2] = 23
    diff_vis[changed] = (255, 60, 60)
    diff_img = Image.fromarray(diff_vis, mode="RGB")

    return {
        "mse": mse,
        "psnr": psnr,
        "max_diff": int(diff.max()) if diff.size else 0,
        "mean_abs_diff": float(diff.mean()) if diff.size else 0.0,
        "total_pixels": total_pixels,
        "total_subpixels": total_subpixels,
        "changed_pixels": changed_pixels,
        "changed_subpixels": changed_subpixels,
        "changed_pixel_ratio": (changed_pixels / total_pixels * 100.0) if total_pixels else 0.0,
        "changed_subpixel_ratio": (changed_subpixels / total_subpixels * 100.0) if total_subpixels else 0.0,
        "identical": mse == 0.0,
        "diff_image": diff_img,
    }


def hamming_distance_bits(b1: bytes, b2: bytes) -> int:
    """Menghitung jumlah bit yang berbeda antara dua array byte."""
    diff = 0
    for x, y in zip(b1, b2):
        diff += bin(x ^ y).count("1")
    return diff


def evaluate_avalanche_and_speed(plaintext: str, key: str) -> dict:
    """
    Membandingkan Avalanche Effect (perubahan 1 bit pada blok pertama 64-bit plaintext)
    dan waktu enkripsi antara Blowfish Standar vs Modified Blowfish.
    """
    pt_bytes = plaintext.encode("utf-8") if plaintext else b"ITERA_KRIPTO"
    key_bytes = key.encode("utf-8")

    # Ambil blok pertama (8 byte) untuk pengukuran Avalanche Effect tingkat blok (64-bit)
    block_pt = pt_bytes[:8]
    flipped_block = bytearray(block_pt)
    flipped_block[0] ^= 0x01
    flipped_block = bytes(flipped_block)

    # 1. Uji Blowfish Standar
    t0 = time.perf_counter()
    bf_std = BlowfishCipher(key_bytes, modified=False)
    _ = bf_std.encrypt_bytes(pt_bytes)
    t_std_ms = (time.perf_counter() - t0) * 1000.0

    c1_std = bf_std.encrypt_bytes(block_pt)[:8]
    c2_std = bf_std.encrypt_bytes(flipped_block)[:8]
    diff_std = hamming_distance_bits(c1_std, c2_std)
    total_bits = 64
    ae_std = (diff_std / total_bits) * 100.0

    # 2. Uji Modified Blowfish
    t0 = time.perf_counter()
    bf_mod = BlowfishCipher(key_bytes, modified=True)
    _ = bf_mod.encrypt_bytes(pt_bytes)
    t_mod_ms = (time.perf_counter() - t0) * 1000.0

    c1_mod = bf_mod.encrypt_bytes(block_pt)[:8]
    c2_mod = bf_mod.encrypt_bytes(flipped_block)[:8]
    diff_mod = hamming_distance_bits(c1_mod, c2_mod)
    ae_mod = (diff_mod / total_bits) * 100.0

    return {
        "total_bits": total_bits,
        "std_diff_bits": diff_std,
        "std_avalanche": round(ae_std, 2),
        "std_time_ms": round(t_std_ms, 3),
        "mod_diff_bits": diff_mod,
        "mod_avalanche": round(ae_mod, 2),
        "mod_time_ms": round(t_mod_ms, 3),
    }
