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

    # --- Karaoke Player
    autoplay_flag = "true" if auto_play == "Ya" else "false"
    repeat_flag = "true" if repeat_audio else "false"

    payload = {
        "audio_url": audio_url,
        "arab": arab,
        "latin": latin,
        "indo": indo,
        "reciter": reciter_choice,
        "ayat_nomor": ayat_nomor,
        "surah_nomor": surat_data["nomor"],
        "surah_nama": surat_data["namaLatin"],
        "auto_play": autoplay_flag,
        "repeat": repeat_flag,
    }

    payload_json = json.dumps(payload)

    html_code = f"""
    <div id="karaoke-container" style="max-width:100%; padding:15px; border-radius:8px; border:1px solid #ddd;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <button id="playBtn">▶️ Play</button>
          <button id="pauseBtn">⏸️ Pause</button>
          <input id="seek" type="range" min="0" max="1" step="0.001" value="0" style="width:250px;" />
          <span id="timeLabel">0:00 / 0:00</span>
        </div>
        <div>
          <strong>{payload["surah_nama"]} : {payload["ayat_nomor"]}</strong> | Qari: {payload["reciter"]}
        </div>
      </div>

      <audio id="audio" crossorigin="anonymous" preload="metadata" {"loop" if repeat_audio else ""}>
        Browser tidak mendukung audio.
      </audio>

      <div id="arabContainer" style="margin-top:20px; font-size:48px; direction:rtl; text-align:right; line-height:1.5;"></div>
      <div id="latinContainer" style="margin-top:10px; font-size:20px;"></div>
      <div id="indoContainer" style="margin-top:5px; font-size:16px; color:#555;"></div>
    </div>

    <style>
      .kara-seg {{
        display:inline-block;
        padding:0 2px;
        transition: background-color 0.2s, color 0.2s;
      }}
      .kara-active {{
        background: #fef08a;
        color: #000;
        border-radius:4px;
      }}
    </style>

    <script>
    (function() {{
      const payload = {payload_json};
      const audio = document.getElementById('audio');
      const playBtn = document.getElementById('playBtn');
      const pauseBtn = document.getElementById('pauseBtn');
      const seek = document.getElementById('seek');
      const timeLabel = document.getElementById('timeLabel');

      const arabText = payload.arab;
      const latinText = payload.latin;
      const indoText = payload.indo;

      function splitArabic(text) {{
        const words = text.trim().split(/\\s+/);
        if (words.length < 2) return text.split('');
        return words;
      }}

      const arabSegs = splitArabic(arabText);
      const arabContainer = document.getElementById('arabContainer');
      arabContainer.innerHTML = '';
      arabSegs.forEach((seg, i) => {{
        const span = document.createElement('span');
        span.className = 'kara-seg';
        span.dataset.idx = i;
        span.textContent = seg + ' ';
        arabContainer.appendChild(span);
      }});

      document.getElementById('latinContainer').textContent = latinText;
      document.getElementById('indoContainer').textContent = indoText;

      let duration = 0;
      // --- PERUBAHAN DIMULAI ---
      // Secara manual atur sumber audio dari payload JS
      if (payload.audio_url) {{
          audio.src = payload.audio_url;
      }} else {{
          console.error("Audio URL tidak ditemukan di payload.");
      }}

      audio.onloadedmetadata = () => {{
        duration = audio.duration;
        timeLabel.textContent = '0:00 / ' + formatTime(duration);
        
        // Logika autoplay yang lebih baik dengan penanganan promise
        if (payload.auto_play === "true") {{
           var playPromise = audio.play();
           if (playPromise !== undefined) {{
             playPromise.catch(e => {{
               console.warn('Autoplay dicegah oleh browser:', e);
             }});
           }}
        }}
      }};

      function formatTime(t) {{
        const s = Math.floor(t % 60);
        const m = Math.floor(t / 60);
        return m + ':' + (s < 10 ? '0' + s : s);
      }}

      function updateUI() {{
        if (!duration) return;
        const frac = audio.currentTime / duration;
        seek.value = frac;
        timeLabel.textContent = formatTime(audio.currentTime) + ' / ' + formatTime(duration);

        const idx = Math.min(arabSegs.length - 1, Math.floor(frac * arabSegs.length));
        document.querySelectorAll('.kara-seg').forEach(e => e.classList.remove('kara-active'));
        const active = document.querySelector(`.kara-seg[data-idx="{{idx}}"]`);
        if (active) active.classList.add('kara-active');
      }}

      let raf;
      function loop() {{
        updateUI();
        raf = requestAnimationFrame(loop);
      }}
      audio.onplay = () => loop();
      audio.onpause = () => cancelAnimationFrame(raf);
      audio.onended = () => {{
        cancelAnimationFrame(raf);
        if (payload.repeat === "true") {{
          audio.currentTime = 0;
          audio.play();
        }}
      }};

      playBtn.onclick = () => audio.play();
      pauseBtn.onclick = () => audio.pause();
      seek.oninput = e => {{
        audio.currentTime = parseFloat(e.target.value) * duration;
      }};
    }})();
    </script>
    """

    st.components.v1.html(html_code, height=460, scrolling=True)
    st.markdown("> 🔊 **Auto Play** & **Repeat** aktif sesuai pengaturan di atas.")

