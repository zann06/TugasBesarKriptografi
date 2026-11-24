"""
app.py
Aplikasi Web Flask untuk Pengamanan Pesan Teks Menggunakan
Modified Blowfish (Rotasi Bit Dinamis) & Steganografi Key-Based Random LSB.
Mendukung perbandingan dengan Blowfish Standar serta pembanding citra cover vs stego.
"""

import base64
import io
import math
import time
from flask import Flask, render_template, request, jsonify
from PIL import Image

from modified_blowfish import BlowfishCipher
from random_lsb import embed_lsb, extract_lsb
from metrics import (
    calculate_image_comparison,
    calculate_mse_psnr,
    evaluate_avalanche_and_speed,
    format_psnr,
)

app = Flask(__name__)

ALGORITHMS = {
    "modified": {
        "label": "Modified Blowfish",
        "description": "Fungsi F + ROTL32 dinamis",
        "modified": True,
    },
    "standard": {
        "label": "Blowfish Standar",
        "description": "Tanpa modifikasi",
        "modified": False,
    },
}


def _image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _run_pipeline(
    cover_img: Image.Image,
    plaintext_bytes: bytes,
    key_bytes: bytes,
    secret_key: str,
    algorithm: str,
) -> dict:
    """Enkripsi + sisipkan untuk satu varian algoritma, lalu hitung kualitas citra."""
    config = ALGORITHMS[algorithm]

    t_start = time.perf_counter()
    cipher = BlowfishCipher(key_bytes, modified=config["modified"])
    ciphertext = cipher.encrypt_bytes(plaintext_bytes)
    stego_img = embed_lsb(cover_img, ciphertext, secret_key)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 3)

    mse, psnr = calculate_mse_psnr(cover_img, stego_img)

    return {
        "key": algorithm,
        "label": config["label"],
        "description": config["description"],
        "ciphertext_hex": ciphertext.hex().upper(),
        "ciphertext_len": len(ciphertext),
        "stego_image_b64": _image_to_base64(stego_img),
        "mse": round(mse, 6),
        "psnr": format_psnr(psnr),
        "psnr_db": None if math.isinf(psnr) else round(psnr, 2),
        "process_time_ms": elapsed_ms,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/encode", methods=["POST"])
def api_encode():
    try:
        plaintext = request.form.get("plaintext", "")
        secret_key = request.form.get("secret_key", "")
        algorithm = request.form.get("algorithm", "modified")
        image_file = request.files.get("cover_image")

        if not plaintext:
            return jsonify({"success": False, "error": "Pesan teks (plaintext) tidak boleh kosong."}), 400
        if not (1 <= len(secret_key.encode("utf-8")) <= 56):
            return jsonify({"success": False, "error": "Panjang kunci rahasia harus 1–56 karakter."}), 400
        if algorithm not in ALGORITHMS:
            return jsonify({"success": False, "error": "Algoritma enkripsi tidak dikenali."}), 400
        if not image_file:
            return jsonify({"success": False, "error": "Silakan unggah gambar penampung (PNG/BMP)."}), 400

        cover_img = Image.open(image_file.stream).convert("RGB")
        w, h = cover_img.size
        plaintext_bytes = plaintext.encode("utf-8")
        key_bytes = secret_key.encode("utf-8")

        # Jalankan kedua varian agar hasil Blowfish Standar dan Modified bisa dibandingkan.
        variants = {
            name: _run_pipeline(cover_img, plaintext_bytes, key_bytes, secret_key, name)
            for name in ("modified", "standard")
        }
        selected = variants[algorithm]

        # Perbandingan Avalanche Effect & kecepatan enkripsi (tanpa penyisipan).
        benchmark = evaluate_avalanche_and_speed(plaintext, secret_key)

        total_bits_embedded = (4 + selected["ciphertext_len"]) * 8
        capacity_bits = w * h * 3

        return jsonify({
            "success": True,
            "algorithm": algorithm,
            "algorithm_label": selected["label"],
            "ciphertext_hex": selected["ciphertext_hex"],
            "ciphertext_len": selected["ciphertext_len"],
            "stego_image_b64": selected["stego_image_b64"],
            "metrics": {
                "image_dim": f"{w} x {h} px",
                "bits_embedded": total_bits_embedded,
                "capacity_bits": capacity_bits,
                "payload_ratio": round((total_bits_embedded / capacity_bits) * 100.0, 4),
                "mse": selected["mse"],
                "psnr": selected["psnr"],
                "psnr_db": selected["psnr_db"],
                "process_time_ms": selected["process_time_ms"],
                "benchmark": benchmark,
            },
            "variants": variants,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/decode", methods=["POST"])
def api_decode():
    try:
        secret_key = request.form.get("secret_key", "")
        image_file = request.files.get("stego_image")

        if not (1 <= len(secret_key.encode("utf-8")) <= 56):
            return jsonify({"success": False, "error": "Panjang kunci rahasia harus 1–56 karakter."}), 400
        if not image_file:
            return jsonify({"success": False, "error": "Silakan unggah Stego-Image (PNG/BMP)."}), 400

        stego_img = Image.open(image_file.stream).convert("RGB")
        key_bytes = secret_key.encode("utf-8")

        t_start = time.perf_counter()
        extracted_cipher = extract_lsb(stego_img, secret_key)

        # Deteksi otomatis algoritma: coba Modified Blowfish, lalu Blowfish Standar.
        plaintext = None
        detected_algorithm = None
        for name in ("modified", "standard"):
            try:
                cipher = BlowfishCipher(key_bytes, modified=ALGORITHMS[name]["modified"])
                plaintext = cipher.decrypt_bytes(extracted_cipher).decode("utf-8")
                detected_algorithm = name
                break
            except (ValueError, UnicodeDecodeError):
                continue

        if detected_algorithm is None:
            raise ValueError("Kunci rahasia salah atau citra bukan stego yang valid.")

        elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 3)

        return jsonify({
            "success": True,
            "plaintext": plaintext,
            "extracted_hex": extracted_cipher.hex().upper(),
            "algorithm": detected_algorithm,
            "algorithm_label": ALGORITHMS[detected_algorithm]["label"],
            "process_time_ms": elapsed_ms,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal memulihkan pesan: {str(e)}"}), 400


@app.route("/api/compare", methods=["POST"])
def api_compare():
    try:
        cover_file = request.files.get("cover_image")
        stego_file = request.files.get("stego_image")

        if not cover_file or not stego_file:
            return jsonify({
                "success": False,
                "error": "Unggah citra asli (cover) dan citra stego terlebih dahulu.",
            }), 400

        cover_img = Image.open(cover_file.stream).convert("RGB")
        stego_img = Image.open(stego_file.stream).convert("RGB")

        if cover_img.size != stego_img.size:
            cw, ch = cover_img.size
            sw, sh = stego_img.size
            return jsonify({
                "success": False,
                "error": (
                    f"Dimensi citra berbeda ({cw} x {ch} px vs {sw} x {sh} px). "
                    "Gunakan dua citra dengan ukuran yang sama."
                ),
            }), 400

        t_start = time.perf_counter()
        stats = calculate_image_comparison(cover_img, stego_img)
        diff_img = stats.pop("diff_image")
        elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 3)

        w, h = cover_img.size
        return jsonify({
            "success": True,
            "metrics": {
                "image_dim": f"{w} x {h} px",
                "mse": round(stats["mse"], 6),
                "psnr": format_psnr(stats["psnr"]),
                "psnr_db": None if math.isinf(stats["psnr"]) else round(stats["psnr"], 2),
                "max_diff": stats["max_diff"],
                "mean_abs_diff": round(stats["mean_abs_diff"], 6),
                "total_pixels": stats["total_pixels"],
                "changed_pixels": stats["changed_pixels"],
                "changed_pixel_ratio": round(stats["changed_pixel_ratio"], 4),
                "total_subpixels": stats["total_subpixels"],
                "changed_subpixels": stats["changed_subpixels"],
                "changed_subpixel_ratio": round(stats["changed_subpixel_ratio"], 4),
                "identical": stats["identical"],
                "diff_image_b64": _image_to_base64(diff_img),
                "process_time_ms": elapsed_ms,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal membandingkan citra: {str(e)}"}), 400


if __name__ == "__main__":
    print("Server berjalan di http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
