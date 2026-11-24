"""
streamlit_app.py
Versi web-live (Streamlit) dari Tugas Besar Kriptografi:
Pengamanan Pesan Teks menggunakan Modified Blowfish (ROTL32 dinamis)
& Steganografi Key-Based Random LSB, dengan pembanding Blowfish Standar.

Modul inti (modified_blowfish.py, random_lsb.py, metrics.py) dipakai apa adanya,
sehingga hasil komputasi identik dengan versi Flask.

Jalankan lokal:
    streamlit run streamlit_app.py
"""

import io
import math
import time

import pandas as pd
import streamlit as st
from PIL import Image

from metrics import (
    calculate_image_comparison,
    calculate_mse_psnr,
    evaluate_avalanche_and_speed,
    format_psnr,
)
from modified_blowfish import BlowfishCipher
from random_lsb import embed_lsb, extract_lsb

ALGORITHMS = {
    "modified": {
        "label": "Modified Blowfish",
        "short": "Modified",
        "description": "Fungsi F + ROTL32 dinamis",
        "modified": True,
    },
    "standard": {
        "label": "Blowfish Standar",
        "short": "Standar",
        "description": "Tanpa modifikasi",
        "modified": False,
    },
}

MAX_KEY_BYTES = 56


# --------------------------------------------------------------------------- #
# Lapisan pemrosesan (tipis di atas modul inti)
# --------------------------------------------------------------------------- #
def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def validate_key(secret_key: str) -> str | None:
    """Mengembalikan pesan kesalahan, atau None jika kunci valid."""
    length = len(secret_key.encode("utf-8"))
    if length == 0:
        return "Kunci rahasia tidak boleh kosong."
    if length > MAX_KEY_BYTES:
        return f"Panjang kunci rahasia maksimal {MAX_KEY_BYTES} byte UTF-8 (sekarang {length} byte)."
    return None


def run_pipeline(
    cover_img: Image.Image,
    plaintext_bytes: bytes,
    key_bytes: bytes,
    secret_key: str,
    algorithm: str,
) -> dict:
    """Enkripsi + sisipkan untuk satu varian algoritma."""
    config = ALGORITHMS[algorithm]

    t_start = time.perf_counter()
    cipher = BlowfishCipher(key_bytes, modified=config["modified"])
    ciphertext = cipher.encrypt_bytes(plaintext_bytes)
    stego_img = embed_lsb(cover_img, ciphertext, secret_key)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    w, h = cover_img.size
    mse, psnr = calculate_mse_psnr(cover_img, stego_img)
    return {
        "key": algorithm,
        "label": config["label"],
        "description": config["description"],
        "ciphertext_hex": ciphertext.hex().upper(),
        "ciphertext_len": len(ciphertext),
        "stego_img": stego_img,
        "stego_png": to_png_bytes(stego_img),
        "mse": mse,
        "psnr": psnr,
        "process_time_ms": elapsed_ms,
        "image_dim": f"{w} × {h} px",
        "bits_embedded": (4 + len(ciphertext)) * 8,
        "capacity_bits": w * h * 3,
    }


def decode_pipeline(stego_img: Image.Image, secret_key: str) -> dict:
    """Ekstrak ciphertext lalu coba dekripsi dengan kedua varian algoritma."""
    key_bytes = secret_key.encode("utf-8")

    t_start = time.perf_counter()
    extracted = extract_lsb(stego_img, secret_key)

    plaintext = None
    detected = None
    for name in ("modified", "standard"):
        try:
            cipher = BlowfishCipher(key_bytes, modified=ALGORITHMS[name]["modified"])
            plaintext = cipher.decrypt_bytes(extracted).decode("utf-8")
            detected = name
            break
        except (ValueError, UnicodeDecodeError):
            continue

    if detected is None:
        raise ValueError("Kunci rahasia salah atau citra bukan stego yang valid.")

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    return {
        "plaintext": plaintext,
        "extracted_hex": extracted.hex().upper(),
        "algorithm": detected,
        "algorithm_label": ALGORITHMS[detected]["label"],
        "process_time_ms": elapsed_ms,
    }


def build_comparison_table(result: dict) -> pd.DataFrame:
    """Tabel Blowfish Standar vs Modified Blowfish."""
    bench = result["benchmark"]
    std = result["variants"]["standard"]
    mod = result["variants"]["modified"]

    rows = [
        ("Panjang ciphertext", f"{std['ciphertext_len']} byte", f"{mod['ciphertext_len']} byte"),
        ("Waktu enkripsi + penyisipan", f"{std['process_time_ms']:.2f} ms", f"{mod['process_time_ms']:.2f} ms"),
        ("MSE citra stego", f"{std['mse']:.6f}", f"{mod['mse']:.6f}"),
        ("PSNR citra stego", format_psnr(std["psnr"]), format_psnr(mod["psnr"])),
        (
            "Bit berubah / total",
            f"{bench['std_diff_bits']} / {bench['total_bits']}",
            f"{bench['mod_diff_bits']} / {bench['total_bits']}",
        ),
        ("Avalanche effect", f"{bench['std_avalanche']:.2f}%", f"{bench['mod_avalanche']:.2f}%"),
        ("Waktu penyiapan kunci + enkripsi", f"{bench['std_time_ms']:.2f} ms", f"{bench['mod_time_ms']:.2f} ms"),
    ]
    return pd.DataFrame(rows, columns=["Parameter", "Blowfish Standar", "Modified Blowfish"])


# --------------------------------------------------------------------------- #
# Konfigurasi halaman & gaya
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Lab Kriptografi | Modified Blowfish & Random LSB",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap');

    /* Catatan: JANGAN menimpa font pada elemen ikon Material Streamlit
       (span[data-testid="stIconMaterial"], .material-symbols-rounded, dll),
       karena ikon tersebut berupa ligature teks dan akan tampil sebagai kata mentah. */
    html, body, .stApp, .stMarkdown, p, label, input, textarea, li,
    h1, h2, h3, h4, h5, h6, button, .stButton button {
        font-family: 'Space Grotesk', system-ui, -apple-system, sans-serif;
    }
    .stApp {
        background:
            linear-gradient(90deg, #bdd0b109 1px, transparent 1px) center top / 56px 56px,
            linear-gradient(#bdd0b109 1px, transparent 1px) center top / 56px 56px,
            #101411;
    }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1240px; }

    .lab-brand {
        display: flex; align-items: center; gap: 12px;
        font-size: 1.06rem; font-weight: 700; letter-spacing: -.02em; color: #edf0e7;
        padding-bottom: 14px; border-bottom: 1px solid #323c32; margin-bottom: 26px;
    }
    .lab-brand .mark {
        display: grid; grid-template-columns: repeat(2, 5px); gap: 2px;
        place-content: center; width: 32px; height: 32px;
        border: 1px solid #5b6c5c; border-radius: 6px; background: #1c281c;
    }
    .lab-brand .mark i { aspect-ratio: 1; background: #c6e898; }
    .lab-brand .mark i:nth-child(2) { opacity: .4; }
    .lab-brand .mark i:nth-child(3) { opacity: .65; }
    .lab-brand .tag { margin-left: auto; color: #adb8aa; font: .72rem/1.4 ui-monospace, monospace; font-weight: 400; }

    .hero-eyebrow {
        margin: 0 0 6px; color: #c6e898; font: 500 .72rem/1.4 ui-monospace, monospace;
        letter-spacing: .12em; text-transform: uppercase;
    }
    .hero-title {
        margin: 0; font-size: clamp(2.3rem, 5vw, 3.6rem); font-weight: 700;
        line-height: .95; letter-spacing: -.05em; color: #edf0e7;
    }
    .hero-title span { color: #c6e898; }
    .hero-sub { max-width: 60ch; margin: 12px 0 0; color: #adb8aa; font-size: .98rem; }

    .flow { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 18px 0 0; }
    .flow .step {
        padding: 7px 12px; border: 1px solid #323c32; border-radius: 6px;
        background: #141a15; font-size: .8rem; font-weight: 600; color: #edf0e7;
    }
    .flow .step small { display: block; color: #adb8aa; font: .66rem/1.3 ui-monospace, monospace; font-weight: 400; }
    .flow .arrow { color: #c6e898; font-family: ui-monospace, monospace; }

    .panel-title { margin: 0; font-size: 1.42rem; font-weight: 700; letter-spacing: -.04em; color: #edf0e7; }
    .panel-sub { margin: 3px 0 16px; color: #adb8aa; font-size: .86rem; }

    div[data-testid="stMetric"] {
        padding: 10px 13px; border: 1px solid #323c32; border-radius: 6px; background: #121612;
    }
    div[data-testid="stMetricLabel"] p {
        color: #adb8aa !important; font-size: .76rem !important; font-weight: 400 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #c6e898 !important; font-family: ui-monospace, monospace !important;
        font-size: 1.02rem !important; overflow-wrap: anywhere;
    }

    .hex-box {
        padding: 12px; border: 1px solid #323c32; border-radius: 6px; background: #121612;
        color: #c6e898; font: .78rem/1.6 ui-monospace, monospace;
        white-space: pre-wrap; overflow-wrap: anywhere; max-height: 150px; overflow: auto;
    }
    .hex-box.empty { color: #adb8aa; }

    .empty-state {
        display: grid; place-content: center; justify-items: center;
        min-height: 180px; margin-top: 13px; padding: 18px;
        border: 1px dashed #323c32; border-radius: 6px;
        background:
            radial-gradient(ellipse at center, #182019 20%, transparent 75%),
            radial-gradient(circle, #8eab782c 1px, transparent 1.5px) center / 15px 15px,
            #121612;
        text-align: center;
    }
    .empty-state strong { font-size: .87rem; font-weight: 650; color: #edf0e7; }
    .empty-state p { margin: 3px 0 0; color: #adb8aa; font-size: .78rem; }
    .empty-state .empty-mark {
        width: 35px; height: 31px; margin-bottom: 12px;
        border: 1px solid #5b6c5c; border-radius: 5px;
        background: radial-gradient(circle at center, #8eb286 1.5px, transparent 2px) 1px 1px / 8px 8px, #223024;
    }

    .verdict {
        margin-top: 14px; padding: 10px 13px; border: 1px solid #456044; border-radius: 6px;
        color: #c6e898; font-size: .86rem;
    }
    .verdict.warn { border-color: #88514a; color: #ffc4ba; }

    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #323c32; }
    .stTabs [data-baseweb="tab"] {
        height: auto; padding: 10px 20px; background: transparent; color: #adb8aa;
        border-bottom: 2px solid transparent; font-weight: 600; font-size: .88rem;
    }
    .stTabs [aria-selected="true"] {
        color: #edf0e7 !important; background: #212b20; border-bottom-color: #c6e898 !important;
    }

    div[data-testid="stFileUploaderDropzone"] {
        border: 1px dashed #5b6c5c; border-radius: 6px; background: #1d2720;
    }
    div[data-testid="stFileUploaderDropzone"]:hover { border-color: #c6e898; }
    div[data-testid="stFileUploaderDropzoneInstructions"] div span { color: #adb8aa; }

    /* Pastikan ikon Material tetap memakai font ikonnya sendiri */
    span[data-testid="stIconMaterial"],
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-icons,
    .material-icons-outlined {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }

    /* Tema kotak pesan agar sesuai palet gelap-hijau */
    div[data-testid="stAlertContainer"] {
        border: 1px solid #323c32; border-radius: 6px; background: #191e19; color: #edf0e7;
    }
    div[data-testid="stAlertContainer"] p { color: #edf0e7; }
    div[data-testid="stAlertContentInfo"] { background: #191e19; }

    .stButton > button[kind="primary"], .stDownloadButton > button {
        border-radius: 6px; font-weight: 700;
    }
    .stButton > button[kind="primary"] { background: #c6e898; color: #182018; border-color: transparent; }
    .stButton > button[kind="primary"]:hover { background: #d7f0b3; color: #182018; }
    .stDownloadButton > button { border-color: #5b6c5c; background: #243124; color: #c6e898; }
    .stDownloadButton > button:hover { border-color: #c6e898; color: #c6e898; background: #243124; }

    div[data-testid="stDataFrame"] { border: 1px solid #323c32; border-radius: 6px; }
    hr { border-color: #323c32; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="lab-brand">
      <span class="mark"><i></i><i></i><i></i><i></i></span>
      Lab Kriptografi
      <span class="tag">Tugas Besar Kriptografi</span>
    </div>
    <p class="hero-eyebrow">Kriptografi &amp; Steganografi</p>
    <h1 class="hero-title">Pesan di balik <span>piksel.</span></h1>
    <p class="hero-sub">
      Enkripsi pesan rahasia dengan Blowfish, lalu sembunyikan hasilnya di dalam citra digital
      memakai steganografi Key-Based Random LSB.
    </p>
    <div class="flow">
      <div class="step">Modified Blowfish<small>Enkripsi · ROTL32</small></div>
      <span class="arrow">→</span>
      <div class="step">Key-Based Random LSB<small>Penyisipan · SHA-256</small></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")


# --------------------------------------------------------------------------- #
# Tab 1 — Pengirim
# --------------------------------------------------------------------------- #
def render_encode_tab():
    left, right = st.columns([1, 1.05], gap="large")

    with left:
        st.markdown('<p class="panel-title">Siapkan pesan</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="panel-sub">Isi pesan, kunci rahasia, pilih algoritma, dan citra penampung.</p>',
            unsafe_allow_html=True,
        )

        plaintext = st.text_area(
            "Pesan rahasia",
            height=110,
            placeholder="Tulis pesan yang ingin disembunyikan...",
            key="enc_plaintext",
        )
        secret_key = st.text_input(
            f"Kunci rahasia (1–{MAX_KEY_BYTES} byte UTF-8)",
            type="password",
            placeholder="Masukkan kunci rahasia",
            key="enc_key",
        )
        algorithm = st.segmented_control(
            "Algoritma enkripsi",
            options=list(ALGORITHMS.keys()),
            format_func=lambda name: f"{ALGORITHMS[name]['short']} · {ALGORITHMS[name]['description']}",
            default="modified",
            key="enc_algorithm",
        ) or "modified"
        cover_file = st.file_uploader(
            "Citra penampung (PNG / BMP)",
            type=["png", "bmp"],
            key="enc_cover",
        )

        submitted = st.button(
            "Enkripsi & sisipkan pesan",
            type="primary",
            use_container_width=True,
            key="enc_submit",
        )

        if submitted:
            error = None
            if not plaintext.strip():
                error = "Pesan teks (plaintext) tidak boleh kosong."
            elif validate_key(secret_key):
                error = validate_key(secret_key)
            elif cover_file is None:
                error = "Silakan unggah citra penampung (PNG/BMP)."

            if error:
                st.session_state.pop("encode_result", None)
                st.error(error)
            else:
                try:
                    cover_bytes = cover_file.getvalue()
                    cover_img = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
                    plaintext_bytes = plaintext.encode("utf-8")
                    key_bytes = secret_key.encode("utf-8")

                    with st.spinner("Mengenkripsi dan menyisipkan pesan…"):
                        variants = {
                            name: run_pipeline(cover_img, plaintext_bytes, key_bytes, secret_key, name)
                            for name in ("modified", "standard")
                        }
                        benchmark = evaluate_avalanche_and_speed(plaintext, secret_key)

                    st.session_state["encode_result"] = {
                        "variants": variants,
                        "benchmark": benchmark,
                        "cover_png": cover_bytes,
                        "selected": algorithm,
                        "plaintext": plaintext,
                    }
                except Exception as exc:  # noqa: BLE001
                    st.session_state.pop("encode_result", None)
                    st.error(str(exc))

    with right:
        st.markdown('<p class="panel-title">Hasil enkripsi</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="panel-sub">Ciphertext dan citra hasil penyisipan.</p>',
            unsafe_allow_html=True,
        )

        result = st.session_state.get("encode_result")
        if not result:
            st.markdown(
                '<div class="hex-box empty">Menunggu proses enkripsi.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-mark"></div>'
                "<strong>Belum ada citra hasil</strong>"
                "<p>Citra bisa diunduh setelah pesan berhasil disisipkan.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            return

        variant_key = st.segmented_control(
            "Tampilkan varian",
            options=["modified", "standard"],
            format_func=lambda name: ALGORITHMS[name]["short"],
            default=result["selected"],
            key="enc_variant_view",
        ) or result["selected"]

        variant = result["variants"][variant_key]

        st.markdown(
            f'<p style="color:#adb8aa;font:0.72rem ui-monospace,monospace;margin-bottom:6px;">'
            f'Ciphertext · {variant["label"]} · HEX</p>'
            f'<div class="hex-box">{variant["ciphertext_hex"]}</div>',
            unsafe_allow_html=True,
        )

        st.write("")
        st.image(variant["stego_img"], caption="Pratinjau citra stego", width=360)

        st.download_button(
            f"Unduh citra PNG ({ALGORITHMS[variant_key]['short']})",
            data=variant["stego_png"],
            file_name=f"stego_{variant_key}.png",
            mime="image/png",
            use_container_width=True,
            key="enc_download",
        )

        if st.button("Simpan untuk tab Pembanding", use_container_width=True, key="enc_to_compare"):
            st.session_state["compare_source"] = {
                "cover_png": result["cover_png"],
                "stego_png": variant["stego_png"],
                "variant": variant_key,
            }
            st.success(
                f"Citra {ALGORITHMS[variant_key]['label']} disimpan. "
                "Buka tab **Pembanding** dan aktifkan “Gunakan citra dari tab Pengirim”."
            )

        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("PSNR", format_psnr(variant["psnr"]))
        m2.metric("MSE", f"{variant['mse']:.6f}")
        m3.metric("Waktu proses", f"{variant['process_time_ms']:.2f} ms")

        m4, m5, m6 = st.columns(3)
        m4.metric("Dimensi citra", variant["image_dim"])
        m5.metric("Bit disisipkan", f"{variant['bits_embedded']} bit")
        ratio = variant["bits_embedded"] / variant["capacity_bits"] * 100.0
        m6.metric("Rasio kapasitas", f"{ratio:.4f}%")

    st.divider()
    st.markdown('<p class="panel-title">Evaluasi perbandingan algoritma</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="panel-sub">Blowfish Standar vs Modified Blowfish pada pesan dan citra yang sama.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        build_comparison_table(result),
        hide_index=True,
        width="stretch",
    )

    bench = result["benchmark"]
    gain = bench["mod_avalanche"] - bench["std_avalanche"]
    st.caption(
        f"Avalanche effect diukur dari perubahan 1 bit pada blok pertama 64-bit plaintext "
        f"({bench['total_bits']} bit). Selisih Modified − Standar: **{gain:+.2f}%**. "
        f"Teoritis nilai ideal adalah 50%."
    )


# --------------------------------------------------------------------------- #
# Tab 2 — Penerima
# --------------------------------------------------------------------------- #
def render_decode_tab():
    left, right = st.columns([1, 1.05], gap="large")

    with left:
        st.markdown('<p class="panel-title">Pulihkan pesan</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="panel-sub">Gunakan citra hasil penyisipan dan kunci pengirim.</p>',
            unsafe_allow_html=True,
        )

        stego_file = st.file_uploader(
            "Citra berisi pesan (PNG / BMP)",
            type=["png", "bmp"],
            key="dec_stego",
        )
        secret_key = st.text_input(
            f"Kunci rahasia (1–{MAX_KEY_BYTES} byte UTF-8)",
            type="password",
            placeholder="Masukkan kunci pengirim",
            key="dec_key",
        )

        submitted = st.button(
            "Ekstrak & dekripsi pesan",
            type="primary",
            use_container_width=True,
            key="dec_submit",
        )

        if submitted:
            error = None
            if validate_key(secret_key):
                error = validate_key(secret_key)
            elif stego_file is None:
                error = "Silakan unggah Stego-Image (PNG/BMP)."

            if error:
                st.session_state.pop("decode_result", None)
                st.error(error)
            else:
                try:
                    stego_img = Image.open(io.BytesIO(stego_file.getvalue())).convert("RGB")
                    with st.spinner("Mengekstrak dan mendekripsi…"):
                        st.session_state["decode_result"] = decode_pipeline(stego_img, secret_key)
                except Exception as exc:  # noqa: BLE001
                    st.session_state.pop("decode_result", None)
                    st.error(f"Gagal memulihkan pesan: {exc}")

    with right:
        st.markdown('<p class="panel-title">Hasil dekripsi</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="panel-sub">Ciphertext yang diekstrak dan pesan yang dipulihkan.</p>',
            unsafe_allow_html=True,
        )

        result = st.session_state.get("decode_result")
        if not result:
            st.markdown(
                '<div class="hex-box empty">Menunggu proses ekstraksi.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-mark"></div>'
                "<strong>Belum ada pesan</strong>"
                "<p>Pesan yang dipulihkan akan muncul di sini.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<p style="color:#adb8aa;font:0.72rem ui-monospace,monospace;margin-bottom:6px;">'
            "Ciphertext hasil ekstraksi · HEX</p>"
            f'<div class="hex-box">{result["extracted_hex"]}</div>',
            unsafe_allow_html=True,
        )

        st.write("")
        st.text_area("Pesan asli", value=result["plaintext"], height=140, disabled=True)

        st.caption(
            f"Algoritma terdeteksi · **{result['algorithm_label']}**  \n"
            f"Waktu ekstraksi dan dekripsi · {result['process_time_ms']:.2f} ms"
        )
        st.success("Pesan berhasil dipulihkan.")


# --------------------------------------------------------------------------- #
# Tab 3 — Pembanding
# --------------------------------------------------------------------------- #
def render_compare_tab():
    st.markdown('<p class="panel-title">Bandingkan citra</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="panel-sub">Uji kualitas citra asli (sebelum enkripsi) terhadap citra hasil steganografi.</p>',
        unsafe_allow_html=True,
    )

    source = st.session_state.get("compare_source")
    use_source = False
    if source:
        use_source = st.toggle(
            "Gunakan citra dari tab Pengirim",
            value=True,
            key="cmp_use_source",
            help="Memakai citra cover dan stego dari hasil enkripsi terakhir, tanpa unggah ulang.",
        )

    col_a, col_b = st.columns(2, gap="large")

    if use_source:
        cover_img = Image.open(io.BytesIO(source["cover_png"])).convert("RGB")
        stego_img = Image.open(io.BytesIO(source["stego_png"])).convert("RGB")
        with col_a:
            st.image(cover_img, caption="Citra asli (cover) — dari tab Pengirim", width=340)
        with col_b:
            st.image(
                stego_img,
                caption=f"Citra stego — {ALGORITHMS[source['variant']]['label']}",
                width=340,
            )
        ready = True
    else:
        with col_a:
            cover_file = st.file_uploader("Citra asli (sebelum enkripsi)", type=["png", "bmp"], key="cmp_cover")
        with col_b:
            stego_file = st.file_uploader("Citra stego (hasil penyisipan)", type=["png", "bmp"], key="cmp_stego")
        cover_img = Image.open(io.BytesIO(cover_file.getvalue())).convert("RGB") if cover_file else None
        stego_img = Image.open(io.BytesIO(stego_file.getvalue())).convert("RGB") if stego_file else None
        ready = cover_img is not None and stego_img is not None

    compare_now = st.button(
        "Bandingkan citra",
        type="primary",
        disabled=not ready,
        key="cmp_submit",
    )

    if compare_now:
        if cover_img.size != stego_img.size:
            st.session_state.pop("compare_result", None)
            cw, ch = cover_img.size
            sw, sh = stego_img.size
            st.error(
                f"Dimensi citra berbeda ({cw} × {ch} px vs {sw} × {sh} px). "
                "Gunakan dua citra dengan ukuran yang sama."
            )
        else:
            stats = calculate_image_comparison(cover_img, stego_img)
            st.session_state["compare_result"] = {
                "stats": stats,
                "cover": cover_img,
                "stego": stego_img,
            }

    result = st.session_state.get("compare_result")
    if not result:
        if ready:
            st.info("Klik **Bandingkan citra** untuk menghitung selisih dan metrik kualitas.")
        else:
            st.info("Unggah kedua citra terlebih dahulu.")
        return

    stats = result["stats"]
    st.divider()
    st.markdown('<p class="panel-title">Hasil perbandingan</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="panel-sub">Pratinjau berdampingan, peta selisih, dan metrik kualitas citra.</p>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.image(result["cover"], caption="Citra asli · Cover", width=280)
    with c2:
        st.image(result["stego"], caption="Citra stego · Hasil", width=280)
    with c3:
        st.image(
            stats["diff_image"],
            caption="Peta selisih · merah = piksel berubah",
            width=280,
        )

    st.write("")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("PSNR", format_psnr(stats["psnr"]))
    r2.metric("MSE", f"{stats['mse']:.6f}")
    r3.metric("Dimensi citra", f"{result['cover'].size[0]} × {result['cover'].size[1]} px")
    r4.metric("Piksel berubah", f"{stats['changed_pixels']:,} px".replace(",", "."))

    r5, r6, r7, r8 = st.columns(4)
    r5.metric("Rasio piksel berubah", f"{stats['changed_pixel_ratio']:.4f}%")
    r6.metric("Selisih maksimum", str(stats["max_diff"]))
    r7.metric("Rata-rata selisih", f"{stats['mean_abs_diff']:.6f}")
    r8.metric("Subpiksel berubah", f"{stats['changed_subpixels']:,}".replace(",", "."))

    psnr_db = None if math.isinf(stats["psnr"]) else stats["psnr"]
    if stats["identical"]:
        st.markdown(
            '<div class="verdict">Kedua citra identik — tidak ada piksel yang berubah.</div>',
            unsafe_allow_html=True,
        )
    elif psnr_db is not None and psnr_db >= 40:
        st.markdown(
            '<div class="verdict">Perubahan sangat kecil dan tidak kasat mata. '
            "Citra stego masih terlihat identik dengan aslinya.</div>",
            unsafe_allow_html=True,
        )
    elif psnr_db is not None and psnr_db >= 30:
        st.markdown(
            '<div class="verdict">Perubahan kecil; kualitas citra masih baik untuk '
            "sebagian besar penggunaan.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="verdict warn">Perubahan cukup terlihat. Periksa kembali kapasitas '
            "citra dan proses penyisipan.</div>",
            unsafe_allow_html=True,
        )


tab_encode, tab_decode, tab_compare = st.tabs(
    [
        "⬈  Pengirim · Enkripsi & sisipkan",
        "⬋  Penerima · Ekstrak & dekripsi",
        "⇄  Pembanding · Bandingkan citra",
    ]
)

with tab_encode:
    st.write("")
    render_encode_tab()

with tab_decode:
    st.write("")
    render_decode_tab()

with tab_compare:
    st.write("")
    render_compare_tab()

st.write("")
st.caption(
    "Modified Blowfish (ROTL32 dinamis) + Key-Based Random LSB · "
    "Tugas Besar Kriptografi · dibangun dengan Streamlit"
)
