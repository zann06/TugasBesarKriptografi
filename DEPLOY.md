# Panduan Menjalankan & Deploy Live (Streamlit)

Ada **dua versi** aplikasi di repo ini:

| File | Teknologi | Kegunaan |
|---|---|---|
| `app.py` | Flask + HTML/CSS/JS | Versi UI kustom (tampilan lab dark-green) |
| `streamlit_app.py` | Streamlit | Versi untuk **deploy online gratis** |

Keduanya memakai modul inti yang sama: `modified_blowfish.py`, `random_lsb.py`, `metrics.py`.
Hasil enkripsi, stegano, dan metrik **identik** di kedua versi.

---

## 1. Jalankan di lokal

```powershell
cd TugasBesar_Kriptografi
pip install -r requirements.txt
```

### Versi Streamlit (port 8501)
```powershell
streamlit run streamlit_app.py
```
Buka: http://localhost:8501

### Versi Flask (port 5000)
```powershell
python app.py
```
Buka: http://127.0.0.1:5000

> Pakai `python -B app.py` kalau tidak ingin folder `__pycache__` dibuat.

---

## 2. Deploy gratis ke Streamlit Community Cloud

### Langkah 1 — Siapkan repository GitHub

1. Buat akun di https://github.com (kalau belum punya).
2. Buat repository baru, misal `tugas-besar-kriptografi`. **Jangan** centang "Add a README".
3. Di folder proyek, jalankan:

```powershell
git init
git add .
git commit -m "Tugas Besar Kriptografi: Modified Blowfish + Random LSB"
git branch -M main
git remote add origin https://github.com/USERNAME/tugas-besar-kriptografi.git
git push -u origin main
```

> Ganti `USERNAME` dengan username GitHub kamu.

### Langkah 2 — Deploy

1. Buka https://share.streamlit.io
2. Login pakai akun GitHub → **Authorize Streamlit**.
3. Klik **Create app** (atau **New app**).
4. Isi:
   - **Repository**: `USERNAME/tugas-besar-kriptografi`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL**: pilih nama, misal `lab-kriptografi-blwfish`
5. Klik **Deploy**.

Tunggu 1–3 menit. Setelah selesai, aplikasi live di:

```
https://lab-kriptografi-blwfish.streamlit.app
```

Link ini bisa langsung dibagikan untuk demo/sidang.

### Update aplikasi

Setiap `git push` ke branch `main`, Streamlit otomatis rebuild aplikasi:

```powershell
git add .
git commit -m "perbaikan tampilan"
git push
```

---

## 3. Catatan penting saat demo

- **App tidur kalau nganggur.** Streamlit Community Cloud mematikan app setelah tidak diakses beberapa jam. Saat dibuka lagi butuh **±30 detik** untuk bangun. **Buka link 5 menit sebelum sidang/demo.**
- **Batas ukuran file upload** di Streamlit Cloud adalah ±200 MB, tapi kita batasi ke 25 MB lewat `.streamlit/config.toml` agar proses enkripsi tidak lambat.
- **Citra harus PNG atau BMP.** Jangan JPG — kompresi JPEG merusak bit LSB dan pesan tidak bisa dipulihkan. Ini juga alasan di versi Flask hanya PNG/BMP yang diterima.
- **Ukuran citra menentukan kapasitas.** Kapasitas pesan = `lebar × tinggi × 3` bit, dikurangi 32 bit header. Contoh: citra 800×600 px menampung ± 179 KB data.
- **Nama repository & path file harus sama** dengan yang diisi di Streamlit, kalau tidak deploy gagal.

---

## 4. Alternatif deploy lain (kalau Streamlit Cloud bermasalah)

### Hugging Face Spaces (gratis, bisa pakai UI Flask yang sekarang)

1. Buat Space baru → pilih **Docker** → **Blank**.
2. Upload semua file proyek.
3. Buat `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "120", "app:app"]
```

4. Tambahkan `gunicorn` ke `requirements.txt`.

### Render (gratis, ada cold start)

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app`

---

## 5. Troubleshooting

| Masalah | Penyebab & solusi |
|---|---|
| `ModuleNotFoundError: metrics` | Jalankan `streamlit run` dari folder proyek, bukan dari folder induk |
| `Port already in use` | `streamlit run streamlit_app.py --server.port 8502` |
| Deploy gagal "requirements" | Pastikan `requirements.txt` ada di root repo, bukan di subfolder |
| Deploy error "file not found" | Cek *Main file path* = `streamlit_app.py` (persis) |
| Pesan tidak bisa dipulihkan | Kunci salah, atau citra disimpan sebagai JPG sehingga LSB rusak |
| `ValueError: Kapasitas gambar tidak mencukupi` | Pakai citra lebih besar atau pesan lebih pendek |
