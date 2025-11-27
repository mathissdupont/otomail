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

# Yetki Matrisi
ROLE_PERMISSIONS = {
    "admin": {"send": True, "edit_templates": True, "view_analytics": True, "manage_users": True},
    "sender": {"send": True, "edit_templates": True, "view_analytics": False, "manage_users": False},
    "viewer": {"send": False, "edit_templates": False, "view_analytics": True, "manage_users": False}
}

# ================== MODERN CSS & TEMA ==================
st.markdown("""
<style>
    /* Genel Font ve Arka Plan */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Ana Konteyner */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Kart Tasarımı */
    .stCard {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }

    /* Login Kutusu */
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #eee;
    }

    /* Butonlar */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748b;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-size: 1.8rem;
        font-weight: 700;
    }

    /* Header Renkleri */
    h1, h2, h3 {
        color: #1e293b;
    }
    
    /* Sidebar Güzelleştirme */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

</style>
""", unsafe_allow_html=True)

# ================== FONKSİYONLAR ==================
def load_json(filename):
    """
    HISTORY / TEMPLATE gibi dosyaları okur.
    - Bulunamazsa: history/template için [] döner, diğerleri için {}.
    """
    if not os.path.exists(filename):
        return [] if ("gecmisi" in filename or "sablon" in filename) else {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [] if ("gecmisi" in filename or "sablon" in filename) else {}

def save_json(filename, data, mode="w"):
    """
    mode="w": direkt yazar
    mode="a": mevcut listeye append eder
    """
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
    # Eğer hiç kullanıcı yoksa Admin oluştur
    if not config_data.get("users"):
        st.markdown("<div class='login-box'><h2>🔐 Yönetici Kurulumu</h2>", unsafe_allow_html=True)
        with st.form("setup_admin"):
            st.info("Sistemi kullanmak için ilk yönetici hesabını oluşturun.")
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Kurulumu Tamamla", type="primary")
            if submitted:
                if u and p:
                    config_data["users"].append(
                        {"username": u, "password_hash": hash_password(p), "role": "admin"}
                    )
                    save_json(CONFIG_FILE, config_data)
                    st.success("Yönetici oluşturuldu! Lütfen giriş yapın.")
                    st.rerun()
                else:
                    st.error("Alanlar boş bırakılamaz.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # Normal Login
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
        
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            if submitted:
                user = get_user(config_data, username.strip())
                if user and verify_password(password, user.get("password_hash", "")):
                    st.session_state.current_user = {
                        "username": user["username"],
                        "role": user.get("role", "sender")
                    }
                    st.toast(f"Hoş geldin, {user['username']}!", icon="👋")
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre.")
    st.stop()

# ================== ANA UYGULAMA (Giriş Başarılı) ==================
user = st.session_state.current_user
role = user.get("role", "viewer")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2913/2913990.png", width=50)
    st.title("Heptapus Panel")
    st.markdown(f"👤 **{user['username']}** ({role.upper()})")
    
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    
    if has_permission(role, "send"):
        with st.expander("📬 SMTP Ayarları", expanded=True):
            st.caption("Aktif SMTP Havuzu")
            if not st.session_state.smtp_accounts:
                st.warning("Hesap eklenmedi!")
            else:
                for acc in st.session_state.smtp_accounts:
                    st.success(f"✅ {acc['email']}")
            
            if st.button("➕ Hesap Ekle"):
                st.session_state.show_smtp_form = True

    if has_permission(role, "manage_users"):
        with st.expander("⚙️ Admin Paneli"):
            st.write(f"Toplam Kullanıcı: {len(config_data.get('users', []))}")
            st.caption("→ İstersen buraya kullanıcı ekleme/silme ekranı da ekleyebilirsin.")

    st.caption("Heptapus SponsorBot © 2024")

# SMTP Ekleme Modalı (Sidebar butonuyla tetikleniyor)
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

# --- GLOBAL CONTEXT ---
global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB_NAME": st.session_state.club_name,
    "CAMPAIGN_NAME": st.session_state.get("campaign_name", "Genel")
}

# Sekmeler
t_data, t_tmpl, t_send, t_stat = st.tabs(
    ["📂 Veri Yükle", "📝 Şablon Editörü", "🚀 Gönderim Paneli", "📊 Analitik"]
)

# Bu run için df ve email_col default
df = None
email_col = None

# ================== 1. VERİ SEKME ==================
with t_data:
    st.markdown("### 📤 Hedef Kitle Listesi")
    st.markdown("Excel dosyanızda **Yetkili, Email, Sirket** gibi sütunların olduğundan emin olun.")
    
    col_file, col_info = st.columns([1, 2])
    
    with col_file:
        uploaded_file = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx"])
        
        if st.button("📄 Örnek Excel İndir"):
            dummy_data = pd.DataFrame([
                {"Yetkili": "Ahmet Yılmaz", "Email": "ahmet@ornek.com", "Sirket": "Tech A.Ş."},
                {"Yetkili": "Ayşe Demir", "Email": "ayse@demo.com", "Sirket": "Soft Ltd."}
            ])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                dummy_data.to_excel(writer, index=False)
            st.download_button(
                "📥 İndir",
                output.getvalue(),
                "ornek_liste.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file).fillna("").astype(str)
            with col_info:
                st.markdown("<div class='stCard'>", unsafe_allow_html=True)
                email_col = st.selectbox("📧 E-Posta Sütununu Seçin", df.columns, index=0)
                
                valid_mask = df[email_col].apply(is_valid_email)
                valid_count = valid_mask.sum()
                invalid_count = len(df) - valid_count
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Toplam Kayıt", len(df))
                m2.metric("Geçerli Email", valid_count)
                m3.metric("Hatalı/Boş", invalid_count, delta_color="inverse")
                
                if invalid_count > 0:
                    with st.expander("⚠️ Hatalı Kayıtları Gör"):
                        st.dataframe(df[~valid_mask])
                st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Dosya okunamadı: {e}")

# ================== 2. ŞABLON SEKME ==================
with t_tmpl:
    col_editor, col_preview = st.columns([2, 1])
    
    with col_editor:
        st.markdown("### ✍️ İçerik Editörü")
        st.session_state.mail_subject = st.text_input("Konu Başlığı", st.session_state.mail_subject)
        
        st.markdown("""
        <div style="margin-bottom:5px; font-size:0.8em; color:#666;">
        Desteklenen Değişkenler: <code>{Yetkili}</code>, <code>{Sirket}</code>, <code>{CLUB_NAME}</code>, <code>{TODAY}</code>, <code>{CAMPAIGN_NAME}</code>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state.mail_body = st.text_area(
            "HTML Mesaj İçeriği",
            st.session_state.mail_body,
            height=400,
            help="Buraya HTML formatında mail içeriği yazabilirsiniz."
        )
        st.session_state.files = st.file_uploader(
            "📎 Dosya Ekle (PDF/Görsel)",
            accept_multiple_files=True
        )

    with col_preview:
        st.markdown("### 👁️ Önizleme")
        if df is not None and not df.empty:
            prev_idx = st.number_input("Satır No", 0, len(df)-1, 0)
            row = df.iloc[int(prev_idx)].to_dict()
            p_subj = render_template(st.session_state.mail_subject, row, global_ctx)
            p_body = render_template(st.session_state.mail_body, row, global_ctx)
            st.info(f"Konu: {p_subj}")
            st.components.v1.html(p_body, height=400, scrolling=True)
        else:
            st.warning("Önizleme için önce veri yükleyin.")
        
        st.markdown("---")
        templates = load_json(TEMPLATE_FILE)
        if isinstance(templates, list) and templates:
            selected_t = st.selectbox("Hazır Şablon Yükle", [t.get("name", "İsimsiz") for t in templates])
            if st.button("Şablonu Uygula"):
                t_data_load = next((t for t in templates if t.get("name") == selected_t), None)
                if t_data_load:
                    st.session_state.mail_subject = t_data_load.get("subject", st.session_state.mail_subject)
                    st.session_state.mail_body = t_data_load.get("body", st.session_state.mail_body)
                    st.success("Şablon yüklendi.")
                    st.experimental_rerun()
        else:
            st.caption("Kayıtlı şablon bulunamadı (TEMPLATE_FILE).")

# ================== 3. GÖNDERİM SEKME ==================
with t_send:
    st.markdown("### 🚀 Kampanya Başlatıcı")

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
        c1, c2 = st.columns(2)
        st.session_state.campaign_name = c1.text_input(
            "Kampanya Adı",
            st.session_state.get("campaign_name", "Sponsorluk Q1")
        )
        is_dry_run = c2.toggle("Dry Run (Simülasyon)", value=True)

        enable_ab = st.toggle("A/B Testi Aktif")
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

        st.markdown("---")
        test_mail_addr = st.text_input("Test E-Postası Alıcısı", placeholder="kendi.mailiniz@ornek.com")
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
                            time.sleep(random.uniform(2, 5))  # Anti-spam bekleme

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

# ================== 4. ANALİTİK SEKME ==================
with t_stat:
    st.markdown("### 📊 Performans Raporu")
    hist_data = load_json(HISTORY_FILE)

    if isinstance(hist_data, list) and hist_data:
        df_hist = pd.DataFrame(hist_data)
        if "date" in df_hist.columns:
            df_hist["date"] = pd.to_datetime(df_hist["date"], errors="coerce")
            df_hist = df_hist.dropna(subset=["date"])

        total_sent = len(df_hist)
        success_sent = len(df_hist[df_hist["status"] == "SENT_OK"])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Toplam İşlem", total_sent)
        k2.metric("Başarılı Gönderim", success_sent)
        k3.metric("Başarı Oranı", f"%{int(success_sent/total_sent*100) if total_sent else 0}")
        k4.metric("Aktif Kampanyalar", df_hist.get("campaign", pd.Series([])).nunique())

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Günlük Gönderim")
            if "date" in df_hist.columns:
                chart = (
                    alt.Chart(df_hist)
                    .mark_bar()
                    .encode(
                        x="date:T",
                        y="count()",
                        color="status:N",
                        tooltip=["date:T", "status:N", "count()"]
                    )
                    .properties(height=300)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Tarih bilgisi bulunamadı.")

        with col_chart2:
            st.markdown("#### A/B Testi Sonuçları")
            if "variant" in df_hist.columns:
                chart_ab = (
                    alt.Chart(df_hist)
                    .mark_arc(innerRadius=50)
                    .encode(
                        theta="count()",
                        color="variant:N",
                        tooltip=["variant:N", "count()"]
                    )
                    .properties(height=300)
                )
                st.altair_chart(chart_ab, use_container_width=True)
            else:
                st.info("A/B verisi bulunamadı.")

        st.markdown("#### Detaylı Loglar")
        st.dataframe(df_hist.sort_values("date", ascending=False), use_container_width=True)

        # Blacklist yönetimi
        st.markdown("---")
        st.markdown("### 🚫 Blacklist Yönetimi")
        bl = load_blacklist()
        col_bl1, col_bl2 = st.columns(2)
        with col_bl1:
            st.write("Blackliste alınmış adresler:")
            if bl:
                st.write(sorted(list(bl)))
            else:
                st.caption("Şu an blacklist boş.")
        with col_bl2:
            new_bl = st.text_input("Blacklist'e eklenecek email")
            if st.button("Ekle"):
                if not is_valid_email(new_bl):
                    st.error("Geçerli bir email gir.")
                else:
                    bl.add(new_bl.lower())
                    save_blacklist(bl)
                    st.success("Blacklist güncellendi.")
                    st.experimental_rerun()

    else:
        st.info("Henüz gönderim geçmişi bulunmamaktadır.")
