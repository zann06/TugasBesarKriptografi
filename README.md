# Tugas Besar Kriptografi

**Pengamanan Pesan Teks menggunakan Modified Blowfish (Rotasi Bit Dinamis) & Steganografi Key-Based Random LSB pada Citra Digital**

Aplikasi ini mengenkripsi pesan teks dengan Blowfish yang dimodifikasi, lalu menyembunyikan ciphertext ke dalam citra digital menggunakan steganografi LSB dengan urutan piksel acak yang diturunkan dari kunci rahasia.

---

## Fitur

- **Enkripsi dua varian** — Modified Blowfish (ROTL32 dinamis pada fungsi F) dan Blowfish Standar, keduanya bisa langsung disisipkan ke citra.
- **Steganografi Key-Based Random LSB** — posisi bit disebar pseudo-acak menggunakan seed dari `SHA-256(secret_key)`, bukan LSB berurutan.
- **Dekripsi auto-deteksi** — penerima tidak perlu tahu algoritma yang dipakai; sistem mencoba kedua varian secara otomatis.
- **Pembanding citra** — membandingkan citra asli (cover) dengan citra stego: pratinjau berdampingan, peta selisih, MSE, PSNR, dan jumlah piksel yang berubah.
- **Evaluasi algoritma** — tabel perbandingan avalanche effect, waktu enkripsi, MSE, dan PSNR antara Blowfish Standar dan Modified Blowfish.

---

## Struktur Proyek

```
├── app.py                  # Aplikasi web Flask (UI kustom)
├── streamlit_app.py        # Aplikasi web Streamlit (untuk deploy online)
├── modified_blowfish.py    # Implementasi Blowfish Standar & Modified
├── random_lsb.py           # Steganografi Key-Based Random LSB
├── metrics.py              # MSE, PSNR, avalanche effect, pembanding citra
├── test_evaluation.py      # Skrip pengujian otomatis
├── requirements.txt
├── DEPLOY.md               # Panduan deploy ke Streamlit Cloud
├── templates/index.html    # UI versi Flask
├── static/                 # CSS, JS, font, aset versi Flask
└── .streamlit/config.toml  # Tema & konfigurasi Streamlit
```

---

## Cara Menjalankan

```bash
pip install -r requirements.txt
```

### Versi Streamlit (port 8501)
```bash
streamlit run streamlit_app.py
```
Buka http://localhost:8501

### Versi Flask (port 5000)
```bash
python app.py
```
Buka http://127.0.0.1:5000

Panduan deploy ke internet (gratis): lihat [`DEPLOY.md`](DEPLOY.md).

---

## Metode

### 1. Modified Blowfish

Blowfish standar mengenkripsi blok 64-bit melalui 16 putaran Feistel dengan fungsi F:

```
F(x) = ((S1[a] + S2[b]) mod 2^32 XOR S3[c]) + S4[d] mod 2^32
```

Modifikasi yang diterapkan adalah **penambahan Circular Left Shift (ROTL32) dinamis** pada keluaran fungsi F:

```
F'(x, P[i]) = ROTL32(F(x), P[i] mod 32)
```

Jumlah rotasi ditentukan oleh 5 bit LSB sub-kunci `P[i]`, sehingga setiap putaran memiliki pergeseran bit yang berbeda. Hal ini menambah sifat non-linear dan memperkuat **avalanche effect**, yaitu perubahan satu bit pada plaintext atau kunci yang menyebar ke banyak bit ciphertext.

### 2. Key-Based Random LSB

Alih-alih menyisipkan bit secara berurutan dari piksel pertama (yang mudah dideteksi dengan analisis statistik), posisi penyisipan dipilih acak:

1. `seed = SHA-256(secret_key)` sebagai bilangan 256-bit.
2. PRNG ber-seed tersebut menjalankan **Fisher-Yates parsial** untuk membangkitkan indeks sub-piksel RGB yang unik.
3. Setiap bit payload disisipkan ke bit LSB sub-piksel pada indeks tersebut.
4. Skema ini **prefix-invariant**: untuk mengekstrak 32 bit header maupun seluruh payload, urutan indeks yang dihasilkan selalu konsisten.

Payload yang disisipkan terdiri dari **header 32-bit** (panjang ciphertext) diikuti ciphertext hasil enkripsi.

### 3. Padding

Plaintext diberi **PKCS#7 padding** agar panjangnya kelipatan 8 byte (ukuran blok Blowfish). Saat dekripsi, padding divalidasi sehingga kunci yang salah akan terdeteksi dan ditolak.

---

## Pengujian

```bash
python test_evaluation.py
```

Skrip ini menguji:
1. Fungsionalitas enkripsi–dekripsi dan penyisipan–ekstraksi pada berbagai panjang pesan.
2. Perbandingan avalanche effect dan kecepatan antara Blowfish Standar dan Modified Blowfish.
3. Kualitas citra steganografi (MSE & PSNR).
4. Negative test: memastikan kunci yang salah ditolak.

Contoh keluaran:

```
Panjang Teks   | Status   | AE Std   | AE Mod   | MSE        | PSNR (dB)  | Waktu (ms)
----------------------------------------------------------------------------------------
5              | VALID    |  39.06% |  51.56% | 0.000224   | 84.63      | 31.16
49             | VALID    |  42.19% |  45.31% | 0.001088   | 77.76      | 42.41
139            | VALID    |  46.88% |  62.50% | 0.002945   | 73.44      | 24.93
500            | VALID    |  50.00% |  50.00% | 0.010340   | 67.99      | 45.74
----------------------------------------------------------------------------------------
Uji Kunci Salah: BERHASIL DITOLAK -> (Pesan tidak ditemukan atau kunci rahasia salah.)
```

---

## Catatan Penggunaan

- **Format citra wajib PNG atau BMP.** Kompresi JPEG bersifat lossy dan merusak bit LSB, sehingga pesan tidak dapat dipulihkan.
- **Kapasitas citra** = `lebar × tinggi × 3` bit, dikurangi 32 bit untuk header. Citra 800×600 px menampung sekitar 179 KB data.
- **Kunci rahasia** 1–56 byte UTF-8 (8–448 bit), sesuai spesifikasi Blowfish.

---

## Lisensi

Proyek akademik untuk Tugas Besar mata kuliah Kriptografi.
Font *Space Grotesk* digunakan di bawah SIL Open Font License (lihat `static/space-grotesk-OFL.txt`).
