import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time
import json
import os
import re
from datetime import datetime, timedelta
import hashlib
import hmac
import random
import requests # WorldPass için gerekli

# ================== AYARLAR & KONFİGÜRASYON ==================
st.set_page_config(
    page_title="Heptapus SponsorBot Pro",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

# Dosya Yolları
HISTORY_FILE = "gonderim_gecmisi.json"
CONFIG_FILE = "config_settings.json"
TEMPLATE_FILE = "mail_sablonlari.json"

# WorldPass Ayarları (GERİ GELDİ)
WORLDPASS_LOGIN_URL = "https://worldpass-beta.heptapusgroup.com/api/user/login"
ADMIN_EMAILS = ["sametutku64@gmail.com"]

# SMTP Sağlayıcı Ayarları (Hazır Listesi)
SMTP_PRESETS = {
    "Özel (Manuel Ayar)": {"host": "", "port": 587},
    "Gmail": {"host": "smtp.gmail.com", "port": 587},
    "Outlook / Hotmail": {"host": "smtp.office365.com", "port": 587},
    "Yandex Mail": {"host": "smtp.yandex.com", "port": 465},
    "IEEE (Google Altyapılı)": {"host": "smtp.gmail.com", "port": 587},
    "Yahoo Mail": {"host": "smtp.mail.yahoo.com", "port": 587},
    "Zoho Mail": {"host": "smtp.zoho.com", "port": 587}
}

# ================== CSS (UI/UX) ==================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    :root {
        --bg-color: #0e1117;
        --card-bg: #1e293b; 
        --text-primary: #f8fafc;
        --border: #334155;
        --input-bg: #0f172a;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Kart Yapısı */
    .stCard {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid var(--border);
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Input Alanları */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: var(--input-bg) !important;
        color: white !important;
        border-color: var(--border) !important;
        border-radius: 8px;
    }
    
    /* Butonlar */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton button:hover { transform: translateY(-2px); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid var(--border);
    }
    
    /* Login Box */
    .login-box {
        background: var(--card-bg);
        padding: 40px;
        border-radius: 16px;
        border: 1px solid var(--border);
        text-align: center;
        max-width: 450px;
        margin: 50px auto;
    }

    /* Hero Alanı */
    .hero {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        border: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================== YARDIMCI FONKSİYONLAR ==================
def load_json(filename):
    if not os.path.exists(filename): return [] if "gecmisi" in filename or "sablon" in filename else {}
    try:
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    except: return [] if "gecmisi" in filename or "sablon" in filename else {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash) if password_hash else False

def render_template(text, row_data, global_ctx):
    if not text: return ""
    res = str(text)
    for k, v in row_data.items(): res = res.replace(f"{{{k}}}", str(v))
    for k, v in global_ctx.items(): res = res.replace(f"{{{k}}}", str(v))
    return res

def is_valid_email(email):
    return bool(re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', str(email)))

# --- WORLDPASS API FONKSİYONU ---
def worldpass_login(email: str, password: str):
    try:
        resp = requests.post(
            WORLDPASS_LOGIN_URL,
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code != 200:
            return None, f"Giriş Başarısız: Sunucu Hatası ({resp.status_code})"
        
        data = resp.json()
        if "user" not in data:
            return None, "Hatalı cevap formatı."
            
        return data, None
    except Exception as e:
        return None, f"Bağlantı Hatası: {e}"

# ================== STATE BAŞLATMA ==================
if "current_user" not in st.session_state: st.session_state.current_user = None
if "smtp_accounts" not in st.session_state: st.session_state.smtp_accounts = []
if "mail_subject" not in st.session_state: st.session_state.mail_subject = "İş Birliği Hakkında"
if "mail_body" not in st.session_state: st.session_state.mail_body = "Merhaba {Yetkili},\n\n..."
if "loaded_data" not in st.session_state: st.session_state.loaded_data = None
if "email_column" not in st.session_state: st.session_state.email_column = None

config = load_json(CONFIG_FILE)
if not config: config = {"users": [], "smtp_defaults": {"server": "smtp.gmail.com", "port": 587}}

# ================== 1. GİRİŞ EKRANI (WorldPass Geri Geldi) ==================
if not st.session_state.current_user:
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class='login-box'>
            <h1 style='color:#3b82f6 !important; margin:0;'>🧬 Heptapus</h1>
            <h3 style='font-weight:400; color:white !important; margin-top:5px;'>SponsorBot Giriş</h3>
            <p style='color:#94a3b8 !important;'>WorldPass veya Yerel Hesap ile devam et</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab_local, tab_wp = st.tabs(["🔐 Yerel Giriş", "🌍 WorldPass"])
        
        # --- YEREL GİRİŞ ---
        with tab_local:
            with st.form("login_local"):
                u = st.text_input("Kullanıcı Adı")
                p = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş Yap (Yerel)", type="primary"):
                    if not config.get("users"):
                        st.error("Yerel kullanıcı bulunamadı.")
                    else:
                        user_found = next((user for user in config["users"] if user["username"] == u), None)
                        if user_found and verify_password(p, user_found.get("password_hash", "")):
                            st.session_state.current_user = user_found
                            st.rerun()
                        else:
                            st.error("Hatalı kullanıcı adı veya şifre.")

        # --- WORLDPASS GİRİŞ (GERİ GELDİ) ---
        with tab_wp:
            st.info("Heptapus ID'niz ile giriş yapın.")
            with st.form("login_wp"):
                wp_email = st.text_input("WorldPass Email")
                wp_pass = st.text_input("Şifre", type="password")
                if st.form_submit_button("WorldPass ile Bağlan", type="primary"):
                    if not wp_email or not wp_pass:
                        st.error("Alanları doldurun.")
                    else:
                        data, err = worldpass_login(wp_email.strip(), wp_pass)
                        if err:
                            st.error(err)
                        else:
                            user_info = data.get("user", {})
                            email = user_info.get("email", wp_email).lower()
                            
                            # Admin kontrolü
                            mapped_role = "admin" if email in [e.lower() for e in ADMIN_EMAILS] else "sender"
                            
                            st.session_state.current_user = {
                                "username": email,
                                "role": mapped_role,
                                "auth_type": "worldpass",
                                "wp_token": data.get("token")
                            }
                            st.success("WorldPass bağlantısı başarılı!")
                            time.sleep(1)
                            st.rerun()
    st.stop()

# ================== 2. ANA PANEL ==================
user = st.session_state.current_user
role = user.get("role", "sender")
global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB": "Heptapus Group"
}

# --- SIDEBAR (Gelişmiş SMTP Yönetimi) ---
with st.sidebar:
    st.markdown(f"### 👤 {user['username']}")
    st.caption(f"Yöntem: {user.get('auth_type', 'local').upper()}")
    
    if st.button("Çıkış Yap"):
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📧 Gönderici Ayarları")
    
    with st.expander("➕ Yeni Hesap Ekle", expanded=False):
        # Hazır Sağlayıcı Seçimi
        provider = st.selectbox("E-posta Sağlayıcısı", list(SMTP_PRESETS.keys()))
        
        default_host = SMTP_PRESETS[provider]["host"]
        default_port = SMTP_PRESETS[provider]["port"]
        
        srv = st.text_input("SMTP Sunucusu", value=default_host)
        prt = st.number_input("Port", value=default_port)
        
        st.caption("Giriş Bilgileri")
        em = st.text_input("E-posta Adresi")
        pw = st.text_input("Uygulama Şifresi", type="password", help="Gmail/Outlook için 'App Password' gerekir.")
        
        if st.button("Kaydet ve Test Et"):
            if not em or not pw:
                st.error("E-posta ve şifre zorunlu.")
            else:
                try:
                    s = smtplib.SMTP(srv, prt)
                    s.starttls()
                    s.login(em, pw)
                    s.quit()
                    
                    st.session_state.smtp_accounts.append({"server": srv, "port": prt, "email": em, "password": pw})
                    st.success("✅ Hesap eklendi.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Bağlantı Hatası: {e}")

    if st.session_state.smtp_accounts:
        st.markdown("#### Aktif Hesaplar")
        for i, acc in enumerate(st.session_state.smtp_accounts):
            with st.container():
                c1, c2 = st.columns([4, 1])
                c1.code(acc['email'])
                if c2.button("Sil", key=f"del_{i}"):
                    st.session_state.smtp_accounts.pop(i)
                    st.rerun()
    else:
        st.warning("⚠️ Henüz gönderici hesabı eklenmedi.")

# --- HEADER ---
st.markdown(f"""
<div class='hero'>
    <h1>Heptapus Kontrol Paneli</h1>
    <p>WorldPass Entegrasyonu Aktif. Akıllı Zamanlayıcı Hazır.</p>
</div>
""", unsafe_allow_html=True)

# --- SEKMELER ---
tab_data, tab_template, tab_send, tab_logs = st.tabs([
    "📂 1. Hedef Kitle", 
    "📝 2. İçerik Tasarımı", 
    "⏱️ 3. Planla & Gönder", 
    "📊 4. Raporlar"
])

# ================== TAB 1: VERİ ==================
with tab_data:
    col_up, col_stat = st.columns([1, 1])
    with col_up:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Excel Yükle")
        uploaded_file = st.file_uploader("Dosya Seç (.xlsx)", type=["xlsx"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file).fillna("").astype(str)
                st.session_state.loaded_data = df
                st.success(f"{len(df)} kayıt yüklendi.")
            except Exception as e:
                st.error(f"Hata: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_stat:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Sütun Eşleştirme")
        if st.session_state.loaded_data is not None:
            df = st.session_state.loaded_data
            st.session_state.email_column = st.selectbox("E-posta Sütunu", df.columns)
            valid = df[st.session_state.email_column].apply(is_valid_email).sum()
            st.metric("Gönderilebilir Mail Sayısı", valid, f"Toplam: {len(df)}")
            st.dataframe(df.head(3), use_container_width=True)
        else:
            st.info("Veri bekleniyor...")
        st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 2: ŞABLON ==================
with tab_template:
    col_ed, col_man = st.columns([2, 1])
    with col_ed:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("E-posta İçeriği")
        st.session_state.mail_subject = st.text_input("Konu", st.session_state.mail_subject)
        st.session_state.mail_body = st.text_area("İçerik (HTML)", st.session_state.mail_body, height=300)
        st.session_state.files = st.file_uploader("Dosya Ekleri", accept_multiple_files=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_man:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Hızlı İşlemler")
        templates = load_json(TEMPLATE_FILE)
        
        # Şablon Yükle
        if templates:
            secilen = st.selectbox("Şablon Seç", [t["name"] for t in templates])
            if st.button("Şablonu Uygula"):
                t = next((x for x in templates if x["name"] == secilen), None)
                if t:
                    st.session_state.mail_subject = t["subject"]
                    st.session_state.mail_body = t["body"]
                    st.rerun()
        
        # Kaydet
        st.divider()
        new_name = st.text_input("Yeni Şablon Adı")
        if st.button("Kaydet"):
            templates.append({"name": new_name, "subject": st.session_state.mail_subject, "body": st.session_state.mail_body})
            save_json(TEMPLATE_FILE, templates)
            st.success("Kaydedildi!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 3: GÖNDERİM ==================
with tab_send:
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    
    if st.session_state.loaded_data is None or not st.session_state.smtp_accounts:
        st.warning("⚠️ Lütfen önce Veri Yükleyin ve Hesap Ekleyin.")
    else:
        c1, c2, c3 = st.columns([2, 1, 1])
        camp_name = c1.text_input("Kampanya Adı", "Kampanya 1")
        is_dry_run = c2.toggle("Dry Run (Test)", value=True)
        enable_schedule = c3.toggle("🕒 Zamanla", value=False)

        start_time = datetime.now()
        
        # Zamanlayıcı UI
        if enable_schedule:
            st.info("ℹ️ Zamanlayıcı çalışırken bu sekmeyi kapatmayın.")
            sc1, sc2 = st.columns(2)
            sch_date = sc1.date_input("Tarih", datetime.now())
            sch_time = sc2.time_input("Saat", (datetime.now() + timedelta(minutes=10)).time())
            start_time = datetime.combine(sch_date, sch_time)
            
            if start_time < datetime.now():
                st.error("Lütfen ileri bir tarih seçin.")

        st.divider()
        
        # Başlat Butonu
        btn_text = f"⏳ {start_time.strftime('%d.%m %H:%M')} İçin Planla" if enable_schedule else "🚀 Hemen Gönder"
        
        if st.button(btn_text, type="primary"):
            # Zamanlayıcı Bekleme
            if enable_schedule:
                placeholder = st.empty()
                while datetime.now() < start_time:
                    diff = start_time - datetime.now()
                    placeholder.warning(f"⏳ Kalan Süre: {str(diff).split('.')[0]}")
                    time.sleep(1)
                placeholder.empty()

            # GÖNDERİM BAŞLIYOR
            st.toast("Gönderim başladı!")
            status_container = st.status("Gönderim Durumu", expanded=True)
            df_target = st.session_state.loaded_data
            total = len(df_target)
            bar = status_container.progress(0)
            
            success = 0
            logs = []
            
            # SMTP Bağlantılarını Hazırla
            conns = []
            if not is_dry_run:
                for acc in st.session_state.smtp_accounts:
                    try:
                        s = smtplib.SMTP(acc['server'], acc['port'])
                        s.starttls()
                        s.login(acc['email'], acc['password'])
                        conns.append({"c": s, "e": acc['email']})
                    except: pass
            
            if not is_dry_run and not conns:
                status_container.error("SMTP Bağlantısı kurulamadı!")
                st.stop()

            # Loop
            for i, row in df_target.iterrows():
                email = str(row[st.session_state.email_column]).strip()
                subj = render_template(st.session_state.mail_subject, row.to_dict(), global_ctx)
                body = render_template(st.session_state.mail_body, row.to_dict(), global_ctx)
                
                stat_code = "UNKNOWN"
                
                if is_dry_run:
                    status_container.write(f"📝 [Test] {email}")
                    stat_code = "SIMULATED"
                    time.sleep(0.05)
                else:
                    try:
                        delay = random.uniform(2.0, 5.0) 
                        time.sleep(delay)
                        
                        acc = conns[i % len(conns)]
                        msg = MIMEMultipart()
                        msg['From'] = acc['e']
                        msg['To'] = email
                        msg['Subject'] = subj
                        msg.attach(MIMEText(body, 'html'))
                        
                        if st.session_state.files:
                            for f in st.session_state.files:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(f.getvalue())
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', f"attachment; filename={f.name}")
                                msg.attach(part)
                                
                        acc['c'].sendmail(acc['e'], email, msg.as_string())
                        status_container.write(f"✅ Gönderildi: {email} ({delay:.1f}s)")
                        stat_code = "SENT_OK"
                        success += 1
                    except Exception as e:
                        status_container.write(f"❌ Hata {email}: {e}")
                        stat_code = "ERROR"

                logs.append({"date": str(datetime.now()), "email": email, "status": stat_code, "campaign": camp_name})
                bar.progress((i+1)/total)

            # Bitiş
            if not is_dry_run:
                for c in conns: c['c'].quit()
                existing = load_json(HISTORY_FILE)
                existing.extend(logs)
                save_json(HISTORY_FILE, existing)

            status_container.update(label=f"Bitti! {success}/{total} Başarılı", state="complete")
            st.balloons()
            
    st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 4: RAPOR ==================
with tab_logs:
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    hist = load_json(HISTORY_FILE)
    if hist:
        df_h = pd.DataFrame(hist)
        st.metric("Toplam Log", len(df_h))
        st.dataframe(df_h, use_container_width=True)
        st.download_button("İndir CSV", df_h.to_csv().encode('utf-8'), "rapor.csv", "text/csv")
    else:
        st.info("Kayıt yok.")
    st.markdown("</div>", unsafe_allow_html=True)