# Deploy ke Hugging Face Spaces (UI Flask — tampilan sama persis dengan lokal)

Panduan ini untuk meng-online-kan **versi Flask** (`app.py`) sehingga tampilan yang muncul
di internet **identik** dengan yang ada di `127.0.0.1:5000` — hero bergambar chip, tab kotak,
file picker drag & drop, semuanya.

---

## Prasyarat

- Akun Hugging Face (gratis): https://huggingface.co/join
- File yang dibutuhkan sudah ada di repo ini:
  - `Dockerfile`
  - `requirements-space.txt`
  - `app.py`, `modified_blowfish.py`, `random_lsb.py`, `metrics.py`
  - `templates/`, `static/`

---

## Cara 1 — Lewat website (paling mudah, tanpa install apa pun)

### Langkah 1: Buat Space baru

1. Buka https://huggingface.co/new-space
2. Isi:
   - **Space name**: `lab-kriptografi` (atau bebas)
   - **License**: MIT
   - **Select the Space SDK**: **Docker** → pilih template **Blank**
   - **Space hardware**: CPU basic (gratis)
   - **Visibility**: Public
3. Klik **Create Space**

### Langkah 2: Upload file

Setelah Space dibuat, buka tab **Files** → **Add file** → **Upload files**.

Upload semua file berikut (pertahankan struktur folder):

```
Dockerfile
requirements-space.txt
app.py
modified_blowfish.py
random_lsb.py
metrics.py
templates/index.html
static/crypto.css
static/crypto.js
static/crypto-chip.webp
static/space-grotesk.woff2
static/space-grotesk-OFL.txt
```

> **Penting:** `README.md` Space **wajib** berisi YAML front-matter dengan `sdk: docker`
> dan `app_port: 7860`. Kalau mengupload `README.md` dari repo GitHub (tanpa front-matter),
> Space akan gagal build. Gunakan isi file `hf_space_readme.md` sebagai `README.md` di Space,
> atau edit langsung `README.md` di tab Files dan tambahkan blok berikut di paling atas:

```yaml
---
title: Lab Kriptografi - Modified Blowfish & Random LSB
emoji: 🔐
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
---
```

### Langkah 3: Tunggu build

Buka tab **App**. Build pertama makan waktu **3–6 menit** (install Python + numpy + pillow).
Status akan berubah: `Building` → `Running`.

Aplikasi live di:

```
https://huggingface.co/spaces/USERNAME/lab-kriptografi
```

---

## Cara 2 — Lewat Git (untuk update berulang)

```powershell
# 1. Install tool HF
pip install huggingface_hub

# 2. Login (butuh token dari https://huggingface.co/settings/tokens, scope: write)
hf auth login

# 3. Clone Space kosong
git clone https://huggingface.co/spaces/USERNAME/lab-kriptografi hf-space
cd hf-space

# 4. Salin file proyek
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\Dockerfile .
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\requirements-space.txt .
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\app.py .
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\modified_blowfish.py .
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\random_lsb.py .
Copy-Item C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\metrics.py .
Copy-Item -Recurse C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\templates .
Copy-Item -Recurse C:\project\TugasBesar_Kriptografi\TugasBesar_Kriptografi\static .
Copy-Item C:\Users\User\AppData\Local\Temp\opencode\hf_space_readme.md README.md

# 5. Push
git add .
git commit -m "Deploy Lab Kriptografi"
git push
```

Setiap `git push` berikutnya akan otomatis rebuild Space.

---

## Cara 3 — Lewat GitHub (auto-sync)

Hugging Face bisa menarik otomatis dari repo GitHub:

1. Di halaman Space → **Settings** → **Repository** → **Connect to a GitHub repository**
2. Pilih `zann06/TugasBesarKriptografi`, branch `main`
3. Simpan

Namun cara ini menyalin **seluruh** isi repo, termasuk `streamlit_app.py` dan `README.md`
tanpa front-matter — Space akan gagal build. **Cara 1 atau 2 lebih aman.**

---

## Verifikasi yang sudah dilakukan

Sebelum panduan ini ditulis, image Docker-nya sudah di-build dan dijalankan di lokal:

| Uji | Hasil |
|---|---|
| `docker build` | ✅ sukses, image 327 MB |
| Gunicorn start di port 7860 | ✅ `Listening at: http://0.0.0.0:7860` |
| `GET /` | ✅ HTTP 200, title benar |
| `GET /static/crypto.css` | ✅ HTTP 200, 17 KB |
| Elemen UI (tab Pembanding, dll) | ✅ semua ada |
| `POST /api/encode` (modified) | ✅ PSNR 78.10 dB, 2 varian dikembalikan |
| `POST /api/decode` | ✅ pesan balik persis, auto-deteksi benar |
| `POST /api/encode` (standard) | ✅ terdeteksi Blowfish Standar |
| `POST /api/compare` | ✅ 157 piksel berubah, peta selisih terkirim |
| Kunci salah | ✅ ditolak HTTP 400 |

---

## Troubleshooting

| Masalah | Penyebab & solusi |
|---|---|
| Build gagal `No such file: requirements.txt` | Dockerfile memakai `requirements-space.txt` — pastikan file itu ikut terupload |
| Space error "README.md missing sdk" | Tambahkan YAML front-matter `sdk: docker` dan `app_port: 7860` |
| Build sukses tapi App blank / 503 | Cek **Logs** → pastikan gunicorn listen di `0.0.0.0:7860`, bukan `127.0.0.1` |
| `ModuleNotFoundError: flask` | `requirements-space.txt` tidak terupload atau namanya salah |
| Space tidur | Space gratis **tidur setelah 48 jam** tidak diakses. Buka 2–3 menit sebelum sidang |
| Enkripsi lambat (>10 detik) | Normal untuk citra besar di CPU basic; Blowfish key expansion memang berat |
