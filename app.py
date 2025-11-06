# app.py
import streamlit as st
import requests
import json
import html
import base64  # <-- TAMBAHKAN INI

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

    st.markdown("<div id='scroll-target-player'></div>", unsafe_allow_html=True)

    st.markdown("**Teks Arab:**")
    st.markdown(f"<div style='font-size:40px; direction: rtl; text-align: right;'>{html.escape(arab)}</div>", unsafe_allow_html=True)

    st.markdown("**Latin:**")
    st.markdown(f"<div style='font-size:20px'>{html.escape(latin)}</div>", unsafe_allow_html=True)

    st.markdown("**Terjemahan:**")
    st.markdown(f"<div style='font-size:18px'>{html.escape(indo)}</div>", unsafe_allow_html=True)

    # --- PERUBAHAN BESAR DIMULAI DI SINI ---
    
    # 1. Download audio di sisi Python (Server) untuk menghindari CORS
    audio_data_uri = ""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://equran.id/'
        }
        with requests.get(audio_url, headers=headers, stream=True, timeout=15) as r_audio:
            r_audio.raise_for_status()
            audio_bytes = r_audio.content
        
        # 2. Encode audio menjadi Base64 Data URI
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        audio_data_uri = f"data:audio/mp3;base64,{audio_base64}"

    except Exception as e:
        st.error(f"Gagal mengambil audio (masalah CORS/Jaringan): {e}")
        st.stop()
    
    if not audio_data_uri:
        st.error("Audio Data URI gagal dibuat.")
        st.stop()

    # --- Karaoke Player (KEMBALI KE KODE ASLI ANDA, TAPI DENGAN PERBAIKAN)
    autoplay_flag = "true" if auto_play == "Ya" else "false"
    repeat_flag = "true" if repeat_audio else "false"

    payload = {
        # 3. Gunakan Data URI, BUKAN URL asli
        "audio_url": audio_data_uri, 
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

    # Ini adalah kode HTML/JS Anda sebelumnya, dengan perbaikan dari saya
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

      <audio id="audio" crossorigin="anonymous" preload="metadata" referrerpolicy="no-referrer" {"loop" if repeat_audio else ""}>
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
        background: #ffcccc; /* Warna highlight (merah muda) */
        color: #a00; /* Warna teks (merah tua) */
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

      // Fungsi split teks Arab (ini sudah ada di kode Anda)
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

      // --- PERBAIKAN TEKS LATIN AGAR BISA IKUT KARAOKE ---
      // Kita pecah juga teks Latin berdasarkan spasi
      const latinSegs = latinText.trim().split(/\\s+/);
      const latinContainer = document.getElementById('latinContainer');
      latinContainer.innerHTML = '';
      latinSegs.forEach((seg, i) => {{
        const span = document.createElement('span');
        span.className = 'kara-seg-latin'; // Class berbeda
        span.dataset.idx = i;
        span.textContent = seg + ' ';
        span.style.transition = 'color 0.2s';
        span.style.padding = '0 1px';
        latinContainer.appendChild(span);
      }});

      document.getElementById('indoContainer').textContent = indoText;

      let duration = 0;

      // 4. Set 'src' audio menggunakan Data URI dari payload
      if (payload.audio_url) {{
        audio.src = payload.audio_url;
      }} else {{
        console.error("Audio Data URI tidak ditemukan!");
      }}

      audio.onloadedmetadata = () => {{
        duration = audio.duration;
        timeLabel.textContent = '0:00 / ' + formatTime(duration);
        
        // 5. Logika Autoplay sekarang akan berfungsi
        if (payload.auto_play === "true") {{
          var playPromise = audio.play();
          if (playPromise !== undefined) {{
            playPromise.catch(e => console.warn('Autoplay dicegah oleh browser:', e));
          }}
        }}
      }};

      function formatTime(t) {{
        const s = Math.floor(t % 60);
        const m = Math.floor(t / 60);
        return m + ':' + (s < 10 ? '0' + s : s);
      }}

      // 6. INI ADALAH LOGIKA KARAOKE (sudah ada di kode Anda)
      function updateUI() {{
        if (!duration) return;
        const currentTime = audio.currentTime;
        const frac = currentTime / duration;
        seek.value = frac;
        timeLabel.textContent = formatTime(currentTime) + ' / ' + formatTime(duration);

        // Hitung indeks kata yang aktif
        const arabIdx = Math.min(arabSegs.length - 1, Math.floor(frac * arabSegs.length));
        const latinIdx = Math.min(latinSegs.length - 1, Math.floor(frac * latinSegs.length));

        // Update highlight Arab
        document.querySelectorAll('.kara-seg').forEach(e => e.classList.remove('kara-active'));
        const activeArab = document.querySelector('.kara-seg[data-idx="' + arabIdx + '"]');
        if (activeArab) activeArab.classList.add('kara-active');

        // Update highlight Latin (sedikit berbeda, kita ubah warna saja)
        document.querySelectorAll('.kara-seg-latin').forEach(e => {{
            e.style.color = '#000'; // Reset warna
            e.style.backgroundColor = 'transparent';
        }});
        const activeLatin = document.querySelector('.kara-seg-latin[data-idx="' + latinIdx + '"]');
        if (activeLatin) {{
            activeLatin.style.color = '#000';
            activeLatin.style.backgroundColor = '#fef08a'; // Samakan dengan highlight Arab
            activeLatin.style.borderRadius = '3px';
        }}
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
        document.querySelectorAll('.kara-seg').forEach(e => e.classList.remove('kara-active'));
        document.querySelectorAll('.kara-seg-latin').forEach(e => {{
            e.style.color = '#000';
            e.style.backgroundColor = 'transparent';
        }});
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

    st.components.v1.html(html_code, height=480, scrolling=True)
    st.markdown("> 🔊 **Auto Play** & **Repeat** aktif sesuai pengaturan di atas.")

    scroll_script = """
    <script>
        // Kita beri jeda sedikit (misal 300ms) untuk memastikan 
        // elemen 'scroll-target-player' sudah dirender oleh Streamlit
        setTimeout(function() {
            // Perintah ini mencari elemen di 'jendela induk' (halaman utama Streamlit)
            var target = window.parent.document.getElementById('scroll-target-player');
            
            if (target) {
                // Perintahkan browser untuk scroll ke elemen tersebut
                target.scrollIntoView({ 
                    behavior: 'smooth', // Animasi scroll halus
                    block: 'start'      // Posisikan di bagian atas layar
                });
            }
        }, 300); 
    </script>
    """
    # Kita gunakan height=0 karena komponen ini tidak perlu terlihat
    st.components.v1.html(scroll_script, height=0)



