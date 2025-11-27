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

# ================== AYARLAR & SABİTLER ==================
st.set_page_config(
    page_title="Heptapus SponsorBot",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

HISTORY_FILE = "gonderim_gecmisi.json"
CONFIG_FILE = "config_settings.json"
TEMPLATE_FILE = "mail_sablonlari.json"
BLACKLIST_FILE = "blacklist.json"

ROLE_PERMISSIONS = {
    "admin": {
        "send": True,
        "edit_templates": True,
        "view_analytics": True,
        "manage_users": True
    },
    "sender": {
        "send": True,
        "edit_templates": True,
        "view_analytics": False,
        "manage_users": False
    },
    "viewer": {
        "send": False,
        "edit_templates": False,
        "view_analytics": True,
        "manage_users": False
    }
}

# ================== IEEE HAZIR ŞABLONLAR (EMBCAMP EKLENDİ) ==================
IEEE_DEFAULTS = [
    {
        "name": "🧬 IEEE EMBS - EMBCAMP (Biyomedikal Kampı)",
        "category": "Etkinlik",
        "subject": "Geleceğin Biyomedikal Mühendisleri Sizinle Tanışmak İstiyor: EMBCAMP'25",
        "body": """
<div style="font-family: 'Segoe UI', sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #009ca6;">Sağlık Teknolojilerinin Geleceği Burada Şekilleniyor</h2>
    <p>Sayın <strong>{Yetkili}</strong>,</p>
    
    <p>Bizler, {CLUB_NAME} bünyesindeki <strong>Engineering in Medicine and Biology Society (EMBS)</strong> öğrenci ekibiyiz. Sağlık ve mühendisliği birleştiren bu büyüleyici alanda kendimizi geliştirmek için yola çıktık.</p>
    
    <p>Bu yıl düzenleyeceğimiz <strong>EMBCAMP</strong> (Biyomedikal Kampı), sadece bir etkinlik değil; akademi, sektör ve öğrencilerin bir araya geldiği bir tecrübe aktarım merkezidir.</p>
    
    <div style="background: #e0f7fa; border-left: 5px solid #009ca6; padding: 15px; margin: 20px 0;">
        <strong>Sizden Ne Bekliyoruz?</strong>
        <p style="margin-top:5px;">Maddi destekten çok daha fazlasına; <strong>vizyonunuza ve tecrübenize</strong> ihtiyacımız var.</p>
        <ul>
            <li>Biyomedikal sektöründeki tecrübelerinizi aktaracağınız bir <strong>oturum</strong>,</li>
            <li>Teknolojilerinizi tanıtabileceğiniz bir <strong>fuaye alanı</strong>,</li>
            <li>Ya da sadece öğrencilerimize yol gösterecek bir <strong>mentorluk</strong>.</li>
        </ul>
    </div>
    
    <p><strong>{Sirket}</strong> gibi sektörün öncülerini aramızda görmek, kariyer yolculuğunun başındaki bizler için paha biçilemez bir motivasyon olacaktır.</p>
    
    <p>Bu yolculukta elimizden tutmanız dileğiyle. Detaylı dosyamız ektedir.</p>
    <br>
    <p>Saygılarımızla,<br><strong>IEEE EMBS Ekibi</strong></p>
</div>
"""
    },
    {
        "name": "⚡ IEEE - Genel Yıllık Sponsorluk",
        "category": "Sponsorluk",
        "subject": "İş Birliği Fırsatı: {Sirket} & IEEE {CLUB_NAME}",
        "body": """
<div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #00629B;">Geleceği Birlikte Şekillendirelim!</h2>
    <p>Sayın <strong>{Yetkili}</strong>,</p>
    
    <p>Dünyanın en büyük teknik organizasyonu olan <strong>IEEE</strong>'nin, kampüsümüzdeki temsilcisi <strong>{CLUB_NAME}</strong> olarak, mühendislik ve teknoloji tutkunu öğrencilerle sektörü bir araya getirmeye devam ediyoruz.</p>
    
    <p><strong>{Sirket}</strong> olarak sektördeki öncü konumunuz ve inovatif yaklaşımınız, üyelerimiz için büyük bir ilham kaynağıdır.</p>
    
    <div style="background: #f4f4f4; border-left: 5px solid #00629B; padding: 15px; margin: 20px 0;">
        <strong>Neden Partnerimiz Olmalısınız?</strong>
        <ul>
            <li><strong>Erişim:</strong> Yıllık 5.000+ mühendislik öğrencisine doğrudan ulaşım.</li>
            <li><strong>Marka Bilinirliği:</strong> Kampüs içi tüm etkinliklerde logo ve stant görünürlüğü.</li>
            <li><strong>Yetenek Keşfi:</strong> Başarılı öğrencilerle staj ve işe alım süreçleri için networking.</li>
        </ul>
    </div>
    
    <p>Yeni dönemde sizi <strong>"Ana Sponsorumuz"</strong> olarak yanımızda görmekten onur duyarız. Detaylı sponsorluk dosyamız ektedir.</p>
    
    <p>Geri dönüşünüzü heyecanla bekliyoruz.</p>
    <br>
    <p>Saygılarımla,<br><strong>IEEE Yönetim Kurulu</strong></p>
</div>
"""
    },
    {
        "name": "🚀 IEEE - Kariyer Zirvesi Daveti",
        "category": "Etkinlik",
        "subject": "Davet: Teknoloji ve Kariyer Zirvesi'nde Yeriniz Hazır mı?",
        "body": """
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
    <h2 style="color: #E91D33;">Campus Tech Summit'e Davetlisiniz!</h2>
    <p>Sayın <strong>{Yetkili}</strong>,</p>
    
    <p>Bu yıl X. kez düzenleyeceğimiz, üniversitenin en büyük teknoloji etkinliği olan <strong>Tech Summit</strong> için geri sayım başladı!</p>
    
    <p><strong>{Sirket}</strong> ekibini, sektör tecrübelerini aktarmak ve geleceğin mühendisleriyle tanışmak üzere etkinliğimize davet ediyoruz.</p>
    
    <table style="width:100%; margin: 20px 0; border-collapse: collapse;">
        <tr style="background-color: #eee;">
            <td style="padding: 10px; border: 1px solid #ddd;">📅 <strong>Tarih:</strong> [Tarih Giriniz]</td>
            <td style="padding: 10px; border: 1px solid #ddd;">📍 <strong>Yer:</strong> [Mekan Giriniz]</td>
        </tr>
    </table>
    
    <p><strong>Sponsorluk Kapsamında:</strong></p>
    <ul>
        <li>Ana sahnede konuşma (Keynote) hakkı</li>
        <li>Fuaye alanında İK standı</li>
        <li>Workshop salonu kullanımı</li>
    </ul>
    
    <p>Katılım koşulları ve detaylar için ekteki dosyayı inceleyebilirsiniz.</p>
    <p>Saygılarımızla.</p>
</div>
"""
    },
    {
        "name": "💻 IEEE - Hackathon / Kodlama Yarışması",
        "category": "Teknik",
        "subject": "{Sirket} ile Kodluyoruz: Hackathon Sponsorluğu",
        "body": """
<div style="font-family: monospace; color: #333;">
    <h2 style="color: #28a745;">&lt;CodeTheFuture /&gt;</h2>
    <p>Merhaba <strong>{Yetkili}</strong>,</p>
    
    <p>Öğrencilerin 24 saat boyunca aralıksız kod yazarak projeler geliştireceği <strong>Hackathon</strong> etkinliğimiz yaklaşıyor.</p>
    
    <p><strong>{Sirket}</strong> API'lerini veya teknolojilerini kullanarak öğrencilerin neler yaratabileceğini görmek istemez misiniz?</p>
    
    <p><strong>Destek Alanları:</strong></p>
    <ul>
        <li>Ödül Sponsorluğu (Bilgisayar, Ekipman vb.)</li>
        <li>Mentorluk Desteği (Yazılımcılarınızın ekiplere desteği)</li>
        <li>Pizza/İçecek Sponsorluğu 🍕</li>
    </ul>
    
    <p>Yazılım dünyasının yeni yıldızlarını keşfetmek için sizi de aramızda görmek istiyoruz.</p>
    <br>
    <p><strong>IEEE Computer Society</strong></p>
</div>
"""
    }
]

# ================== MODERN CSS (UI DÜZELTMELERİ BURADA) ==================
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    
    /* Kart Tasarımı */
    .stCard { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #e0e0e0; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
    }
    
    /* İlerleme Çubuğu Renkleri (IEEE Mavisi & Kırmızısı) */
    .stProgress > div > div > div > div { 
        background-image: linear-gradient(to right, #00629B 0%, #E91D33 100%); 
    }
    
    /* --- KRİTİK UI DÜZELTMESİ --- */
    div[data-testid="stMetric"] { 
        background-color: #f0f8ff; 
        border-radius: 8px; 
        padding: 10px; 
        border-left: 4px solid #00629B; 
    }
    
    /* Yazı rengini SİYAH yapıyoruz ki beyaz arka planda okunsun */
    div[data-testid="stMetric"] label {
        color: #000000 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
    }
    
    .status-ok { color: #28a745; font-weight: bold; }
    .status-err { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ================== SESSION STATE BAŞLATMA ==================
defaults = {
    "mail_body": "Sayın {Yetkili},\n\n...",
    "mail_subject": "İş Birliği Teklifi",
    "smtp_accounts": [],
    "saved_config": {},
    "files": [],
    "ab_mode": False,
    "subject_a": "",
    "subject_b": "",
    "ab_strategy": "Sıra ile",
    "campaign_name": "Genel",
    "stop_sending": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "club_name" not in st.session_state:
    st.session_state.club_name = "IEEE Öğrenci Kolu"

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "subject_a" not in st.session_state or not st.session_state.subject_a:
    st.session_state.subject_a = st.session_state.mail_subject
if "subject_b" not in st.session_state:
    st.session_state.subject_b = st.session_state.mail_subject + " (Varyasyon)"

# ================== YARDIMCI FONKSİYONLAR ==================

def load_json(filename):
    # Şablon dosyasını güncel listeyle başlat
    if filename == TEMPLATE_FILE and not os.path.exists(filename):
        save_json(filename, IEEE_DEFAULTS)
        return IEEE_DEFAULTS

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return [] if "gecmisi" in filename or "sablon" in filename else {}
    return [] if "gecmisi" in filename or "sablon" in filename else {}

def save_json(filename, data, mode="w"):
    if mode == "a" and os.path.exists(filename):
        current = load_json(filename)
        if isinstance(current, list):
            current.append(data)
            data = current
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_config():
    defaults = {
        "smtp_defaults": {
            "server": "smtp.gmail.com",
            "port": 587,
            "delay_min": 5,
            "delay_max": 15
        },
        "users": []
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            return defaults

        # Eski format desteği
        if "server" in user_cfg:
            defaults["smtp_defaults"]["server"] = user_cfg.get("server", defaults["smtp_defaults"]["server"])
            defaults["smtp_defaults"]["port"] = user_cfg.get("port", defaults["smtp_defaults"]["port"])
            defaults["smtp_defaults"]["delay_min"] = user_cfg.get("delay_min", defaults["smtp_defaults"]["delay_min"])
            defaults["smtp_defaults"]["delay_max"] = user_cfg.get("delay_max", defaults["smtp_defaults"]["delay_max"])
            user_cfg.pop("server", None)
            user_cfg.pop("port", None)
            user_cfg.pop("delay_min", None)
            user_cfg.pop("delay_max", None)

        for key, val in defaults.items():
            user_cfg.setdefault(key, val)
        return user_cfg
    return defaults

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(email.lower() for email in data if isinstance(email, str))
    except (json.JSONDecodeError, OSError):
        return set()
    return set()

def save_blacklist(emails):
    unique = sorted({email.lower() for email in emails if isinstance(email, str)})
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=4)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return hmac.compare_digest(hash_password(password), password_hash)

def get_user(cfg, username):
    return next((u for u in cfg.get("users", []) if u.get("username") == username), None)

def add_user(cfg, username, password, role):
    cfg.setdefault("users", [])
    cfg["users"].append({
        "username": username,
        "password_hash": hash_password(password),
        "role": role
    })
    save_config(cfg)

def update_user_password(cfg, username, password):
    for user in cfg.get("users", []):
        if user.get("username") == username:
            user["password_hash"] = hash_password(password)
            save_config(cfg)
            return True
    return False

def has_permission(role, permission):
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS.get("viewer", {})).get(permission, False)

config_data = load_config()

if not config_data.get("users"):
    st.title("🔐 İlk Yönetici Kaydı")
    st.write("Sistemi kullanmadan önce bir yönetici hesabı oluşturmalısınız.")
    with st.form("bootstrap_admin"):
        admin_user = st.text_input("Kullanıcı Adı")
        admin_pass = st.text_input("Şifre", type="password")
        admin_pass_confirm = st.text_input("Şifre (Tekrar)", type="password")
        submitted = st.form_submit_button("Kaydet")
        if submitted:
            if not admin_user or not admin_pass:
                st.error("Kullanıcı adı ve şifre zorunlu.")
            elif admin_pass != admin_pass_confirm:
                st.error("Şifreler eşleşmiyor.")
            else:
                add_user(config_data, admin_user.strip(), admin_pass, "admin")
                st.success("Yönetici oluşturuldu. Şimdi giriş yapabilirsiniz.")
                st.stop()
    st.stop()

def render_template(text, row_data, global_ctx):
    if not text: return ""
    res = str(text)
    for k, v in row_data.items(): res = res.replace(f"{{{k}}}", str(v))
    for k, v in global_ctx.items(): res = res.replace(f"{{{k}}}", str(v))
    return res

def read_uploaded_excel(uploaded_file):
    """Sağlam excel okuma; openpyxl eksikse kullanıcıya yol göster."""
    try:
        return pd.read_excel(uploaded_file).fillna("").astype(str)
    except ImportError:
        st.error(
            "Excel okumak için `openpyxl` kurulmalı. `pip install -r requirements.txt` komutuyla kurulum yapıp tekrar deneyin."
        )
        st.stop()
    except Exception as exc:
        st.error(f"Excel dosyası okunamadı: {exc}")
        return None

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

def is_valid_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    return bool(re.fullmatch(regex, str(email)))

# ================== SIDEBAR ==================
current_user = st.session_state.current_user
club_name = st.session_state.club_name
smtp_defaults = config_data.get("smtp_defaults", {})
delay_min = int(smtp_defaults.get("delay_min", 5))
delay_max = int(smtp_defaults.get("delay_max", 15))
smtp_port_default = int(smtp_defaults.get("port", 587))
smtp_server_default = smtp_defaults.get("server", "smtp.gmail.com")
if delay_min > delay_max:
    delay_min, delay_max = delay_max, delay_min

with st.sidebar:
    st.title("⚡ Heptapus SponsorBot")
    user = current_user

    if user:
        st.success(f'Giriş: {user["username"]} ({user["role"]})')
        if st.button("Çıkış Yap"):
            st.session_state.current_user = None
            st.rerun()
    else:
        with st.form("login_form"):
            login_user = st.text_input("Kullanıcı Adı")
            login_pass = st.text_input("Şifre", type="password")
            login = st.form_submit_button("Giriş Yap")
            if login:
                record = get_user(config_data, login_user.strip()) if login_user else None
                if record and verify_password(login_pass, record.get("password_hash", "")):
                    st.session_state.current_user = {
                        "username": record["username"],
                        "role": record.get("role", "sender")
                    }
                    st.toast("Giriş başarılı!", icon="✅")
                    st.rerun()
                else:
                    st.error("Geçersiz kullanıcı adı veya şifre")

    if user and has_permission(user.get("role"), "manage_users"):
        with st.expander("🔐 Kullanıcı Yönetimi"):
            clean_users = [
                {"username": u.get("username"), "role": u.get("role", "sender")}
                for u in config_data.get("users", [])
            ]
            if clean_users:
                st.dataframe(pd.DataFrame(clean_users))
            with st.form("add_user_form", clear_on_submit=True):
                nu, nr = st.columns([2, 1])
                new_user = nu.text_input("Yeni Kullanıcı Adı")
                new_role = nr.selectbox("Rol", list(ROLE_PERMISSIONS.keys()), index=1)
                new_pass = st.text_input("Geçici Şifre", type="password")
                if st.form_submit_button("Kullanıcı Oluştur"):
                    if not new_user or not new_pass:
                        st.error("Tüm alanlar zorunlu.")
                    elif get_user(config_data, new_user.strip()):
                        st.error("Bu kullanıcı adı zaten kayıtlı.")
                    else:
                        add_user(config_data, new_user.strip(), new_pass, new_role)
                        st.success("Kullanıcı oluşturuldu.")
                        st.rerun()
            if config_data.get("users"):
                with st.form("reset_form", clear_on_submit=True):
                    reset_user = st.selectbox(
                        "Şifresi Sıfırlanacak Kullanıcı",
                        [u.get("username") for u in config_data.get("users", [])]
                    )
                    reset_pass = st.text_input("Yeni Şifre", type="password")
                    if st.form_submit_button("Şifreyi Güncelle"):
                        if not reset_pass:
                            st.error("Şifre zorunlu.")
                        elif update_user_password(config_data, reset_user, reset_pass):
                            st.success("Şifre güncellendi.")
                            st.rerun()

        with st.expander("🛠️ Sistem Ayarları"):
            with st.form("system_settings"):
                new_server = st.text_input("Varsayılan SMTP Server", value=smtp_server_default)
                new_port = st.number_input("Varsayılan Port", min_value=1, max_value=65535, value=smtp_port_default)
                d1, d2 = st.columns(2)
                new_delay_min = d1.number_input("Minimum Bekleme (sn)", min_value=0, value=delay_min)
                new_delay_max = d2.number_input("Maksimum Bekleme (sn)", min_value=0, value=delay_max)
                if st.form_submit_button("Ayarları Kaydet"):
                    if new_delay_min > new_delay_max:
                        st.error("Minimum bekleme maksimumdan büyük olamaz.")
                    else:
                        config_data.setdefault("smtp_defaults", {})
                        config_data["smtp_defaults"].update({
                            "server": new_server,
                            "port": int(new_port),
                            "delay_min": int(new_delay_min),
                            "delay_max": int(new_delay_max)
                        })
                        save_config(config_data)
                        st.success("Ayarlar güncellendi.")
                        st.rerun()

    if user and has_permission(user.get("role"), "send"):
        with st.expander("📬 SMTP Hesapları", expanded=True):
            st.info("Havuzdaki hesaplar sırayla kullanılır.")
            with st.form("smtp_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                srv = c1.text_input("Server", smtp_server_default)
                prt = c2.number_input("Port", min_value=1, max_value=65535, value=smtp_port_default)
                umail = st.text_input("Email")
                upass = st.text_input("Uygulama Şifresi", type="password")
                if st.form_submit_button("Ekle"):
                    if umail and upass:
                        st.session_state.smtp_accounts.append({"server": srv, "port": prt, "email": umail, "password": upass})
                        st.toast(f"{umail} eklendi!", icon="✅")
            
            if st.session_state.smtp_accounts:
                st.write(f"**Aktif:** {len(st.session_state.smtp_accounts)}")
                if st.button("Temizle"): st.session_state.smtp_accounts = []; st.rerun()

    if user:
        with st.expander("⚙️ Kulüp Ayarları"):
            st.session_state.club_name = st.text_input("Kulüp Adı", st.session_state.club_name)
            st.caption("Mail şablonlarında {CLUB_NAME} olarak geçer.")

    st.caption("Heptapus SponsorBot © 2024")

if not current_user:
    st.info("Devam etmek için giriş yapın.")
    st.stop()

# ================== ANA EKRAN ==================
st.title("⚡Heptapus SponsorBot")
st.markdown("****")

global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB_NAME": club_name,
    "CAMPAIGN_NAME": st.session_state.get("campaign_name", "")
}

role = current_user.get("role", "viewer")
can_edit_templates = has_permission(role, "edit_templates")
can_send = has_permission(role, "send")
can_view_analytics = has_permission(role, "view_analytics")

tab_data, tab_content, tab_send, tab_analytics = st.tabs(["📂 1. Veri", "📝 2. Şablonlar", "🚀 3. Gönderim", "📊 4. Analitik"])

# --- TAB 1: VERİ ---
with tab_data:
    col_up, col_audit = st.columns([1, 2])
    with col_up:
        uploaded_file = st.file_uploader("Excel Dosyası", type=["xlsx"])
    df = None; email_col = None
    if uploaded_file:
        df = read_uploaded_excel(uploaded_file)
        if df is not None:
            with col_up:
                email_col = st.selectbox("E-Posta Sütunu", df.columns)
                st.success(f"Kayıt: {len(df)}")
            with col_audit:
                # Hata Düzeltmesi: bool() eklendiği için artık hata vermez
                invalid_mails = df[~df[email_col].apply(is_valid_email)]
                m1, m2 = st.columns(2)
                m1.metric("Geçerli", len(df)-len(invalid_mails))
                m2.metric("Hatalı", len(invalid_mails), delta_color="inverse")
                if len(invalid_mails) > 0: st.dataframe(invalid_mails[[email_col]])

# --- TAB 2: ŞABLON ---
with tab_content:
    c_left, c_right = st.columns([2, 1])
    with c_right:
        st.markdown("### ⚡ IEEE Kütüphanesi")
        templates = load_json(TEMPLATE_FILE)
        template_list = templates if isinstance(templates, list) else []
        categories = sorted({tpl.get("category", "Genel") for tpl in template_list}) if template_list else []
        selected_category = st.selectbox("Kategori", ["Hepsi"] + categories)
        filtered_templates = [tpl for tpl in template_list if selected_category == "Hepsi" or tpl.get("category", "Genel") == selected_category]
        template_names = [t["name"] for t in filtered_templates]
        selected_template = st.selectbox("Şablon Seç", ["-- Seçiniz --"] + template_names)
        
        if selected_template != "-- Seçiniz --":
            tpl_data = next((t for t in filtered_templates if t["name"] == selected_template), None)
            if tpl_data:
                st.info(f"Konu: {tpl_data['subject']}")
                if st.button("📥 Bu Şablonu Kullan", disabled=not can_edit_templates):
                    st.session_state.mail_subject = tpl_data["subject"]
                    st.session_state.mail_body = tpl_data["body"]
                    st.session_state.subject_a = tpl_data["subject"] 
                    st.toast("Şablon editöre yüklendi!")
                    st.rerun()
        
        st.divider()
        new_name = st.text_input("Yeni Şablon Adı", disabled=not can_edit_templates)
        new_category = st.selectbox(
            "Kategori",
            ["Genel", "Sponsorluk", "Etkinlik", "Teknik", "Diğer"],
            disabled=not can_edit_templates,
            key="template_category_select"
        )
        if st.button("💾 Şablonu Kaydet", disabled=not can_edit_templates):
            if not new_name:
                st.error("Şablon adı zorunlu.")
            else:
                new_entry = {
                    "name": new_name,
                    "subject": st.session_state.mail_subject,
                    "body": st.session_state.mail_body,
                    "category": new_category
                }
                template_list.append(new_entry)
                save_json(TEMPLATE_FILE, template_list)
                st.success("Kaydedildi.")

    with c_left:
        st.markdown("### ✍️ Editör")
        st.session_state.mail_subject = st.text_input("Konu", st.session_state.mail_subject, disabled=not can_edit_templates)
        st.session_state.mail_body = st.text_area("HTML İçerik", st.session_state.mail_body, height=400, disabled=not can_edit_templates)
        st.session_state.files = st.file_uploader("Ekler", accept_multiple_files=True, disabled=not can_send)

        with st.expander("🔎 Kullanılabilir Değişkenler", expanded=False):
            st.markdown("- `{CLUB_NAME}` → Kulüp adı")
            st.markdown("- `{TODAY}` → Bugünün tarihi")
            st.markdown("- `{CAMPAIGN_NAME}` → Kampanya adı")
            if df is not None and not df.empty:
                st.markdown("**Excel sütunları:**")
                for col in df.columns:
                    st.markdown(f"- `{{{col}}}`")
            else:
                st.caption("Excel yüklendiğinde satır bazlı alanlar listelenecek.")
        
        with st.expander("👁️ Önizleme"):
            if df is not None and not df.empty:
                max_row = len(df) - 1
                preview_idx = st.number_input(
                    "Önizleme Satırı",
                    min_value=0,
                    max_value=max_row,
                    value=min(st.session_state.get("preview_idx", 0), max_row),
                    step=1
                )
                st.session_state.preview_idx = int(preview_idx)
                row_data = df.iloc[int(preview_idx)].to_dict()
                prev_bod = render_template(st.session_state.mail_body, row_data, global_ctx)
                st.components.v1.html(prev_bod, height=300, scrolling=True)
                st.caption(f"Önizlenen kişi: {row_data.get(email_col or '', 'Seçili değil')}")
            elif df is None:
                st.info("Önizleme için Excel yükleyin.")
            else:
                st.warning("Tabloda kayıt yok.")

# --- TAB 3: GÖNDERİM ---
with tab_send:
    if not can_send:
        st.error("Bu sekmeye erişim yetkiniz yok.")
    elif df is None:
        st.warning("Excel yükle.")
    elif not st.session_state.smtp_accounts:
        st.error("SMTP ekle.")
    else:
        blacklisted_emails = load_blacklist()
        st.session_state.campaign_name = st.text_input("Kampanya Adı", st.session_state.campaign_name)
        global_ctx["CAMPAIGN_NAME"] = st.session_state.campaign_name

        st.session_state.ab_mode = st.toggle("A/B Test Modu", value=st.session_state.ab_mode)
        if st.session_state.ab_mode:
            ab_left, ab_right = st.columns(2)
            st.session_state.subject_a = ab_left.text_input("Konu A", st.session_state.subject_a or st.session_state.mail_subject, disabled=not can_edit_templates)
            st.session_state.subject_b = ab_right.text_input("Konu B", st.session_state.subject_b or f"{st.session_state.mail_subject} (Varyasyon)", disabled=not can_edit_templates)
            st.session_state.ab_strategy = st.selectbox(
                "Dağıtım Şekli",
                ["Sıra ile", "Rastgele"],
                index=["Sıra ile", "Rastgele"].index(st.session_state.ab_strategy) if st.session_state.ab_strategy in ["Sıra ile", "Rastgele"] else 0,
                disabled=not can_edit_templates
            )
        else:
            st.info("A/B testi pasif. Tüm mailler ana konu ile gönderilir.")

        hist = load_json(HISTORY_FILE)
        sent_emails = [x["email"] for x in hist if x.get("status") == "SENT_OK"] if isinstance(hist, list) else []
        resume = st.toggle("Smart Resume", value=True)
        
        final_df = df[~df[email_col].isin(sent_emails)] if resume else df
        if email_col and len(final_df) > 0 and blacklisted_emails:
            mask = final_df[email_col].astype(str).str.lower().isin(blacklisted_emails)
            skipped = int(mask.sum())
            if skipped > 0:
                st.info(f"Blacklist nedeniyle atlanacak: {skipped}")
            final_df = final_df[~mask]
        elif blacklisted_emails:
            st.caption("Blacklist kayıtlı ancak filtrelenecek veri bulunamadı.")
        st.info(f"Gönderilecek: {len(final_df)}")

        st.session_state.dry_run = st.checkbox(
            "Dry-Run (Sadece simülasyon, mail gönderme)",
            value=st.session_state.get("dry_run", False)
        )
        
        st.session_state.test_email = st.text_input("Test mail adresi", st.session_state.get("test_email", ""))
        if st.button("📨 Test Mail Gönder", use_container_width=False):
            test_target = st.session_state.test_email.strip()
            if not test_target:
                st.error("Önce test mail adresi girin.")
            elif not st.session_state.smtp_accounts:
                st.error("Test maili için en az bir SMTP hesabı ekleyin.")
            elif df is None or df.empty:
                st.error("Test maili göndermek için Excel verisi gerekli.")
            else:
                idx = min(st.session_state.get("preview_idx", 0), len(df) - 1)
                row_dict = df.iloc[int(idx)].to_dict()
                subject = render_template(st.session_state.mail_subject, row_dict, global_ctx)
                body = render_template(st.session_state.mail_body, row_dict, global_ctx)
                acc = st.session_state.smtp_accounts[0]
                try:
                    conn = open_smtp(acc)
                    send_mail_single(conn, acc["email"], test_target, subject, body, st.session_state.files)
                    conn.quit()
                    st.success("Test mail başarıyla gönderildi.")
                except Exception as exc:
                    st.error(f"Test mail gönderilemedi: {exc}")

        if st.button("🔥 BAŞLAT", type="primary", use_container_width=True):
            st.session_state.run_sending = True
            st.session_state.target_df = final_df

        if st.session_state.get("run_sending"):
            stop = st.button("🛑 DURDUR")
            if stop:
                st.session_state.run_sending = False
                st.stop()

            dry_run_mode = st.session_state.get("dry_run", False)
            conns = []
            can_process = True
            if not dry_run_mode:
                for acc in st.session_state.smtp_accounts:
                    try:
                        conns.append({"conn": open_smtp(acc), "email": acc["email"]})
                    except Exception as exc:
                        st.warning(f"SMTP bağlantısı başarısız: {acc['email']} ({exc})")

                if not conns:
                    st.error("Hiçbir SMTP bağlantısı açılamadı.")
                    st.session_state.run_sending = False
                    can_process = False

            if not can_process:
                st.stop()

            bar = st.progress(0)
            status = st.empty()
            suc = 0
            fail = 0
            results = []
            for i, row in st.session_state.target_df.reset_index(drop=True).iterrows():
                if stop:
                    break
                target = row[email_col]
                row_dict = row.to_dict()
                variant = "default"
                subject_template = st.session_state.mail_subject
                if st.session_state.ab_mode:
                    subj_a = st.session_state.subject_a or st.session_state.mail_subject
                    subj_b = st.session_state.subject_b or subj_a
                    strategy = st.session_state.ab_strategy or "Sıra ile"
                    if strategy == "Rastgele":
                        variant = random.choice(["A", "B"])
                    else:
                        variant = "A" if i % 2 == 0 else "B"
                    subject_template = subj_a if variant == "A" else subj_b
                rendered_subject = render_template(subject_template, row_dict, global_ctx)

                if dry_run_mode:
                    s_str = "DRY_RUN"
                    err_msg = ""
                    status.write(f"🔎 {target} (simülasyon)")
                else:
                    conn_obj = conns[i % len(conns)]
                    try:
                        body = render_template(st.session_state.mail_body, row_dict, global_ctx)
                        send_mail_single(conn_obj["conn"], conn_obj["email"], target, rendered_subject, body, st.session_state.files)
                        suc += 1
                        s_str = "SENT_OK"
                        err_msg = ""
                        status.write(f"✅ {target}")
                    except Exception as e:
                        fail += 1
                        s_str = "ERROR"
                        err_msg = str(e)
                        status.write(f"❌ {target}: {e}")

                payload = {
                    "date": str(datetime.now()),
                    "email": target,
                    "status": s_str,
                    "campaign": st.session_state.campaign_name,
                    "subject": rendered_subject,
                    "subject_variant": variant,
                    "user": current_user.get("username"),
                    "error": err_msg
                }

                if dry_run_mode:
                    results.append(payload)
                else:
                    save_json(HISTORY_FILE, payload, "a")
                    results.append(payload)

                bar.progress((i+1)/len(st.session_state.target_df))
                if not dry_run_mode and delay_max > 0:
                    wait_time = random.uniform(delay_min, delay_max)
                    time.sleep(wait_time)

            if not dry_run_mode:
                for c in conns:
                    c["conn"].quit()
                st.success(f"Bitti. Başarılı: {suc}, Hatalı: {fail}")
                if results:
                    st.dataframe(pd.DataFrame(results))
            else:
                st.success(f"Dry-run tamamlandı, {len(results)} mail simüle edildi.")
                if results:
                    st.dataframe(pd.DataFrame(results))

            st.session_state.run_sending = False

# --- TAB 4: ANALİTİK ---
with tab_analytics:
    if not can_view_analytics:
        st.error("Analitiklere erişim yetkiniz yok.")
    else:
        hist = load_json(HISTORY_FILE)
        if isinstance(hist, list) and len(hist) > 0:
            dfh = pd.DataFrame(hist)
            for col, default in [("campaign", "Genel"), ("subject_variant", "default"), ("user", "-"), ("error", "")]:
                if col not in dfh.columns:
                    dfh[col] = default
            dfh["date"] = pd.to_datetime(dfh["date"], errors="coerce")
            dfh.dropna(subset=["date"], inplace=True)
            dfh["gün"] = dfh["date"].dt.strftime("%Y-%m-%d")
            suc = len(dfh[dfh["status"] == "SENT_OK"])
            fail = len(dfh[dfh["status"] == "ERROR"])
            st.metric("Toplam Başarılı", suc)
            st.metric("Toplam Hatalı", fail)

            colf1, colf2 = st.columns(2)
            campaigns = sorted(dfh["campaign"].dropna().unique())
            selected_campaigns = colf1.multiselect("Kampanyalar", campaigns)
            variants = sorted(dfh["subject_variant"].dropna().unique())
            selected_variants = colf2.multiselect("Subject Varyasyonları", variants)
            filtered = dfh
            if selected_campaigns:
                filtered = filtered[filtered["campaign"].isin(selected_campaigns)]
            if selected_variants:
                filtered = filtered[filtered["subject_variant"].isin(selected_variants)]

            if not filtered.empty:
                summary_group = filtered.groupby(["campaign", "subject_variant"]).agg(
                    toplam=("status", "size"),
                    basarili=("status", lambda s: (s == "SENT_OK").sum()),
                    hatali=("status", lambda s: (s == "ERROR").sum())
                ).reset_index()
                summary_group["success_rate"] = summary_group.apply(
                    lambda row: round((row["basarili"] / row["toplam"]) * 100, 2) if row["toplam"] else 0,
                    axis=1
                )
                st.markdown("#### A/B Performans Özeti")
                st.dataframe(
                    summary_group.rename(columns={
                        "campaign": "Kampanya",
                        "subject_variant": "Varyasyon",
                        "toplam": "Toplam",
                        "basarili": "Başarılı",
                        "hatali": "Hatalı",
                        "success_rate": "Success Rate (%)"
                    })
                )

                ab_chart = (
                    alt.Chart(summary_group)
                    .mark_bar()
                    .encode(
                        x="subject_variant:N",
                        y="basarili:Q",
                        color="campaign:N",
                        tooltip=["campaign", "subject_variant", "basarili", "toplam", "success_rate"]
                    )
                    .properties(height=250)
                )
                st.altair_chart(ab_chart, use_container_width=True)

            daily = filtered.groupby(["gün", "status"]).size().reset_index(name="adet")
            chart = (
                alt.Chart(daily)
                .mark_bar()
                .encode(x="gün:N", y="adet:Q", color="status:N", tooltip=["gün", "status", "adet"])
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

            report_buffer = io.StringIO()
            daily.to_csv(report_buffer, index=False)
            st.download_button(
                "📄 Günlük Raporu İndir (CSV)",
                data=report_buffer.getvalue(),
                file_name=f"otomail_rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

            full_buffer = io.StringIO()
            filtered.sort_values("date", ascending=False).to_csv(full_buffer, index=False)
            st.download_button(
                "📥 Tam Kayıtları İndir (CSV)",
                data=full_buffer.getvalue(),
                file_name=f"otomail_kayit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

            st.dataframe(filtered[["date", "email", "status", "campaign", "subject_variant", "user", "error"]].sort_values("date", ascending=False))

            with st.expander("🚫 Blacklist Yönetimi", expanded=False):
                blacklist_current = load_blacklist()
                st.caption(f"Aktif blacklist sayısı: {len(blacklist_current)}")
                bl_email = st.text_input("Blacklist’e eklenecek email", key="blacklist_input")
                if st.button("Ekle", key="blacklist_add_btn"):
                    if not bl_email:
                        st.error("Email zorunlu.")
                    else:
                        blacklist_current.add(bl_email.strip().lower())
                        save_blacklist(blacklist_current)
                        st.success("Email blacklist’e eklendi.")
                        st.rerun()
        else:
            st.info("Veri yok.")