"""
random_lsb.py
Implementasi Steganografi Key-Based Random Least Significant Bit (LSB)
Menggunakan SHA-256 dari Secret Key sebagai seed PRNG pengacak indeks sub-piksel RGB.
"""

import hashlib
import random
import struct
import numpy as np
from PIL import Image


def derive_seed(secret_key: str) -> int:
    """Menurunkan seed numerik 256-bit dari kunci rahasia via SHA-256."""
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def bytes_to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit
        out.append(byte_val)
    return bytes(out)


def _generate_random_indices(total_subpixels: int, count: int, seed: int) -> list[int]:
    """
    Membangkitkan urutan indeks sub-piksel acak unik secara konsisten (prefix-invariant)
    menggunakan algoritma Fisher-Yates parsial berbasis PRNG ber-seed SHA-256.
    """
    rng = random.Random(seed)
    chosen = []
    swapped = {}
    for i in range(count):
        j = rng.randrange(i, total_subpixels)
        val_i = swapped.get(i, i)
        val_j = swapped.get(j, j)
        swapped[j] = val_i
        chosen.append(val_j)
    return chosen


def embed_lsb(cover_img: Image.Image, ciphertext: bytes, secret_key: str) -> Image.Image:
    """Menyisipkan header panjang (32-bit) + ciphertext ke posisi sub-piksel RGB acak."""
    rgb_img = cover_img.convert("RGB")
    arr = np.array(rgb_img, dtype=np.uint8)
    h, w, c = arr.shape
    total_subpixels = h * w * c

    header = struct.pack(">I", len(ciphertext))
    payload = header + ciphertext
    bit_stream = bytes_to_bits(payload)

    if len(bit_stream) > total_subpixels:
        max_bytes = (total_subpixels // 8) - 4
        raise ValueError(
            f"Kapasitas gambar tidak mencukupi! Butuh {len(bit_stream)} bit, "
            f"kapasitas gambar hanya {total_subpixels} bit (maks ~{max_bytes} byte)."
        )

    seed = derive_seed(secret_key)
    indices = _generate_random_indices(total_subpixels, len(bit_stream), seed)

    flat = arr.flatten()
    for k, bit in enumerate(bit_stream):
        idx = indices[k]
        flat[idx] = (flat[idx] & 0xFE) | bit

    stego_arr = flat.reshape((h, w, c))
    return Image.fromarray(stego_arr, mode="RGB")


def extract_lsb(stego_img: Image.Image, secret_key: str) -> bytes:
    """Mengekstrak ciphertext dari stego-image menggunakan urutan piksel acak dari kunci."""
    rgb_img = stego_img.convert("RGB")
    arr = np.array(rgb_img, dtype=np.uint8)
    h, w, c = arr.shape
    total_subpixels = h * w * c

    if total_subpixels < 32:
        raise ValueError("Ukuran gambar terlalu kecil untuk menyimpan header steganografi.")

    seed = derive_seed(secret_key)
    flat = arr.flatten()

    # 1. Ekstrak 32 bit pertama untuk membaca panjang ciphertext
    header_indices = _generate_random_indices(total_subpixels, 32, seed)
    header_bits = [int(flat[idx] & 1) for idx in header_indices]
    cipher_len = struct.unpack(">I", bits_to_bytes(header_bits))[0]

    total_bits = 32 + (cipher_len * 8)
    if cipher_len == 0 or total_bits > total_subpixels:
        raise ValueError("Pesan tidak ditemukan atau kunci rahasia salah.")

    # 2. Ekstrak seluruh bit payload (32 header + 8 * cipher_len)
    all_indices = _generate_random_indices(total_subpixels, total_bits, seed)
    cipher_bits = [int(flat[idx] & 1) for idx in all_indices[32:]]
    return bits_to_bytes(cipher_bits)
