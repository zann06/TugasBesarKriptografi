"""
test_lengkap.py
Pengujian lanjutan untuk menutup celah cakupan pada test_evaluation.py.

Berkas ini TIDAK mengubah algoritma apa pun. Semua fungsi diimpor dari
modified_blowfish.py, random_lsb.py, dan metrics.py yang sudah ada.

Cakupan tambahan:
  A. Variasi panjang kunci (1-56 byte) pada KEDUA varian + validasi batas
  B. Variasi format plaintext (UTF-8 multibyte, emoji, NUL, newline)
  C. Variasi cover media (ukuran citra & format berkas, termasuk simpan-muat)
  D. Kapasitas terlampaui (penolakan yang benar)
  E. Avalanche Effect dengan banyak sampel (rata-rata + simpangan baku)
  F. Sensitivitas kunci 1-bit pada KEDUA varian
  G. Pipeline end-to-end pada KEDUA varian (standar vs modified)

Setiap pengujian memakai ambang lulus yang ditetapkan di awal.
"""

import io
import os
import struct
import sys
import time

import numpy as np
from PIL import Image

from modified_blowfish import BlowfishCipher
from random_lsb import embed_lsb, extract_lsb, derive_seed
from metrics import calculate_mse_psnr, hamming_distance_bits

# ============================================================
# AMBANG LULUS (ditetapkan sebelum eksekusi)
# ============================================================
AMBANG_PSNR_DB = 40.0          # citra stego harus di atas ambang persepsi
AMBANG_AE_MIN = 40.0           # batas bawah Avalanche Effect (%)
AMBANG_AE_MAX = 60.0           # batas atas Avalanche Effect (%)
AMBANG_SENS_MIN = 40.0         # batas bawah sensitivitas kunci (%)
AMBANG_SENS_MAX = 60.0         # batas atas sensitivitas kunci (%)
JUMLAH_FLIP_AE = 64            # enumerasi penuh seluruh bit blok 64-bit

KEY = "KunciRahasiaITERA2026"
KEY_BYTES = KEY.encode("utf-8")
VARIAN = ("standar", "modified")

# ============================================================
# UTILITAS
# ============================================================
_hasil = []          # (kode, nama uji, status, keterangan)


def catat(kode, nama, lulus, ket=""):
    status = "PASS" if lulus else "FAIL"
    _hasil.append((kode, nama, status, ket))
    print(f"  [{status}] {kode} {nama}" + (f" -> {ket}" if ket else ""))


def buat_citra(w, h, seed=42):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def cipher(varian, key_bytes=KEY_BYTES):
    return BlowfishCipher(key_bytes, modified=(varian == "modified"))


def flip_bit(data: bytes, posisi: int) -> bytes:
    b = bytearray(data)
    b[posisi // 8] ^= (1 << (posisi % 8))
    return bytes(b)


# ============================================================
# A. VARIASI PANJANG KUNCI
# ============================================================
def uji_panjang_kunci():
    print("\n" + "=" * 78)
    print("A. VARIASI PANJANG KUNCI (1-56 byte) PADA KEDUA VARIAN")
    print("=" * 78)

    base = b"KunciRahasiaITERA2026XYZ0123456789abcdefghijklmnopqrstuvwxyz"
    pesan = b"Pesan uji panjang kunci"

    for varian in VARIAN:
        print(f"\n  -- varian {varian} --")
        seen = {}
        semua_pulih = True
        for n in [1, 2, 3, 4, 8, 16, 21, 32, 56]:
            k = base[:n]
            bf = cipher(varian, k)
            ct = bf.encrypt_bytes(pesan)
            pulih = bf.decrypt_bytes(ct) == pesan
            semua_pulih = semua_pulih and pulih
            seen[ct] = seen.get(ct, 0) + 1
            print(f"     {n:2d} byte ({n*8:3d} bit) ct={ct.hex()[:16]}... pulih={pulih}")

        catat(f"A1-{varian}", "Semua panjang kunci 1-56 byte dapat dipulihkan",
              semua_pulih)
        catat(f"A2-{varian}", "Setiap panjang kunci menghasilkan ciphertext unik",
              len(seen) == 9, f"{len(seen)}/9 unik")

        # validasi batas
        tolak = []
        for n in (0, 57):
            try:
                cipher(varian, b"K" * n).encrypt_bytes(pesan)
                tolak.append(False)
            except ValueError:
                tolak.append(True)
        catat(f"A3-{varian}", "Kunci 0 byte dan 57 byte ditolak ValueError",
              all(tolak))


# ============================================================
# B. VARIASI FORMAT PLAINTEXT
# ============================================================
def uji_format_plaintext():
    print("\n" + "=" * 78)
    print("B. VARIASI FORMAT PLAINTEXT (UTF-8, emoji, NUL, newline)")
    print("=" * 78)

    sampel = {
        "ASCII polos": "Halo ITERA",
        "UTF-8 multibyte": "Kriptografi \u00e9\u00e8\u00ea \u65e5\u672c\u8a9e",
        "Emoji 4-byte": "\U0001F510" * 20,
        "Mengandung NUL": "a\x00b\x00c",
        "Newline dan tab": "baris1\nbaris2\ttab",
        "Karakter khusus": "a!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/",
    }

    for varian in VARIAN:
        print(f"\n  -- varian {varian} --")
        semua = True
        for nama, s in sampel.items():
            b = s.encode("utf-8")
            bf = cipher(varian)
            ct = bf.encrypt_bytes(b)
            pulih = bf.decrypt_bytes(ct) == b
            semua = semua and pulih
            print(f"     {nama:20s} {len(s):3d} char -> {len(b):3d} byte -> "
                  f"ct {len(ct):3d} byte | pulih={pulih}")
        catat(f"B1-{varian}", "Semua format plaintext pulih byte-per-byte", semua)


# ============================================================
# C. VARIASI COVER MEDIA
# ============================================================
def uji_cover_media():
    print("\n" + "=" * 78)
    print("C. VARIASI COVER MEDIA (ukuran & format berkas)")
    print("=" * 78)

    pesan = b"Pesan uji cover media"
    bf = cipher("modified")
    ct = bf.encrypt_bytes(pesan)

    # --- C1: variasi ukuran ---
    print("\n  -- C1. variasi ukuran citra --")
    hasil_ukuran = []
    for (w, h) in [(64, 64), (128, 128), (256, 256), (512, 512), (1024, 768)]:
        img = buat_citra(w, h)
        st = embed_lsb(img, ct, KEY)
        mse, psnr = calculate_mse_psnr(img, st)
        pulih = bf.decrypt_bytes(extract_lsb(st, KEY)) == pesan
        kap = w * h * 3
        hasil_ukuran.append((w, h, kap, kap // 8 - 4, mse, psnr, pulih))
        print(f"     {w:4d}x{h:<4d} kap={kap:8d} bit | maks {kap//8-4:7d} B | "
              f"MSE {mse:.6f} PSNR {psnr:6.2f} dB | pulih={pulih}")

    catat("C1a", "Semua ukuran citra memulihkan pesan",
          all(r[6] for r in hasil_ukuran))
    catat("C1b", "PSNR semua ukuran di atas ambang 40 dB",
          all(r[5] >= AMBANG_PSNR_DB for r in hasil_ukuran),
          f"min {min(r[5] for r in hasil_ukuran):.2f} dB")
    # PSNR naik seiring ukuran citra (payload tetap)
    naik = all(hasil_ukuran[i][5] <= hasil_ukuran[i+1][5]
               for i in range(len(hasil_ukuran) - 1))
    catat("C1c", "PSNR naik seiring bertambahnya ukuran citra", naik)

    # --- C2: variasi format berkas (simpan lalu muat ulang) ---
    print("\n  -- C2. variasi format berkas (simpan-muat ulang) --")
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_cover")
    os.makedirs(tmp, exist_ok=True)

    img = buat_citra(256, 256)
    format_uji = [
        ("PNG", "png", {}),
        ("BMP", "bmp", {}),
        ("WEBP lossless", "webp", {"lossless": True}),
        ("TIFF", "tif", {}),
        ("JPEG lossy", "jpg", {"quality": 90}),
    ]

    for label, ext, kw in format_uji:
        p = os.path.join(tmp, f"cover.{ext}")
        img.save(p, **kw)
        loaded = Image.open(p).convert("RGB")
        st = embed_lsb(loaded, ct, KEY)
        mse, psnr = calculate_mse_psnr(loaded, st)

        # simpan stego, muat ulang, ekstrak
        p2 = os.path.join(tmp, f"stego.{ext}")
        st.save(p2, **kw)
        reload_st = Image.open(p2).convert("RGB")
        try:
            pulih = bf.decrypt_bytes(extract_lsb(reload_st, KEY)) == pesan
            ket = "pulih" if pulih else "salah"
        except Exception as e:
            pulih = False
            ket = f"GAGAL {type(e).__name__}"
        print(f"     {label:14s} MSE {mse:.6f} PSNR {psnr:6.2f} dB | "
              f"setelah simpan-muat: {ket}")

        if label.startswith("JPEG"):
            catat("C2-jpeg", "JPEG lossy TIDAK dapat diandalkan (diharapkan gagal)",
                  not pulih, "terbukti rusak" if not pulih else "ternyata pulih")
        else:
            catat(f"C2-{ext}", f"{label} bertahan setelah simpan-muat", pulih)

    # bersihkan
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


# ============================================================
# D. KAPASITAS TERLAMPAUI
# ============================================================
def uji_kapasitas():
    print("\n" + "=" * 78)
    print("D. KAPASITAS TERLAMPAUI (penolakan yang benar)")
    print("=" * 78)

    img = buat_citra(64, 64)
    bf = cipher("modified")
    kap_bit = 64 * 64 * 3
    maks_byte = kap_bit // 8 - 4

    # di bawah batas
    ct_ok = bf.encrypt_bytes(b"X" * 1000)
    try:
        embed_lsb(img, ct_ok, KEY)
        lulus_ok = True
    except Exception:
        lulus_ok = False
    catat("D1", f"Payload {len(ct_ok)} byte (< {maks_byte}) diterima", lulus_ok)

    # di atas batas
    ct_besar = bf.encrypt_bytes(b"X" * 1600)
    try:
        embed_lsb(img, ct_besar, KEY)
        lulus_besar = False
        pesan_galat = "(tidak menolak!)"
    except ValueError as e:
        lulus_besar = True
        pesan_galat = str(e)
    catat("D2", f"Payload {len(ct_besar)} byte (> {maks_byte}) ditolak",
          lulus_besar, pesan_galat[:70])


# ============================================================
# E. AVALANCHE EFFECT DENGAN BANYAK SAMPEL
# ============================================================
def uji_avalanche():
    print("\n" + "=" * 78)
    print(f"E. AVALANCHE EFFECT ({JUMLAH_FLIP_AE} SAMPEL BIT-FLIP)")
    print("=" * 78)

    pesan = b"Tugas Besar Kriptografi Semester Ganjil 2026/2027"
    blok = pesan[:8]
    total_bit_blok = 64

    ringkas = {}
    for varian in VARIAN:
        bf = cipher(varian)
        acuan = bf.encrypt_bytes(blok)[:8]
        nilai = []
        for pos in range(JUMLAH_FLIP_AE):
            pos_bit = pos % total_bit_blok
            blok_ubah = flip_bit(blok, pos_bit)
            ct_ubah = bf.encrypt_bytes(blok_ubah)[:8]
            d = hamming_distance_bits(acuan, ct_ubah)
            nilai.append(d / total_bit_blok * 100.0)
        arr = np.array(nilai)
        ringkas[varian] = (arr.mean(), arr.std(), arr.min(), arr.max())
        print(f"  {varian:9s} rata-rata {arr.mean():6.2f}% | "
              f"std {arr.std():5.2f} | min {arr.min():5.2f}% | max {arr.max():5.2f}%")

    for varian in VARIAN:
        mean, std, mn, mx = ringkas[varian]
        catat(f"E1-{varian}", f"AE {varian} dalam rentang "
              f"{AMBANG_AE_MIN:.0f}-{AMBANG_AE_MAX:.0f}%",
              AMBANG_AE_MIN <= mean <= AMBANG_AE_MAX,
              f"rata-rata {mean:.2f}%")

    selisih = ringkas["modified"][0] - ringkas["standar"][0]
    print(f"\n  Selisih rata-rata AE (modified - standar): {selisih:+.2f}%")
    catat("E2", "Perbandingan AE kedua varian tercatat", True,
          f"modified {ringkas['modified'][0]:.2f}% vs "
          f"standar {ringkas['standar'][0]:.2f}%")


# ============================================================
# F. SENSITIVITAS KUNCI 1-BIT
# ============================================================
def uji_sensitivitas_kunci():
    print("\n" + "=" * 78)
    print("F. SENSITIVITAS KUNCI 1-BIT PADA KEDUA VARIAN")
    print("=" * 78)

    pesan = b"Pesan rahasia untuk uji sensitivitas kunci"
    total_bit_kunci = len(KEY_BYTES) * 8
    print(f"  kunci {len(KEY_BYTES)} byte = {total_bit_kunci} bit, "
          f"plaintext {len(pesan)} byte = {len(pesan)*8} bit")

    ringkas = {}
    for varian in VARIAN:
        bf = cipher(varian)
        acuan = bf.encrypt_bytes(pesan)
        total_bit_ct = len(acuan) * 8
        nilai = []
        for pos in range(total_bit_kunci):
            k2 = flip_bit(KEY_BYTES, pos)
            bf2 = cipher(varian, k2)
            ct2 = bf2.encrypt_bytes(pesan)
            d = hamming_distance_bits(acuan, ct2)
            nilai.append(d / total_bit_ct * 100.0)
        arr = np.array(nilai)
        ringkas[varian] = (arr.mean(), arr.std(), arr.min(), arr.max())
        print(f"  {varian:9s} rata-rata {arr.mean():6.2f}% | "
              f"std {arr.std():5.2f} | min {arr.min():5.2f}% | max {arr.max():5.2f}%")

    for varian in VARIAN:
        mean, std, mn, mx = ringkas[varian]
        catat(f"F1-{varian}", f"Sensitivitas kunci {varian} dalam rentang "
              f"{AMBANG_SENS_MIN:.0f}-{AMBANG_SENS_MAX:.0f}%",
              AMBANG_SENS_MIN <= mean <= AMBANG_SENS_MAX,
              f"rata-rata {mean:.2f}%")


# ============================================================
# G. PIPELINE END-TO-END KEDUA VARIAN
# ============================================================
def uji_pipeline():
    print("\n" + "=" * 78)
    print("G. PIPELINE END-TO-END KEDUA VARIAN (enkripsi + sisip + ekstrak + dekripsi)")
    print("=" * 78)

    cover = buat_citra(256, 256)
    teks = ["ITERA",
            "Tugas Besar Kriptografi Semester Ganjil 2026/2027",
            "Pengamanan pesan teks menggunakan modifikasi Blowfish berbasis "
            "rotasi bit dinamis dan steganografi Key-Based Random LSB pada "
            "citra digital.",
            "A" * 500]

    hasil = {}
    for varian in VARIAN:
        print(f"\n  -- varian {varian} --")
        baris = []
        for msg in teks:
            b = msg.encode("utf-8")
            bf = cipher(varian)
            t0 = time.perf_counter()
            ct = bf.encrypt_bytes(b)
            st = embed_lsb(cover, ct, KEY)
            ext = extract_lsb(st, KEY)
            dec = bf.decrypt_bytes(ext).decode("utf-8")
            ms = (time.perf_counter() - t0) * 1000.0
            mse, psnr = calculate_mse_psnr(cover, st)
            ok = dec == msg
            baris.append((len(msg), len(ct), mse, psnr, ms, ok))
            print(f"     {len(msg):3d} char -> ct {len(ct):3d} B | "
                  f"MSE {mse:.6f} PSNR {psnr:6.2f} dB | {ms:6.2f} ms | "
                  f"{'VALID' if ok else 'GAGAL'}")
        hasil[varian] = baris

    for varian in VARIAN:
        catat(f"G1-{varian}", f"Semua teks uji VALID pada varian {varian}",
              all(r[5] for r in hasil[varian]))
        catat(f"G2-{varian}", f"PSNR varian {varian} di atas 40 dB",
              all(r[3] >= AMBANG_PSNR_DB for r in hasil[varian]),
              f"min {min(r[3] for r in hasil[varian]):.2f} dB")

    # tabel perbandingan
    print("\n  -- perbandingan standar vs modified --")
    print(f"     {'Panjang':>7} | {'ct std':>7} {'ct mod':>7} | "
          f"{'PSNR std':>9} {'PSNR mod':>9} | {'ms std':>7} {'ms mod':>7}")
    for i in range(len(teks)):
        s, m = hasil["standar"][i], hasil["modified"][i]
        print(f"     {s[0]:7d} | {s[1]:7d} {m[1]:7d} | "
              f"{s[3]:9.2f} {m[3]:9.2f} | {s[4]:7.2f} {m[4]:7.2f}")


# ============================================================
# H. PENOLAKAN KUNCI SALAH
# ============================================================
def uji_kunci_salah():
    print("\n" + "=" * 78)
    print("H. PENOLAKAN KUNCI SALAH")
    print("=" * 78)

    cover = buat_citra(256, 256)
    pesan = "Pesan rahasia yang harus terlindungi".encode()

    for varian in VARIAN:
        bf = cipher(varian)
        ct = bf.encrypt_bytes(pesan)
        st = embed_lsb(cover, ct, KEY)

        # 1. kunci salah pada ekstraksi
        ditolak_ekstrak = False
        try:
            extract_lsb(st, "KunciSalah2026")
        except ValueError:
            ditolak_ekstrak = True
        catat(f"H1-{varian}", "Ekstraksi dengan kunci salah ditolak ValueError",
              ditolak_ekstrak)

        # 2. kunci salah pada dekripsi (ciphertext benar, kunci beda)
        bf_salah = cipher(varian, b"KunciSalah2026")
        ditolak_dekrip = False
        try:
            hasil = bf_salah.decrypt_bytes(ct).decode("utf-8")
            ditolak_dekrip = (hasil != pesan.decode())
        except (ValueError, UnicodeDecodeError):
            ditolak_dekrip = True
        catat(f"H2-{varian}", "Dekripsi dengan kunci salah tidak menghasilkan plaintext",
              ditolak_dekrip)


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 78)
    print("PENGUJIAN LENGKAP HYBRID MODIFIED BLOWFISH + KEY-BASED RANDOM LSB")
    print("Menguji KEDUA varian (standar dan modified) secara berdampingan")
    print("=" * 78)
    print(f"Ambang: PSNR >= {AMBANG_PSNR_DB} dB | "
          f"AE {AMBANG_AE_MIN}-{AMBANG_AE_MAX}% | "
          f"Sensitivitas {AMBANG_SENS_MIN}-{AMBANG_SENS_MAX}%")

    t_mulai = time.perf_counter()
    uji_panjang_kunci()
    uji_format_plaintext()
    uji_cover_media()
    uji_kapasitas()
    uji_avalanche()
    uji_sensitivitas_kunci()
    uji_pipeline()
    uji_kunci_salah()
    durasi = time.perf_counter() - t_mulai

    # ringkasan
    print("\n" + "=" * 78)
    print("RINGKASAN HASIL")
    print("=" * 78)
    total = len(_hasil)
    lulus = sum(1 for h in _hasil if h[2] == "PASS")
    gagal = total - lulus
    for kode, nama, status, ket in _hasil:
        tanda = "OK  " if status == "PASS" else "X   "
        print(f"  {tanda} {kode:14s} {nama}" + (f"  [{ket}]" if ket else ""))
    print("-" * 78)
    print(f"  Total {total} uji | LULUS {lulus} | GAGAL {gagal} | "
          f"Durasi {durasi:.1f} detik")
    print("=" * 78)
    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
