"""
test_evaluation.py
Skrip Pengujian Otomatis (Tahap 7) untuk Menghasilkan Data Evaluasi BAB IV Laporan:
1. Uji Fungsionalitas Enkripsi-Dekripsi & Embedding-Extraction
2. Uji Perbandingan Avalanche Effect & Kecepatan (Blowfish Standar vs Modified Blowfish)
3. Uji Kualitas Citra Steganografi (MSE & PSNR) pada berbagai panjang pesan
"""

import time
import numpy as np
from PIL import Image
from modified_blowfish import BlowfishCipher
from random_lsb import embed_lsb, extract_lsb
from metrics import calculate_mse_psnr, evaluate_avalanche_and_speed


def run_all_tests():
    key = "KunciRahasiaITERA2026"
    # Buat citra uji sintetis RGB 256x256 (kapasitas 196.608 bit = 24.576 byte)
    rng = np.random.default_rng(42)
    sample_pixels = rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)
    cover_img = Image.fromarray(sample_pixels, mode="RGB")

    test_messages = [
        "ITERA",
        "Tugas Besar Kriptografi Semester Ganjil 2026/2027",
        "Pengamanan pesan teks menggunakan modifikasi Blowfish berbasis rotasi bit dinamis dan steganografi Key-Based Random LSB pada citra digital.",
        "A" * 500
    ]

    print("=" * 88)
    print("HASIL PENGUJIAN OTOMATIS HYBRID MODIFIED BLOWFISH + KEY-BASED RANDOM LSB")
    print("=" * 88)
    print(f"{'Panjang Teks':<14} | {'Status':<8} | {'AE Std':<8} | {'AE Mod':<8} | {'MSE':<10} | {'PSNR (dB)':<10} | {'Waktu (ms)':<10}")
    print("-" * 88)

    for msg in test_messages:
        t0 = time.perf_counter()
        cipher = BlowfishCipher(key.encode("utf-8"), modified=True)
        ct = cipher.encrypt_bytes(msg.encode("utf-8"))
        stego = embed_lsb(cover_img, ct, key)

        ext_ct = extract_lsb(stego, key)
        dec_pt = cipher.decrypt_bytes(ext_ct).decode("utf-8")
        elapsed = (time.perf_counter() - t0) * 1000.0

        status = "VALID" if dec_pt == msg else "GAGAL"
        mse, psnr = calculate_mse_psnr(cover_img, stego)
        bench = evaluate_avalanche_and_speed(msg, key)

        print(f"{len(msg):<14} | {status:<8} | {bench['std_avalanche']:>6.2f}% | {bench['mod_avalanche']:>6.2f}% | {mse:<10.6f} | {psnr:<10.2f} | {elapsed:<10.2f}")

    # Uji Kunci Salah (Negative Test)
    print("-" * 88)
    ct_valid = BlowfishCipher(key.encode("utf-8"), modified=True).encrypt_bytes(b"Pesan Rahasia")
    stego_valid = embed_lsb(cover_img, ct_valid, key)
    try:
        extract_lsb(stego_valid, "KunciSalah2026")
        print("Uji Kunci Salah: GAGAL (seharusnya menolak kunci salah)")
    except ValueError as err:
        print(f"Uji Kunci Salah: BERHASIL DITOLAK -> ({err})")
    print("=" * 88)


if __name__ == "__main__":
    run_all_tests()
