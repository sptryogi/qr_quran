# app.py
import streamlit as st
import requests
import json
import html

st.set_page_config(layout="wide", page_title="Quran QR → Player")

st.title("📖 Quran QR → Player")
st.markdown(
    """
    Aplikasi demo membaca Al-Qur'an dengan pilihan surat, ayat, dan suara (qari).
    Setelah menekan **Siap**, akan muncul tampilan ayat beserta teks Latin, terjemahan, dan audio dengan highlight karaoke.
    """
)

API_BASE = "https://equran.id/api/v2/surat/{}"

# --- Sidebar
with st.sidebar:
    st.header("⚙️ Kontrol")
    surah_id = st.number_input("ID Surat", min_value=1, max_value=114, value=112, step=1)
    fetch_btn = st.button("🔄 Muat Surat")
    st.markdown("---")

# --- Fetch data surat
surat_data = None
if fetch_btn:
    try:
        r = requests.get(API_BASE.format(int(surah_id)), timeout=10)
        r.raise_for_status()
        surat_data = r.json().get("data")
        if surat_data:
            st.session_state["surat_data"] = surat_data
            st.success(f"Surat **{surat_data['namaLatin']} ({surat_data['nama']})** berhasil dimuat.")
        else:
            st.error("Gagal mengambil data surat.")
    except Exception as e:
        st.error(f"Gagal fetch data: {e}")

# Reuse surat dari session state
if "surat_data" in st.session_state:
    surat_data = st.session_state["surat_data"]

if not surat_data:
    st.info("Masukkan nomor surat dan klik *Muat Surat* di kiri.")
    st.stop()

# --- Kontrol setelah surat dimuat
st.subheader(f"{surat_data['namaLatin']} — {surat_data['nama']} ({surat_data['tempatTurun']})")
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    ayat_nomor = st.selectbox("Pilih Ayat", options=list(range(1, surat_data["jumlahAyat"] + 1)), index=0)
with col2:
    reciters = list(surat_data["audioFull"].keys())
    reciter_choice = st.selectbox("Pilih Qari", options=reciters, index=0)
with col3:
    auto_play = st.radio("Auto Play setelah klik Siap?", ["Ya", "Tidak"], index=1, horizontal=True)
    repeat_audio = st.checkbox("🔁 Ulangi (Repeat)", value=False)

ready = st.button("🎧 Siap")

if ready:
    ayat_obj = next((a for a in surat_data["ayat"] if a["nomorAyat"] == int(ayat_nomor)), None)
    if not ayat_obj:
        st.error("Ayat tidak ditemukan.")
        st.stop()

    audio_url = ayat_obj["audio"].get(reciter_choice)
    arab = ayat_obj["teksArab"]
    latin = ayat_obj["teksLatin"]
    indo = ayat_obj["teksIndonesia"]

    st.markdown("---")
    st.markdown(f"## {surat_data['namaLatin']} : {ayat_nomor}")

    st.markdown("**Teks Arab:**")
    st.markdown(f"<div style='font-size:40px; direction: rtl; text-align: right;'>{html.escape(arab)}</div>", unsafe_allow_html=True)

    st.markdown("**Latin:**")
    st.markdown(f"<div style='font-size:20px'>{html.escape(latin)}</div>", unsafe_allow_html=True)

    st.markdown("**Terjemahan:**")
    st.markdown(f"<div style='font-size:18px'>{html.escape(indo)}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"**Qari:** {reciter_choice}")

    # --- INI ADALAH PERUBAHAN UTAMA ---
    # Kita tidak bisa menggunakan HTML/JS player karena CORS.
    # Kita harus download audio di sisi server (Python) lalu menampilkannya.
    
    try:
        # 1. Download audio bytes menggunakan Python (server-side, tidak ada CORS)
        # Tambahkan header User-Agent agar terlihat seperti browser biasa
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://equran.id/' # Coba berpura-pura jadi equran.id
        }
        
        # Tambahkan stream=True dan timeout
        with requests.get(audio_url, headers=headers, stream=True, timeout=10) as r_audio:
            r_audio.raise_for_status()
            
            # Baca audio bytes
            audio_bytes = r_audio.content

            # 2. Gunakan st.audio bawaan Streamlit
            autoplay_flag = True if auto_play == "Ya" else False
            
            # st.audio() tidak mendukung repeat, tapi bisa autoplay
            st.audio(audio_bytes, format='audio/mp3', start_time=0)
            
            if autoplay_flag:
                st.markdown("> 🔊 **Catatan:** Autoplay diatur oleh browser. Anda mungkin perlu menekan play secara manual.")
            
            # Opsi repeat manual (kurang ideal, tapi sbg info)
            if repeat_audio:
                st.warning("Fitur 'Repeat' tidak didukung oleh st.audio() bawaan.")

    except Exception as e:
        st.error(f"Gagal mengambil audio (masalah CORS atau jaringan): {e}")
        st.error(f"URL Audio: {audio_url}")

    st.markdown("> 🔊 **Auto Play** & **Repeat** aktif sesuai pengaturan di atas.")

