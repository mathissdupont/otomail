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
WORLDPASS_LOGIN_URL = "https://worldpass-beta.heptapusgroup.com/api/user/login"  # gerekirse değiştir
ADMIN_EMAILS = ["sametutku64@gmail.com"]  # WorldPass üzerinden admin sayılacak adresler

# Yetki Matrisi
ROLE_PERMISSIONS = {
    "admin": {"send": True, "edit_templates": True, "view_analytics": True, "manage_users": True},
    "sender": {"send": True, "edit_templates": True, "view_analytics": False, "manage_users": False},
    "viewer": {"send": False, "edit_templates": False, "view_analytics": True, "manage_users": False}
}

# ================== MODERN CSS & TEMA ==================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    :root {
        --surface-light: #ffffff;
        --surface-dark: #111827;
        --border-light: #e5e7eb;
        --border-dark: #1f2937;
        --text-light: #0f172a;
        --text-dark: #f1f5f9;
        --muted-light: #64748b;
        --muted-dark: #94a3b8;
        --sidebar-light: #f8fafc;
        --sidebar-dark: #0f172a;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stCard {
        background-color: var(--surface-light);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid var(--border-light);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
        color: var(--text-light);
    }
    .hero {
        background: linear-gradient(135deg, #1d4ed8 0%, #9333ea 100%);
        color: white;
        padding: 32px;
        border-radius: 18px;
        margin-bottom: 30px;
        box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.45);
        border: 1px solid rgba(255,255,255,0.15);
    }
    .hero h1 {
        color: white;
        margin-bottom: 0.3rem;
        font-size: 2rem;
    }
    .hero p {
        color: rgba(255,255,255,0.8);
        margin: 0.2rem 0;
    }
    .stat-pill {
        display: inline-flex;
        gap: 6px;
        align-items: center;
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 999px;
        padding: 6px 14px;
        font-size: 0.85rem;
        margin-right: 8px;
        color: #0f172a;
        font-weight: 600;
    }
    .kpi-card {
        border-radius: 16px;
        padding: 18px;
        border: 1px solid var(--border-light);
        background: var(--surface-light);
        box-shadow: 0 20px 35px -18px rgba(15, 23, 42, 0.35);
    }
    .kpi-card h4 {
        margin: 0;
        font-size: 0.85rem;
        color: var(--muted-light);
    }
    .kpi-card p {
        margin: 6px 0 0;
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-light);
    }
    .tag {
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        font-size: 0.75rem;
        background: #e0e7ff;
        color: #312e81;
        margin-right: 6px;
    }
    .stepper {
        display: flex;
        gap: 16px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .stepper .step {
        flex: 1 1 200px;
        border-radius: 12px;
        border: 1px dashed #c7d2fe;
        padding: 14px 18px;
        background: rgba(99,102,241,0.08);
    }
    .step .step-title {
        font-weight: 600;
        color: #312e81;
        margin-bottom: 6px;
    }
    .sidebar-shell {
        display: flex;
        flex-direction: column;
        gap: 18px;
    }
    .sidebar-header {
        display: flex;
        gap: 14px;
        align-items: center;
        padding: 18px;
        margin-bottom: 16px;
        border-radius: 16px;
        border: 1px solid var(--border-light);
        background: linear-gradient(135deg, rgba(15,23,42,0.05), rgba(59,130,246,0.12));
    }
    .sidebar-avatar {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        background: #1d4ed8;
        color: #fff;
        font-weight: 700;
        font-size: 1.2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 0 0 2px rgba(255,255,255,0.3);
    }
    .sidebar-tag {
        display: inline-flex;
        align-items: center;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        background: rgba(59,130,246,0.15);
        color: #1d4ed8;
        font-weight: 600;
    }
    .sidebar-card {
        border-radius: 16px;
        border: 1px solid var(--border-light);
        padding: 16px 18px;
        background: var(--surface-light);
        margin-bottom: 0;
        box-shadow: 0 12px 20px -16px rgba(15,23,42,0.4);
    }
    .sidebar-card p,
    .sidebar-card span,
    .sidebar-card strong {
        color: var(--text-light);
    }
    .sidebar-note {
        margin: 0 0 8px;
        font-size: 0.8rem;
        color: var(--muted-light);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .sidebar-stat-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
    }
    .sidebar-stat {
        padding: 10px 12px;
        border-radius: 12px;
        background: rgba(99,102,241,0.08);
    }
    .sidebar-stat span {
        display: block;
        font-size: 0.75rem;
        color: var(--muted-light);
    }
    .sidebar-stat strong {
        display: block;
        margin-top: 4px;
        font-size: 1.1rem;
        color: var(--text-light);
    }
    .sidebar-chip {
        display: inline-flex;
        padding: 4px 10px;
        margin: 2px 4px 2px 0;
        border-radius: 999px;
        background: rgba(16,185,129,0.12);
        color: #047857;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .sidebar-empty {
        padding: 10px;
        border-radius: 10px;
        background: rgba(248,113,113,0.16);
        color: #991b1b;
        font-size: 0.85rem;
    }
    .sidebar-footer {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted-light);
        text-align: center;
    }
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: var(--surface-light);
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid var(--border-light);
        color: var(--text-light);
    }
    .stButton > button,
    .stLinkButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
        background: #1d4ed8;
        color: #fff;
        border: 1px solid rgba(15,23,42,0.1);
    }
    .stButton > button:hover,
    .stLinkButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--muted-light);
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-light);
        font-size: 1.8rem;
        font-weight: 700;
    }
    h1, h2, h3 {
        color: var(--text-light);
    }
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-light);
        border-right: 1px solid var(--border-light);
    }
    section[data-testid="stSidebar"] * {
        color: var(--text-light);
    }

    /* DARK THEME OVERRIDES */
    body[data-theme="dark"], [data-theme="dark"] .block-container {
        color: var(--text-dark);
    }
    body[data-theme="dark"] .stCard {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
        color: var(--text-dark);
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    body[data-theme="dark"] .login-box {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
        color: var(--text-dark);
        box-shadow: 0 15px 35px rgba(0,0,0,0.45);
    }
    body[data-theme="dark"] div[data-testid="stMetric"] {
        background-color: #0f172a;
        border-color: #1f2937;
    }
    body[data-theme="dark"] div[data-testid="stMetricLabel"] {
        color: var(--muted-dark);
    }
    body[data-theme="dark"] div[data-testid="stMetricValue"],
    body[data-theme="dark"] h1,
    body[data-theme="dark"] h2,
    body[data-theme="dark"] h3,
    body[data-theme="dark"] p,
    body[data-theme="dark"] label {
        color: var(--text-dark);
    }
    body[data-theme="dark"] section[data-testid="stSidebar"] {
        background-color: var(--sidebar-dark);
        border-right: 1px solid var(--border-dark);
    }
    body[data-theme="dark"] section[data-testid="stSidebar"] * {
        color: var(--text-dark) !important;
    }
    body[data-theme="dark"] .sidebar-header,
    body[data-theme="dark"] .sidebar-card {
        background-color: #0f172a;
        border-color: #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.6);
    }
    body[data-theme="dark"] .sidebar-stat {
        background: rgba(59,130,246,0.15);
    }
    body[data-theme="dark"] .sidebar-chip {
        background: rgba(16,185,129,0.25);
        color: #34d399;
    }
    body[data-theme="dark"] .stButton > button,
    body[data-theme="dark"] .stLinkButton > button {
        color: var(--text-dark);
        border: 1px solid rgba(148, 163, 184, 0.4);
        background-color: #1d4ed8;
    }
    body[data-theme="dark"] .stButton > button:hover,
    body[data-theme="dark"] .stLinkButton > button:hover {
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
    }
    body[data-theme="dark"] .stat-pill {
        background: rgba(15,23,42,0.4);
        border-color: rgba(148,163,184,0.4);
        color: var(--text-dark);
    }
    body[data-theme="dark"] .stSelectbox > div,
    body[data-theme="dark"] .stTextInput > div > div,
    body[data-theme="dark"] .stNumberInput > div > div {
        background-color: #0f172a !important;
        border-color: #1f2937 !important;
        color: var(--text-dark) !important;
    }
    body[data-theme="dark"] .stTextInput input,
    body[data-theme="dark"] .stNumberInput input,
    body[data-theme="dark"] .stTextArea textarea {
        color: var(--text-dark) !important;
    }
    body[data-theme="dark"] .stMarkdown, body[data-theme="dark"] .stCaption {
        color: var(--text-dark);
    }
    body[data-theme="dark"] .sidebar-note,
    body[data-theme="dark"] .sidebar-card p,
    body[data-theme="dark"] .sidebar-card span,
    body[data-theme="dark"] .sidebar-card strong,
    body[data-theme="dark"] .sidebar-footer {
        color: var(--text-dark);
    }
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
    """
    WorldPass backend login.
    Beklenen cevap:
    {
        "token": "...",
        "user": {
            "id": ...,
            "email": "...",
            "first_name": "...",
            "last_name": "...",
            "did": "...",
            "email_verified": false
        }
    }
    """
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
            "port": 587,
            "delay_min": 5,
            "delay_max": 15
        }
    }

# ================== LOGIN EKRANI ==================
if not st.session_state.current_user:
    # Kullanıcı yoksa kullanıcıyı config'e manuel eklemesi istenir
    if not config_data.get("users"):
        st.markdown("<div class='login-box'><h2>🔐 Yönetici Gerekli</h2>", unsafe_allow_html=True)
        example_hash = hash_password("admin123")
        st.warning(
            "Lütfen `config_settings.json` dosyasına en az bir kullanıcı ekleyin.\n\n"
            "Örnek kayıt:\n"
            f"```json\n{{\"username\": \"admin\", \"password_hash\": \"{example_hash}\", \"role\": \"admin\"}}\n```"
        )
        st.markdown(
            "<p style='color:#666;'>`password_hash` alanı için kendi şifrenizi `hash_password` fonksiyonundan geçirip değeri manuel yazmanız gerekir.</p></div>",
            unsafe_allow_html=True
        )
        st.stop()

    # Normal Login (Yerel + WorldPass)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='login-box'>
            <h1 style='color:#00629B;'>🧬 Heptapus</h1>
            <h3 style='font-weight:400;'>SponsorBot Panel</h3>
            <p style='color:#666; font-size: 0.9em;'>Kurumsal iletişim ve sponsorluk yönetim sistemi</p>
        </div>
        """, unsafe_allow_html=True)

        tab_local, tab_wp = st.tabs(["Yerel Giriş", "WorldPass ile Giriş"])

        # Yerel giriş
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
                        st.toast(f"Hoş geldin, {user['username']}!", icon="👋")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre.")

        # WorldPass ile giriş
        with tab_wp:
            st.caption("WorldPass hesabınla giriş yaparak SponsorBot'a eriş.")
            st.info("WorldPass, Heptapus ekosistemindeki tüm servisler için tek seferlik kurumsal oturum açma (SSO) katmanıdır.")
            st.link_button("WorldPass hesabı oluştur", "https://worldpass-beta.heptapusgroup.com/", type="secondary")
            with st.form("login_form_worldpass"):
                wp_email = st.text_input("WorldPass Email")
                wp_pass = st.text_input("WorldPass Şifre", type="password")
                submitted_wp = st.form_submit_button("WorldPass ile Giriş Yap", type="primary", use_container_width=True)
                if submitted_wp:
                    if not wp_email or not wp_pass:
                        st.error("Email ve şifre zorunlu.")
                    else:
                        data, err = worldpass_login(wp_email.strip(), wp_pass)
                        if err:
                            st.error(err)
                        else:
                            user_info = data.get("user", {})
                            email = user_info.get("email", wp_email).lower()

                            # Rol mapping
                            if email in [e.lower() for e in ADMIN_EMAILS]:
                                mapped_role = "admin"
                            else:
                                mapped_role = "sender"

                            st.session_state.current_user = {
                                "username": email,
                                "role": mapped_role,
                                "auth_type": "worldpass",
                                "wp_token": data.get("token"),
                                "wp_user": user_info
                            }
                            st.toast("WorldPass ile giriş başarılı! 🎉", icon="✅")
                            time.sleep(0.3)
                            st.rerun()
    st.stop()

# ================== ANA UYGULAMA ==================
user = st.session_state.current_user
role = user.get("role", "viewer")

# GLOBAL CONTEXT & ÖZETLER
global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB_NAME": st.session_state.club_name,
    "CAMPAIGN_NAME": st.session_state.get("campaign_name", "Genel")
}

history_buffer = load_json(HISTORY_FILE)
if not isinstance(history_buffer, list):
    history_buffer = []

sent_ok = sum(1 for item in history_buffer if item.get("status") == "SENT_OK")
success_rate = int(sent_ok / len(history_buffer) * 100) if history_buffer else 0
campaign_count = len({item.get("campaign", "-") for item in history_buffer if item.get("campaign")})
recent_campaign = history_buffer[-1].get("campaign", "Hazır Değil") if history_buffer else "Hazır Değil"
blacklist_snapshot = load_blacklist()
blacklist_total = len(blacklist_snapshot)

# --- SIDEBAR ---
with st.sidebar:
    username = user.get("username", "user")
    primary_initials = "".join([chunk[0] for chunk in re.split(r"[^a-zA-Z0-9]+", username.split("@")[0]) if chunk])[:2].upper()
    initials = primary_initials or username[:2].upper()
    template_data_snapshot = load_json(TEMPLATE_FILE)
    template_count = len(template_data_snapshot) if isinstance(template_data_snapshot, list) else 0
    smtp_count = len(st.session_state.smtp_accounts)
    history_total = len(history_buffer)

    st.markdown("<div class='sidebar-shell'>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class='sidebar-header'>
            <div class='sidebar-avatar'>{initials}</div>
            <div>
                <p class='sidebar-note'>Aktif Kullanıcı</p>
                <h3 style='margin:0;'>{username}</h3>
                <span class='sidebar-tag'>{role.upper()}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

    st.markdown(
        f"""
        <div class='sidebar-card'>
            <p class='sidebar-note'>Panel Özeti</p>
            <div class='sidebar-stat-grid'>
                <div class='sidebar-stat'><span>SMTP</span><strong>{smtp_count}</strong></div>
                <div class='sidebar-stat'><span>Şablon</span><strong>{template_count}</strong></div>
                <div class='sidebar-stat'><span>Log</span><strong>{history_total}</strong></div>
            </div>
            <p style='margin-top:12px;font-size:0.85rem;'>Aktif kampanya: <strong>{global_ctx['CAMPAIGN_NAME']}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if has_permission(role, "send"):
        st.markdown(
            """
            <div class='sidebar-card'>
                <p class='sidebar-note'>SMTP Havuzu</p>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.smtp_accounts:
            st.markdown("<div class='sidebar-empty'>Hesap eklenmedi</div>", unsafe_allow_html=True)
        else:
            chips = "".join([f"<span class='sidebar-chip'>{acc['email']}</span>" for acc in st.session_state.smtp_accounts])
            st.markdown(chips, unsafe_allow_html=True)

        if st.button("➕ Hesap Ekle", use_container_width=True):
            st.session_state.show_smtp_form = True

        st.markdown("</div>", unsafe_allow_html=True)

    if has_permission(role, "manage_users"):
        st.markdown(
            f"""
            <div class='sidebar-card'>
                <p class='sidebar-note'>Yönetim</p>
                <p style='margin:0;'>Toplam kullanıcı: <strong>{len(config_data.get('users', []))}</strong></p>
    st.markdown("<div class='sidebar-footer'>Heptapus SponsorBot © 2024</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
            """,
            unsafe_allow_html=True,
        )

    st.caption("Heptapus SponsorBot © 2024")

# SMTP modal
if st.session_state.get("show_smtp_form"):
    with st.form("new_smtp"):
        st.subheader("Yeni SMTP Hesabı")
        c1, c2 = st.columns(2)
        smtp_defaults = config_data.get("smtp_defaults", {})
        default_server = smtp_defaults.get("server", "smtp.gmail.com")
        default_port = int(smtp_defaults.get("port", 587))

        srv = c1.text_input("Sunucu", default_server)
        prt = c2.number_input("Port", min_value=1, max_value=65535, value=default_port)
        em = st.text_input("Email")
        pw = st.text_input("Uygulama Şifresi", type="password")
        submitted = st.form_submit_button("Kaydet")
        if submitted:
            if not em or not pw:
                st.error("Email ve şifre zorunlu.")
            else:
                st.session_state.smtp_accounts.append(
                    {"server": srv, "port": prt, "email": em, "password": pw}
                )
                st.session_state.show_smtp_form = False
                st.success("SMTP hesabı eklendi.")
                st.rerun()

st.markdown(
    f"""
    <div class='hero'>
        <div style='display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:space-between; align-items:flex-start;'>
            <div>
                <div class='stat-pill'>Aktif Kullanıcı · {user['username']}</div>
                <div class='stat-pill'>Rol · {role.upper()}</div>
                <h1>Heptapus SponsorBot Kontrol Merkezi</h1>
                <p>Kampanyalarını tek panelden kurgula, test et ve performansını takip et.</p>
            </div>
            <div style='text-align:right;'>
                <p>Güncel Kampanya</p>
                <h2 style='margin:0;color:#fff;'>{global_ctx['CAMPAIGN_NAME']}</h2>
                <p style='opacity:0.8;'>Son Aktivite: {recent_campaign}</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

kpi_cols = st.columns(4)
kpi_data = [
    ("Toplam Log", len(history_buffer)),
    ("Başarı Oranı", f"%{success_rate}"),
    ("Kampanya Çeşidi", campaign_count or "-"),
    ("Blacklist", blacklist_total),
]
for idx, col in enumerate(kpi_cols):
    title, value = kpi_data[idx]
    col.markdown(f"<div class='kpi-card'><h4>{title}</h4><p>{value}</p></div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class='stepper'>
        <div class='step'>
            <div class='step-title'>1 · Veri Kaynağı</div>
            Excel'i yükle, alanları doğrula ve temizle
        </div>
        <div class='step'>
            <div class='step-title'>2 · Şablon & İçerik</div>
            Dinamik placeholder'lar ve ekleri hazırlayıp test et
        </div>
        <div class='step'>
            <div class='step-title'>3 · Kampanya</div>
            A/B denemeleri, dry-run ve gerçek gönderime geç
        </div>
        <div class='step'>
            <div class='step-title'>4 · Analitik</div>
            Performans, log ve blacklist'i tek ekrandan izle
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sekmeler
t_data, t_tmpl, t_send, t_stat = st.tabs(
    ["📂 Veri Yükle", "📝 Şablon Editörü", "🚀 Gönderim Paneli", "📊 Analitik"]
)

# df / email_col başlangıç
df = None
email_col = None

# 1. VERİ
with t_data:
    st.markdown("### 📤 Hedef Kitle Operasyonları")
    st.markdown(
        """
        <div class='stCard'>
            <strong>İpucu:</strong> Yetkili adı, şirket, telefon, sektör gibi alanları da taşırsan dinamik placeholder'larla daha kişisel mailler gönderebilirsin.
        </div>
        """,
        unsafe_allow_html=True,
    )

    data_left, data_right = st.columns([1.2, 1])

    with data_left:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx"], help="Tek seferde maksimum 10.000 kayıt önerilir")
        helper_cols = st.columns([1, 1])
        with helper_cols[0]:
            dummy_data = pd.DataFrame([
                {"Yetkili": "Ahmet Yılmaz", "Email": "ahmet@ornek.com", "Sirket": "Tech A.Ş."},
                {"Yetkili": "Ayşe Demir", "Email": "ayse@demo.com", "Sirket": "Soft Ltd."}
            ])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                dummy_data.to_excel(writer, index=False)
            st.download_button(
                "📥 Şablonu Al",
                output.getvalue(),
                "ornek_liste.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with helper_cols[1]:
            st.caption("Sürükle-bırak desteklenir. Veri yükledikten sonra ilk 5 kayıt aşağıda görünür.")
        st.markdown("</div>", unsafe_allow_html=True)

    with data_right:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.markdown("#### Veri Sağlığı")
        st.caption("E-posta sütununu seçtikten sonra otomatik doğrulama yapılır.")
        st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file).fillna("").astype(str)

            with data_right:
                st.markdown("<div class='stCard'>", unsafe_allow_html=True)
                email_col = st.selectbox("📧 E-Posta Sütunu", df.columns, index=0)

                valid_mask = df[email_col].apply(is_valid_email)
                valid_count = valid_mask.sum()
                invalid_count = len(df) - valid_count

                m1, m2, m3 = st.columns(3)
                m1.metric("Toplam Kayıt", len(df))
                m2.metric("Geçerli Email", valid_count)
                m3.metric("Hatalı/Boş", invalid_count, delta_color="inverse")

                st.caption("İlk 5 kayıt")
                st.dataframe(df.head(), use_container_width=True)

                if invalid_count > 0:
                    with st.expander("⚠️ Hatalı Kayıtları İncele"):
                        st.dataframe(df[~valid_mask])
                st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Dosya okunamadı: {e}")

# 2. ŞABLON
with t_tmpl:
    st.markdown("### 🧱 Mesaj Tasarım Stüdyosu")
    st.caption("Metin, görsel ve değişkenleri aynı ekranda düzenleyip test et.")

    col_editor, col_preview = st.columns([1.5, 1])

    with col_editor:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Konu & Gövde")

        st.session_state.mail_subject = st.text_input(
            "Konu Başlığı",
            st.session_state.mail_subject,
            help="Kampanya adı yerine kişiselleştirme kullanmak için {CAMPAIGN_NAME} ekleyebilirsin."
        )

        placeholders = ["{Yetkili}", "{Sirket}", "{CLUB_NAME}", "{TODAY}", "{CAMPAIGN_NAME}"]
        tags_html = "".join([f"<span class='tag'>{tag}</span>" for tag in placeholders])
        st.markdown(f"<div style='margin:4px 0 8px;'>{tags_html}</div>", unsafe_allow_html=True)

        st.session_state.mail_body = st.text_area(
            "HTML Mesaj İçeriği",
            st.session_state.mail_body,
            height=360,
            help="Satır içi CSS desteklenir. Görsel linklerini absolute URL olarak ekleyin."
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Ekler & Notlar")
        st.caption("PDF teklifleri, sunumlar veya görselleri toplu ekleyebilirsin.")
        st.session_state.files = st.file_uploader(
            "📎 Dosya Ekle",
            accept_multiple_files=True,
            help="Dosya isimleri Gönderim Panelinde özet olarak listelenir."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_preview:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Canlı Önizleme")
        if df is not None and not df.empty:
            prev_idx = st.number_input("Örnek Satır", 0, len(df)-1, 0)
            row = df.iloc[int(prev_idx)].to_dict()
            p_subj = render_template(st.session_state.mail_subject, row, global_ctx)
            p_body = render_template(st.session_state.mail_body, row, global_ctx)
            st.info(f"Konu: {p_subj}")
            st.components.v1.html(p_body, height=360, scrolling=True)
        else:
            st.warning("Önizleme için önce veri yükleyin.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Şablon Kütüphanesi")
        templates = load_json(TEMPLATE_FILE)
        if isinstance(templates, list) and templates:
            selected_t = st.selectbox("Hazır Şablon", [t.get("name", "İsimsiz") for t in templates])
            st.caption("Şablonlar kategorilere ayrıldıysa isimde görebilirsin.")
            if st.button("Şablonu Yükle"):
                t_data_load = next((t for t in templates if t.get("name") == selected_t), None)
                if t_data_load:
                    st.session_state.mail_subject = t_data_load.get("subject", st.session_state.mail_subject)
                    st.session_state.mail_body = t_data_load.get("body", st.session_state.mail_body)
                    st.success("Şablon yüklendi.")
                    st.rerun()
        else:
            st.caption("Kayıtlı şablon bulunamadı (mail_sablonlari.json).")
        st.markdown("</div>", unsafe_allow_html=True)

# 3. GÖNDERİM
with t_send:
    st.markdown("### 🚀 Kampanya Kontrol Odası")
    st.caption("Gönderim öncesi checklist'i tamamla, dry-run yap ve ardından gerçek gönderime geç.")

    if not has_permission(role, "send"):
        st.error("Bu sekmeye erişim yetkin yok.")
    elif df is None:
        st.warning("Lütfen önce 'Veri Yükle' sekmesinden bir Excel dosyası yükleyin.")
    elif email_col is None:
        st.warning("Lütfen veri sekmesinde e-posta sütununu seçin.")
    elif not st.session_state.smtp_accounts:
        st.error("Lütfen Sidebar üzerinden en az bir SMTP hesabı ekleyin.")
    else:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        c_summary = st.columns(3)
        c_summary[0].metric("Hedef Kayıt", len(df))
        c_summary[1].metric("SMTP Havuzu", len(st.session_state.smtp_accounts))
        c_summary[2].metric("Eklenen Dosya", len(st.session_state.get("files", [])))

        c1, c2 = st.columns(2)
        st.session_state.campaign_name = c1.text_input(
            "Kampanya Adı",
            st.session_state.get("campaign_name", "Sponsorluk Q1")
        )
        is_dry_run = c2.toggle("Dry Run (Önizleme)", value=True, help="Aktifken gönderimler SMTP'ye gitmez, loglar simüle edilir")

        with st.expander("🎛️ Gelişmiş Ayarlar", expanded=False):
            enable_ab = st.checkbox("A/B Testi Aç")
            if enable_ab:
                sa, sb = st.columns(2)
                st.session_state.subject_a = sa.text_input(
                    "Varyasyon A (Konu)",
                    st.session_state.subject_a or st.session_state.mail_subject
                )
                st.session_state.subject_b = sb.text_input(
                    "Varyasyon B (Konu)",
                    st.session_state.subject_b or (st.session_state.mail_subject + " (Özel)")
                )
            st.caption("A/B aktif olduğunda kayıtlar sırayla A ve B olarak gider.")

        qa_col, test_col = st.columns([2, 1])
        with qa_col:
            st.markdown("#### Kalite Kontrol")
            st.write("- Placeholder'lar önizlemede doğrulandı mı?" )
            st.write(f"- Blacklist'te {blacklist_total} mail var, listeyi güncelledin mi?")
            st.write("- SMTP havuzunda kota sınırlarını kontrol ettin mi?")
        with test_col:
            st.markdown("#### Test Gönder")
            test_mail_addr = st.text_input("Test Adresi", placeholder="kendi.mailiniz@ornek.com")
            if st.button("🧪 Test Gönder"):
                if not test_mail_addr:
                    st.warning("Test için mail adresi girin.")
                else:
                    try:
                        acc = st.session_state.smtp_accounts[0]
                        conn = open_smtp(acc)
                        test_row = df.iloc[0].to_dict()
                        subj = render_template(st.session_state.mail_subject, test_row, global_ctx)
                        bod = render_template(st.session_state.mail_body, test_row, global_ctx)
                        send_mail_single(conn, acc["email"], test_mail_addr, f"[TEST] {subj}", bod, st.session_state.files)
                        conn.quit()
                        st.success("Test maili gönderildi!")
                    except Exception as e:
                        st.error(f"Hata: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🚀 GÖNDERİMİ BAŞLAT", type="primary", use_container_width=True):
            st.session_state.sending_active = True

        if st.session_state.get("sending_active"):
            st.markdown("---")
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.container()

            stop_btn = st.button("🛑 ACİL DURDUR")

            blacklisted = load_blacklist()

            sent_history = []
            df_to_send = df.reset_index(drop=True)
            total = len(df_to_send)
            success = 0
            fails = 0

            conns = []
            if not is_dry_run:
                for acc in st.session_state.smtp_accounts:
                    try:
                        conns.append({"c": open_smtp(acc), "from": acc["email"]})
                    except Exception as e:
                        st.warning(f"SMTP bağlantısı başarısız: {acc['email']} ({e})")

            if not is_dry_run and not conns:
                st.error("Hiçbir SMTP sunucusuna bağlanılamadı!")
                st.session_state.sending_active = False
            else:
                for i, row in df_to_send.iterrows():
                    if stop_btn:
                        status_text.warning("Gönderim kullanıcı tarafından durduruldu.")
                        break

                    target_email = str(row[email_col]).lower()

                    if target_email in blacklisted:
                        log_container.warning(f"🚫 {target_email} (Blacklist)")
                        continue

                    subj_final = st.session_state.mail_subject
                    var_label = "Default"
                    if enable_ab:
                        if i % 2 == 0:
                            subj_final = st.session_state.subject_a or st.session_state.mail_subject
                            var_label = "A"
                        else:
                            subj_final = st.session_state.subject_b or st.session_state.mail_subject
                            var_label = "B"

                    subj_rendered = render_template(subj_final, row.to_dict(), global_ctx)
                    body_rendered = render_template(st.session_state.mail_body, row.to_dict(), global_ctx)

                    try:
                        if is_dry_run:
                            log_container.info(f"🔎 DRY-RUN: {target_email} | Konu: {subj_rendered}")
                            status_code = "SIMULATED"
                        else:
                            active_conn = conns[i % len(conns)]
                            send_mail_single(
                                active_conn["c"],
                                active_conn["from"],
                                target_email,
                                subj_rendered,
                                body_rendered,
                                st.session_state.files,
                            )
                            log_container.success(f"✅ {target_email} gönderildi.")
                            status_code = "SENT_OK"
                            time.sleep(random.uniform(2, 5))

                        success += 1
                    except Exception as e:
                        log_container.error(f"❌ {target_email} HATA: {e}")
                        status_code = "ERROR"
                        fails += 1

                    sent_history.append(
                        {
                            "date": str(datetime.now()),
                            "email": target_email,
                            "status": status_code,
                            "campaign": st.session_state.campaign_name,
                            "variant": var_label,
                        }
                    )

                    progress_bar.progress((i + 1) / total)
                    status_text.text(
                        f"İşleniyor: {i+1}/{total} | Başarılı: {success} | Hatalı: {fails}"
                    )

                if not is_dry_run:
                    existing_hist = load_json(HISTORY_FILE)
                    if not isinstance(existing_hist, list):
                        existing_hist = []
                    existing_hist.extend(sent_history)
                    save_json(HISTORY_FILE, existing_hist)

                st.success(f"İşlem Tamamlandı! Toplam Başarılı: {success}, Hatalı: {fails}")
                st.session_state.sending_active = False

# 4. ANALİTİK
with t_stat:
    st.markdown("### 📊 Analitik & Takip")
    hist_data = history_buffer

    if isinstance(hist_data, list) and hist_data:
        df_hist = pd.DataFrame(hist_data)
        if "date" in df_hist.columns:
            df_hist["date"] = pd.to_datetime(df_hist["date"], errors="coerce")
            df_hist = df_hist.dropna(subset=["date"])

        campaigns = ["Tümü"] + sorted(df_hist.get("campaign", pd.Series([])).dropna().unique().tolist())
        statuses = ["Tümü"] + sorted(df_hist.get("status", pd.Series([])).dropna().unique().tolist())
        variants = ["Tümü"] + sorted(df_hist.get("variant", pd.Series([])).dropna().unique().tolist())

        f1, f2, f3 = st.columns(3)
        selected_campaign = f1.selectbox("Kampanya Filtresi", campaigns)
        selected_status = f2.selectbox("Durum Filtresi", statuses)
        selected_variant = f3.selectbox("Varyasyon", variants)

        filtered_df = df_hist.copy()
        if selected_campaign != "Tümü":
            filtered_df = filtered_df[filtered_df["campaign"] == selected_campaign]
        if selected_status != "Tümü":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]
        if selected_variant != "Tümü":
            filtered_df = filtered_df[filtered_df["variant"] == selected_variant]

        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        total_sent = len(filtered_df)
        success_sent = len(filtered_df[filtered_df["status"] == "SENT_OK"])
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Log Kaydı", total_sent)
        k2.metric("Başarılı", success_sent)
        k3.metric("Başarı", f"%{int(success_sent/total_sent*100) if total_sent else 0}")
        k4.metric("Kampanya", filtered_df.get("campaign", pd.Series([])).nunique())
        st.markdown("</div>", unsafe_allow_html=True)

        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            st.subheader("Günlük Gönderim")
            if "date" in filtered_df.columns and not filtered_df.empty:
                chart = (
                    alt.Chart(filtered_df)
                    .mark_bar()
                    .encode(
                        x="date:T",
                        y="count()",
                        color="status:N",
                        tooltip=["date:T", "status:N", "count()"]
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Tarih bilgisi bulunamadı.")
            st.markdown("</div>", unsafe_allow_html=True)

        with chart_cols[1]:
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            st.subheader("Varyasyon Dağılımı")
            if "variant" in filtered_df.columns and not filtered_df.empty:
                chart_ab = (
                    alt.Chart(filtered_df)
                    .mark_arc(innerRadius=50)
                    .encode(
                        theta="count()",
                        color="variant:N",
                        tooltip=["variant:N", "count()"]
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart_ab, use_container_width=True)
            else:
                st.info("A/B verisi bulunamadı.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Detaylı Loglar")
        log_df = filtered_df.sort_values("date", ascending=False) if "date" in filtered_df.columns else filtered_df
        st.dataframe(log_df, use_container_width=True)
        st.download_button(
            "📥 CSV olarak indir",
            filtered_df.to_csv(index=False).encode("utf-8"),
            file_name="kampanya_loglari.csv",
            mime="text/csv"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("🚫 Blacklist Yönetimi")
        bl = blacklist_snapshot
        col_bl1, col_bl2 = st.columns([2, 1])
        with col_bl1:
            if bl:
                st.write(sorted(list(bl)))
            else:
                st.caption("Şu an blacklist boş.")
        with col_bl2:
            new_bl = st.text_input("Yeni Email Ekle")
            if st.button("Blackliste Kaydet"):
                if not is_valid_email(new_bl):
                    st.error("Geçerli bir email gir.")
                else:
                    bl.add(new_bl.lower())
                    save_blacklist(bl)
                    st.success("Blacklist güncellendi.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Henüz gönderim geçmişi bulunmamaktadır.")
