import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time
import random
import json
import os
import re
from datetime import datetime
import altair as alt
import hashlib
import hmac
import io
import requests

# ================== AYARLAR & KONFİGÜRASYON ==================
st.set_page_config(
    page_title="Heptapus SponsorBot",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

# Dosya Yolları
HISTORY_FILE = "gonderim_gecmisi.json"
CONFIG_FILE = "config_settings.json"
TEMPLATE_FILE = "mail_sablonlari.json"
BLACKLIST_FILE = "blacklist.json"

# WorldPass Ayarları
WORLDPASS_LOGIN_URL = "https://worldpass-beta.heptapusgroup.com/api/user/login"
ADMIN_EMAILS = ["sametutku64@gmail.com"]

# Yetki Matrisi
ROLE_PERMISSIONS = {
    "admin": {"send": True, "edit_templates": True, "view_analytics": True, "manage_users": True},
    "sender": {"send": True, "edit_templates": True, "view_analytics": False, "manage_users": False},
    "viewer": {"send": False, "edit_templates": False, "view_analytics": True, "manage_users": False}
}

# ================== DÜZELTİLMİŞ & SAĞLAMLAŞTIRILMIŞ CSS ==================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* TEMEL DEĞİŞKENLER (Dark Mode Odaklı) */
    :root {
        --bg-color: #0e1117;
        --card-bg: #1e293b;
        --sidebar-bg: #111827;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --accent: #3b82f6;
        --border: #334155;
        --input-bg: #0f172a;
    }

    /* GENEL YAPI */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
    }
    
    /* Ana Arka Plan */
    .stApp {
        background-color: var(--bg-color);
    }

    /* KART TASARIMI (Görünürlük Sorunu Çözüldü) */
    .stCard {
        background-color: var(--card-bg);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        color: var(--text-primary); /* Yazı rengini zorla */
    }
    
    .stCard h1, .stCard h2, .stCard h3, .stCard h4, .stCard p, .stCard span, .stCard label {
        color: var(--text-primary) !important;
    }

    /* INPUT ALANLARI (Beyaz/Beyaz Sorunu Çözümü) */
    /* Streamlit inputlarının içini ve yazısını zorla */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"] {
        background-color: var(--input-bg) !important;
        border-color: var(--border) !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Input içi yazı rengi */
    input[type="text"], input[type="password"], input[type="number"], textarea {
        color: white !important;
        background-color: transparent !important;
    }

    /* Selectbox açılır menü */
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: var(--card-bg) !important;
        color: white !important;
    }

    /* HERO ALANI */
    .hero {
        background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
        color: white;
        padding: 32px;
        border-radius: 16px;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.4);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .hero h1 { color: white !important; margin-bottom: 0.5rem; }
    .hero p { color: rgba(255,255,255,0.9) !important; }

    /* KPI KARTLARI */
    .kpi-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .kpi-card h4 { color: var(--text-secondary) !important; font-size: 0.9rem; margin: 0; }
    .kpi-card p { color: var(--text-primary) !important; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0; }

    /* SIDEBAR DÜZELTMELERİ */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 1px solid var(--border);
    }
    
    .sidebar-card {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .sidebar-header {
        display: flex; gap: 12px; align-items: center;
        background: rgba(255,255,255,0.05);
        padding: 16px; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid var(--border);
    }
    .sidebar-avatar {
        width: 42px; height: 42px; background: #3b82f6; color: white;
        border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold;
    }
    .sidebar-note { color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .sidebar-stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }
    .sidebar-stat { background: rgba(0,0,0,0.2); padding: 8px; border-radius: 8px; text-align: center; }
    .sidebar-stat span { display: block; font-size: 0.7rem; color: var(--text-secondary); }
    .sidebar-stat strong { display: block; font-size: 1rem; color: white; }
    
    /* BUTONLAR */
    .stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.3);
    }
    
    /* METRIC WIDGET DÜZELTMESİ */
    div[data-testid="stMetric"] {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 15px;
    }
    div[data-testid="stMetricLabel"] p { color: var(--text-secondary) !important; }
    div[data-testid="stMetricValue"] div { color: var(--text-primary) !important; }

    /* TAGS */
    .stat-pill {
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
        color: white; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; display: inline-block; margin-right: 8px;
    }
    .tag {
        background: #312e81; color: #a5b4fc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-family: monospace;
    }
    
    /* STEPPER */
    .stepper { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
    .step { flex: 1; background: var(--card-bg); border: 1px solid var(--border); padding: 15px; border-radius: 10px; min-width: 200px; }
    .step-title { color: var(--accent); font-weight: bold; margin-bottom: 5px; }
    .step { color: var(--text-secondary); font-size: 0.9rem; }
    
    /* LOGIN BOX */
    .login-box {
        background: var(--card-bg);
        padding: 40px;
        border-radius: 16px;
        border: 1px solid var(--border);
        text-align: center;
        max-width: 400px;
        margin: 50px auto;
    }
    .login-box h1, .login-box h2, .login-box h3 { color: white !important; }
    .login-box p { color: var(--text-secondary) !important; }

</style>
""", unsafe_allow_html=True)

# ================== FONKSİYONLAR ==================
def load_json(filename):
    if not os.path.exists(filename):
        return [] if ("gecmisi" in filename or "sablon" in filename) else {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [] if ("gecmisi" in filename or "sablon" in filename) else {}

def save_json(filename, data, mode="w"):
    if mode == "a" and os.path.exists(filename):
        current = load_json(filename)
        if isinstance(current, list):
            current.append(data)
            data = current
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash) if password_hash else False

def get_user(cfg, username):
    return next((u for u in cfg.get("users", []) if u.get("username") == username), None)

def has_permission(role, permission):
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS.get("viewer", {})).get(permission, False)

def is_valid_email(email):
    return bool(re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', str(email)))

def render_template(text, row_data, global_ctx):
    if not text:
        return ""
    res = str(text)
    for k, v in row_data.items():
        res = res.replace(f"{{{k}}}", str(v))
    for k, v in global_ctx.items():
        res = res.replace(f"{{{k}}}", str(v))
    return res

def open_smtp(acc):
    s = smtplib.SMTP(acc['server'], acc['port'])
    s.starttls()
    s.login(acc['email'], acc['password'])
    return s

def send_mail_single(smtp_conn, sender, to, sub, body, files):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = sub
    msg.attach(MIMEText(body, 'html'))
    if files:
        for f in files:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.getvalue())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={f.name}")
            msg.attach(part)
    smtp_conn.sendmail(sender, to, msg.as_string())

def load_blacklist():
    data = load_json(BLACKLIST_FILE)
    if isinstance(data, list):
        return set(str(e).lower() for e in data)
    return set()

def save_blacklist(blacklist_set):
    data = sorted(list(set(str(e).lower() for e in blacklist_set)))
    save_json(BLACKLIST_FILE, data, mode="w")

def worldpass_login(email: str, password: str):
    try:
        resp = requests.post(
            WORLDPASS_LOGIN_URL,
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code != 200:
            return None, f"WorldPass login başarısız: HTTP {resp.status_code}"
        data = resp.json()
        if "user" not in data:
            return None, "WorldPass cevabında 'user' alanı yok."
        return data, None
    except Exception as e:
        return None, f"WorldPass isteği hata verdi: {e}"

# ================== STATE YÖNETİMİ ==================
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "smtp_accounts" not in st.session_state:
    st.session_state.smtp_accounts = []
if "mail_body" not in st.session_state:
    st.session_state.mail_body = "Merhaba {Yetkili},\n\n..."
if "mail_subject" not in st.session_state:
    st.session_state.mail_subject = "İş Birliği Fırsatı"
if "club_name" not in st.session_state:
    st.session_state.club_name = "Heptapus Group"
if "subject_a" not in st.session_state:
    st.session_state.subject_a = ""
if "subject_b" not in st.session_state:
    st.session_state.subject_b = ""
if "campaign_name" not in st.session_state:
    st.session_state.campaign_name = "Genel"
if "show_smtp_form" not in st.session_state:
    st.session_state.show_smtp_form = False
if "sending_active" not in st.session_state:
    st.session_state.sending_active = False

config_data = load_json(CONFIG_FILE)
if not config_data or not isinstance(config_data, dict):
    config_data = {
        "users": [],
        "smtp_defaults": {
            "server": "smtp.gmail.com",
            "port": 587
        }
    }

# ================== LOGIN EKRANI ==================
if not st.session_state.current_user:
    # Kullanıcı yoksa uyarı
    if not config_data.get("users"):
        st.markdown("<div class='login-box'><h2>🔐 Yönetici Gerekli</h2>", unsafe_allow_html=True)
        example_hash = hash_password("admin123")
        st.warning(f"Lütfen config dosyasına kullanıcı ekleyin.\nHash: {example_hash}")
        st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class='login-box'>
            <h1 style='color:#3b82f6 !important;'>🧬 Heptapus</h1>
            <h3 style='font-weight:400;'>SponsorBot Panel</h3>
            <p>Kurumsal iletişim ve sponsorluk yönetim sistemi</p>
        </div>
        """, unsafe_allow_html=True)

        tab_local, tab_wp = st.tabs(["Yerel Giriş", "WorldPass"])
        
        with tab_local:
            with st.form("login_form_local"):
                username = st.text_input("Kullanıcı Adı")
                password = st.text_input("Şifre", type="password")
                submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
                if submitted:
                    user = get_user(config_data, username.strip())
                    if user and verify_password(password, user.get("password_hash", "")):
                        st.session_state.current_user = {
                            "username": user["username"],
                            "role": user.get("role", "sender"),
                            "auth_type": "local"
                        }
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre.")

        with tab_wp:
            with st.form("login_form_worldpass"):
                wp_email = st.text_input("WorldPass Email")
                wp_pass = st.text_input("WorldPass Şifre", type="password")
                submitted_wp = st.form_submit_button("WorldPass Giriş", type="primary", use_container_width=True)
                if submitted_wp:
                    data, err = worldpass_login(wp_email.strip(), wp_pass)
                    if err:
                        st.error(err)
                    else:
                        user_info = data.get("user", {})
                        email = user_info.get("email", wp_email).lower()
                        mapped_role = "admin" if email in [e.lower() for e in ADMIN_EMAILS] else "sender"
                        st.session_state.current_user = {
                            "username": email,
                            "role": mapped_role,
                            "auth_type": "worldpass"
                        }
                        st.rerun()
    st.stop()

# ================== ANA UYGULAMA ==================
user = st.session_state.current_user
role = user.get("role", "viewer")

# GLOBAL CONTEXT
global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB_NAME": st.session_state.club_name,
    "CAMPAIGN_NAME": st.session_state.get("campaign_name", "Genel")
}

history_buffer = load_json(HISTORY_FILE)
if not isinstance(history_buffer, list): history_buffer = []
sent_ok = sum(1 for item in history_buffer if item.get("status") == "SENT_OK")
success_rate = int(sent_ok / len(history_buffer) * 100) if history_buffer else 0
blacklist_snapshot = load_blacklist()

# --- SIDEBAR ---
with st.sidebar:
    username = user.get("username", "user")
    initials = username[:2].upper()
    
    st.markdown(f"""
        <div class='sidebar-header'>
            <div class='sidebar-avatar'>{initials}</div>
            <div>
                <p class='sidebar-note'>Aktif</p>
                <h3 style='margin:0; font-size:1rem; color:white;'>{username.split('@')[0]}</h3>
                <span style='font-size:0.7rem; color:#94a3b8;'>{role.upper()}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

    st.markdown(f"""
        <div class='sidebar-card'>
            <p class='sidebar-note'>İstatistikler</p>
            <div class='sidebar-stat-grid'>
                <div class='sidebar-stat'><span>SMTP</span><strong>{len(st.session_state.smtp_accounts)}</strong></div>
                <div class='sidebar-stat'><span>Log</span><strong>{len(history_buffer)}</strong></div>
                <div class='sidebar-stat'><span>Oran</span><strong>%{success_rate}</strong></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if has_permission(role, "send"):
        st.markdown("<p class='sidebar-note' style='margin-top:20px;'>Hızlı İşlemler</p>", unsafe_allow_html=True)
        if st.button("➕ SMTP Ekle", use_container_width=True):
            st.session_state.show_smtp_form = True

# SMTP Modal
if st.session_state.get("show_smtp_form"):
    with st.expander("Yeni SMTP Hesabı", expanded=True):
        with st.form("new_smtp"):
            srv = st.text_input("Sunucu", "smtp.gmail.com")
            prt = st.number_input("Port", 587)
            em = st.text_input("Email")
            pw = st.text_input("Uygulama Şifresi", type="password")
            if st.form_submit_button("Kaydet"):
                st.session_state.smtp_accounts.append({"server": srv, "port": prt, "email": em, "password": pw})
                st.session_state.show_smtp_form = False
                st.success("Eklendi.")
                st.rerun()

# HERO HEADER
st.markdown(f"""
    <div class='hero'>
        <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
            <div>
                <div class='stat-pill'>User: {username}</div>
                <div class='stat-pill'>Role: {role}</div>
                <h1 style='margin-top:10px;'>Kontrol Merkezi</h1>
                <p>Kampanyalarını yönet, analitikleri izle.</p>
            </div>
            <div style='text-align:right;'>
                <p style='margin:0; opacity:0.7;'>Kampanya</p>
                <h2 style='margin:0; font-size:1.5rem;'>{global_ctx['CAMPAIGN_NAME']}</h2>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# KPI ROW
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><h4>TOPLAM LOG</h4><p>{len(history_buffer)}</p></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><h4>BAŞARI</h4><p>%{success_rate}</p></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><h4>BLACKLIST</h4><p>{len(blacklist_snapshot)}</p></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><h4>ŞABLONLAR</h4><p>{len(load_json(TEMPLATE_FILE))}</p></div>", unsafe_allow_html=True)

# STEPPER
st.markdown("""
<div class='stepper'>
    <div class='step'><div class='step-title'>1. Veri</div>Excel yükle & doğrula</div>
    <div class='step'><div class='step-title'>2. Şablon</div>Mesajı tasarla</div>
    <div class='step'><div class='step-title'>3. Gönderim</div>Dry-run & Başlat</div>
</div>
""", unsafe_allow_html=True)

# TABS
t1, t2, t3, t4 = st.tabs(["📂 1. Veri Yükle", "📝 2. Şablon", "🚀 3. Gönderim", "📊 4. Analitik"])

df = None
email_col = None

# TAB 1: DATA
with t1:
    col_up, col_info = st.columns([1, 1])
    with col_up:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Excel Dosyası")
        uploaded_file = st.file_uploader("Dosyayı buraya sürükle", type=["xlsx"])
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_info:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.info("İpucu: Sütun adlarını {SütunAdi} şeklinde şablonda kullanabilirsin.")
        st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file).fillna("").astype(str)
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            email_col = st.selectbox("E-posta Sütunu Seç", df.columns)
            valid = df[email_col].apply(is_valid_email).sum()
            c1, c2 = st.columns(2)
            c1.metric("Toplam Kayıt", len(df))
            c2.metric("Geçerli Mail", valid)
            st.dataframe(df.head(), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Hata: {e}")

# TAB 2: TEMPLATE
with t2:
    c_edit, c_view = st.columns([1.5, 1])
    with c_edit:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Mesaj İçeriği")
        st.session_state.mail_subject = st.text_input("Konu", st.session_state.mail_subject)
        
        tags = ["{Yetkili}", "{Sirket}", "{CLUB_NAME}"]
        st.markdown(" ".join([f"<span class='tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
        
        st.session_state.mail_body = st.text_area("HTML İçerik", st.session_state.mail_body, height=300)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.session_state.files = st.file_uploader("Ek Dosyalar", accept_multiple_files=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_view:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Önizleme")
        if df is not None and not df.empty:
            p_idx = st.number_input("Satır No", 0, len(df)-1, 0)
            row = df.iloc[p_idx].to_dict()
            prev_s = render_template(st.session_state.mail_subject, row, global_ctx)
            prev_b = render_template(st.session_state.mail_body, row, global_ctx)
            st.markdown(f"**Konu:** {prev_s}")
            st.markdown("---")
            st.components.v1.html(prev_b, height=400, scrolling=True)
        else:
            st.warning("Veri yüklenmedi.")
        st.markdown("</div>", unsafe_allow_html=True)

# TAB 3: SEND
with t3:
    if not has_permission(role, "send"):
        st.error("Yetkisiz erişim.")
    elif df is None or email_col is None:
        st.warning("Veri yükleyin.")
    elif not st.session_state.smtp_accounts:
        st.error("SMTP hesabı yok.")
    else:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        st.session_state.campaign_name = col_c1.text_input("Kampanya Adı", st.session_state.campaign_name)
        is_dry_run = col_c2.toggle("Dry Run (Test Modu)", value=True)
        
        st.markdown("#### Test Gönder")
        test_mail = st.text_input("Test Alıcısı")
        if st.button("🧪 Test Maili Gönder"):
            try:
                acc = st.session_state.smtp_accounts[0]
                conn = open_smtp(acc)
                test_row = df.iloc[0].to_dict()
                s = render_template(st.session_state.mail_subject, test_row, global_ctx)
                b = render_template(st.session_state.mail_body, test_row, global_ctx)
                send_mail_single(conn, acc['email'], test_mail, f"[TEST] {s}", b, st.session_state.files)
                conn.quit()
                st.success("Test başarılı.")
            except Exception as e:
                st.error(f"Hata: {e}")

        st.markdown("---")
        if st.button("🚀 GÖNDERİMİ BAŞLAT", type="primary", use_container_width=True):
            st.session_state.sending_active = True
        
        if st.session_state.sending_active:
            progress = st.progress(0)
            status_area = st.empty()
            log_area = st.container()
            
            # Gönderim Mantığı (Basitleştirilmiş)
            conns = []
            if not is_dry_run:
                for acc in st.session_state.smtp_accounts:
                    try: conns.append({"c": open_smtp(acc), "email": acc["email"]})
                    except: pass
            
            if not is_dry_run and not conns:
                st.error("SMTP Bağlantı hatası!")
                st.session_state.sending_active = False
            else:
                sent_batch = []
                for i, row in df.iterrows():
                    target = str(row[email_col]).lower()
                    if target in blacklist_snapshot:
                        log_area.warning(f"Blacklist: {target}")
                        continue
                    
                    try:
                        subj = render_template(st.session_state.mail_subject, row.to_dict(), global_ctx)
                        body = render_template(st.session_state.mail_body, row.to_dict(), global_ctx)
                        
                        if is_dry_run:
                            log_area.info(f"Dry-Run: {target}")
                            status = "SIMULATED"
                            time.sleep(0.1)
                        else:
                            active = conns[i % len(conns)]
                            send_mail_single(active["c"], active["email"], target, subj, body, st.session_state.files)
                            log_area.success(f"Gönderildi: {target}")
                            status = "SENT_OK"
                            time.sleep(2)
                        
                        sent_batch.append({"date": str(datetime.now()), "email": target, "status": status, "campaign": st.session_state.campaign_name})
                    except Exception as e:
                        log_area.error(f"Hata {target}: {e}")
                        sent_batch.append({"date": str(datetime.now()), "email": target, "status": "ERROR", "campaign": st.session_state.campaign_name})
                    
                    progress.progress((i+1)/len(df))
                
                if not is_dry_run:
                    exist = load_json(HISTORY_FILE)
                    if isinstance(exist, list): exist.extend(sent_batch)
                    save_json(HISTORY_FILE, exist)
                
                st.success("İşlem bitti.")
                st.session_state.sending_active = False
        st.markdown("</div>", unsafe_allow_html=True)

# TAB 4: ANALYTICS
with t4:
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    if history_buffer:
        df_hist = pd.DataFrame(history_buffer)
        st.dataframe(df_hist, use_container_width=True)
        st.download_button("İndir CSV", df_hist.to_csv().encode('utf-8'), "log.csv", "text/csv")
    else:
        st.info("Kayıt yok.")
    st.markdown("</div>", unsafe_allow_html=True)