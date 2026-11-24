FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependensi dipisah agar layer cache tidak rusak setiap kali kode berubah
COPY requirements-space.txt ./
RUN pip install --no-cache-dir -r requirements-space.txt

COPY . .

# Hugging Face Spaces (Docker) meneruskan trafik ke port 7860
EXPOSE 7860

# Blowfish key expansion cukup berat CPU, jadi 1 worker + beberapa thread
# lebih stabil daripada banyak worker yang berebut CPU.
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "180", "--access-logfile", "-", "app:app"]
