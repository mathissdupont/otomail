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
from datetime import datetime
import hashlib
import hmac
import requests

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
BLACKLIST_FILE = "blacklist.json"

# Admin Listesi
ADMIN_EMAILS = ["sametutku64@gmail.com"]

# Yetki Matrisi
ROLE_PERMISSIONS = {
    "admin": {"send": True, "edit_templates": True, "view_analytics": True},
    "sender": {"send": True, "edit_templates": True, "view_analytics": False},
    "viewer": {"send": False, "edit_templates": False, "view_analytics": True}
}

# ================== CSS (Görünürlük ve Düzen İyileştirmeleri) ==================
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

    /* Genel Yazı ve Arka Plan */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Kart Yapısı */
    .stCard {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid var(--border);
        margin-bottom: 20px;
    }

    /* Input Alanları (Beyaz Sorunu Çözümü) */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: var(--input-bg) !important;
        color: white !important;
        border-color: var(--border) !important;
    }
    
    /* Butonlar */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid var(--border);
    }
    
    /* Metrikler */
    div[data-testid="stMetric"] {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] p { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] div { color: white !important; }

    /* Hero Alanı */
    .hero {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
    }
    .hero h1 { color: white !important; margin: 0; font-size: 1.8rem; }
    .hero p { color: #e0e7ff !important; margin: 5px 0 0; }
    
    /* Etiketler */
    .tag-pill {
        background: #334155; color: #cbd5e1; 
        padding: 2px 8px; border-radius: 4px; 
        font-size: 0.85rem; margin-right: 5px; font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# ================== YARDIMCI FONKSİYONLAR ==================
def load_json(filename):
    if not os.path.exists(filename):
        return [] if "gecmisi" in filename or "sablon" in filename else {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return [] if "gecmisi" in filename or "sablon" in filename else {}

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
    # Excel verilerini işle
    for k, v in row_data.items():
        res = res.replace(f"{{{k}}}", str(v))
    # Global değişkenleri işle
    for k, v in global_ctx.items():
        res = res.replace(f"{{{k}}}", str(v))
    return res

def is_valid_email(email):
    return bool(re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', str(email)))

# ================== STATE BAŞLATMA ==================
if "current_user" not in st.session_state: st.session_state.current_user = None
if "smtp_accounts" not in st.session_state: st.session_state.smtp_accounts = []
if "mail_subject" not in st.session_state: st.session_state.mail_subject = "İş Birliği Hakkında"
if "mail_body" not in st.session_state: st.session_state.mail_body = "Merhaba {Yetkili},\n\n..."
if "loaded_data" not in st.session_state: st.session_state.loaded_data = None
if "email_column" not in st.session_state: st.session_state.email_column = None

config = load_json(CONFIG_FILE)
# Eğer config boşsa default oluştur
if not config:
    config = {"users": [], "smtp_defaults": {"server": "smtp.gmail.com", "port": 587}}

# ================== 1. GİRİŞ EKRANI ==================
if not st.session_state.current_user:
    if not config.get("users"):
        st.warning("⚠️ Hiç kullanıcı yok. Lütfen config_settings.json dosyasına manuel kullanıcı ekleyin.")
        st.stop()

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div class='stCard' style='text-align:center;'><h2>🧬 SponsorBot Giriş</h2></div>", unsafe_allow_html=True)
        
        with st.form("login"):
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", type="primary"):
                user_found = next((user for user in config["users"] if user["username"] == u), None)
                if user_found and verify_password(p, user_found.get("password_hash", "")):
                    st.session_state.current_user = user_found
                    st.rerun()
                else:
                    st.error("Hatalı bilgiler.")
    st.stop()

# ================== 2. ANA PANEL ==================
user = st.session_state.current_user
role = user.get("role", "sender")
global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB": "Heptapus Group"
}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {user['username']}")
    st.caption(f"Yetki: {role.upper()}")
    
    if st.button("Çıkış Yap"):
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚙️ Hızlı Ayarlar")
    
    # SMTP Yönetimi
    with st.expander("SMTP Hesapları", expanded=False):
        srv = st.text_input("Host", "smtp.gmail.com")
        prt = st.number_input("Port", 587)
        em = st.text_input("Email")
        pw = st.text_input("App Şifresi", type="password")
        if st.button("Hesap Ekle"):
            st.session_state.smtp_accounts.append({"server": srv, "port": prt, "email": em, "password": pw})
            st.success("SMTP Eklendi!")
    
    if st.session_state.smtp_accounts:
        st.success(f"✅ {len(st.session_state.smtp_accounts)} SMTP Aktif")
    else:
        st.warning("⚠️ SMTP Yok")

# --- HEADER ---
st.markdown(f"""
<div class='hero'>
    <h1>Heptapus Kontrol Paneli</h1>
    <p>Hoş geldin, {user['username']}. Kampanyalarını yönetmeye başla.</p>
</div>
""", unsafe_allow_html=True)

# --- SEKMELER ---
tab_data, tab_template, tab_send, tab_logs = st.tabs([
    "📂 1. Veri Yükle", 
    "📝 2. Şablon & Kayıt", 
    "🚀 3. Gönderim", 
    "📊 4. Raporlar"
])

# ================== TAB 1: VERİ YÜKLEME ==================
with tab_data:
    col_up, col_stat = st.columns([1, 1])
    
    with col_up:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Excel Dosyası")
        uploaded_file = st.file_uploader("Excel (.xlsx) dosyasını buraya bırak", type=["xlsx"])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file).fillna("").astype(str)
                st.session_state.loaded_data = df
                st.success("Dosya başarıyla okundu!")
            except Exception as e:
                st.error(f"Hata: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_stat:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Veri Analizi")
        if st.session_state.loaded_data is not None:
            df = st.session_state.loaded_data
            cols = df.columns.tolist()
            st.session_state.email_column = st.selectbox("Hangi sütun E-posta içeriyor?", cols)
            
            # Analiz
            valid_mails = df[st.session_state.email_column].apply(is_valid_email).sum()
            
            m1, m2 = st.columns(2)
            m1.metric("Toplam Satır", len(df))
            m2.metric("Geçerli Email", valid_mails)
            
            st.caption("İlk 3 Satır:")
            st.dataframe(df.head(3), use_container_width=True)
        else:
            st.info("Lütfen önce sol taraftan dosya yükle.")
        st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 2: ŞABLON SİSTEMİ (YENİLENDİ) ==================
with tab_template:
    col_editor, col_manager = st.columns([2, 1])

    # --- EDİTÖR KISMI ---
    with col_editor:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("✏️ İçerik Editörü")
        
        st.info("Değişken Kullanımı: {Yetkili}, {Sirket}, {TODAY} şeklinde yazarsan Excel'den otomatik çeker.")
        
        st.session_state.mail_subject = st.text_input("Konu Başlığı", st.session_state.mail_subject)
        st.session_state.mail_body = st.text_area("Mail İçeriği (HTML destekler)", st.session_state.mail_body, height=350)
        
        st.subheader("📎 Dosya Ekleri")
        st.session_state.files = st.file_uploader("PDF/Görsel Ekle", accept_multiple_files=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- YÖNETİCİ KISMI (KAYDET/YÜKLE) ---
    with col_manager:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("💾 Şablon Yönetimi")
        
        # Mevcut şablonları yükle
        templates = load_json(TEMPLATE_FILE)
        template_names = [t["name"] for t in templates]
        
        # 1. Şablon Yükle
        st.markdown("#### Şablon Yükle")
        if template_names:
            selected_load = st.selectbox("Kayıtlı Şablonlar", template_names)
            if st.button("📥 Seçili Şablonu Getir"):
                found = next((t for t in templates if t["name"] == selected_load), None)
                if found:
                    st.session_state.mail_subject = found["subject"]
                    st.session_state.mail_body = found["body"]
                    st.success(f"'{selected_load}' şablonu yüklendi!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.caption("Henüz kayıtlı şablon yok.")
            
        st.markdown("---")
        
        # 2. Şablon Kaydet
        st.markdown("#### Yeni Olarak Kaydet")
        new_temp_name = st.text_input("Şablon Adı Ver", placeholder="Örn: Sponsorluk Q1")
        if st.button("💾 Şablonu Kaydet"):
            if not new_temp_name:
                st.error("Lütfen bir isim ver.")
            else:
                new_entry = {
                    "name": new_temp_name,
                    "subject": st.session_state.mail_subject,
                    "body": st.session_state.mail_body,
                    "date": str(datetime.now())
                }
                # Aynı isim varsa güncelle, yoksa ekle
                templates = [t for t in templates if t["name"] != new_temp_name]
                templates.append(new_entry)
                save_json(TEMPLATE_FILE, templates)
                st.success(f"'{new_temp_name}' başarıyla kaydedildi!")
                time.sleep(1)
                st.rerun()

        # 3. Şablon Sil
        st.markdown("---")
        st.markdown("#### Şablon Sil")
        to_delete = st.selectbox("Silinecek Şablon", ["Seçiniz"] + template_names)
        if st.button("🗑️ Sil"):
            if to_delete != "Seçiniz":
                templates = [t for t in templates if t["name"] != to_delete]
                save_json(TEMPLATE_FILE, templates)
                st.warning("Şablon silindi.")
                time.sleep(1)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 3: GÖNDERİM ==================
with tab_send:
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    
    # Kontroller
    ready = True
    if st.session_state.loaded_data is None:
        st.error("❌ Önce Veri Yükle sekmesinden dosya yükle.")
        ready = False
    if not st.session_state.smtp_accounts:
        st.error("❌ Yan menüden en az bir SMTP hesabı ekle.")
        ready = False
    
    if ready:
        c1, c2 = st.columns(2)
        campaign_name = c1.text_input("Kampanya İsmi", "Genel Gönderim")
        is_dry_run = c2.toggle("Dry Run (Simülasyon)", value=True, help="Açıkken mail gitmez, sadece test eder.")
        
        if is_dry_run:
            st.info("📢 Şu an SİMÜLASYON modundasın. Mail gitmeyecek, sadece loglar oluşacak.")
        else:
            st.warning("🚨 DİKKAT: Gerçek gönderim modu açık. Mailler gidecek!")

        # Önizleme (Canlı)
        with st.expander("Gidecek Mail Önizlemesi (İlk Kayıt)", expanded=True):
            if st.session_state.loaded_data is not None:
                first_row = st.session_state.loaded_data.iloc[0].to_dict()
                prev_s = render_template(st.session_state.mail_subject, first_row, global_ctx)
                prev_b = render_template(st.session_state.mail_body, first_row, global_ctx)
                st.markdown(f"**Konu:** {prev_s}")
                st.markdown(f"**Kime:** {first_row.get(st.session_state.email_column, 'Bilinmiyor')}")
                st.markdown("---")
                st.components.v1.html(prev_b, height=300, scrolling=True)

        if st.button("🚀 GÖNDERİMİ BAŞLAT", type="primary"):
            df_target = st.session_state.loaded_data
            total = len(df_target)
            bar = st.progress(0)
            log_container = st.container()
            
            success_count = 0
            fail_count = 0
            history_logs = []
            
            # SMTP Bağlantıları
            conns = []
            if not is_dry_run:
                for acc in st.session_state.smtp_accounts:
                    try:
                        s = smtplib.SMTP(acc['server'], acc['port'])
                        s.starttls()
                        s.login(acc['email'], acc['password'])
                        conns.append({"conn": s, "email": acc['email']})
                    except Exception as e:
                        st.error(f"SMTP Hatası ({acc['email']}): {e}")
            
            # Eğer gerçek gönderimse ve conn yoksa dur
            if not is_dry_run and not conns:
                st.error("Aktif SMTP bağlantısı kurulamadı!")
                st.stop()

            # Döngü
            for i, row in df_target.iterrows():
                email = str(row[st.session_state.email_column]).strip()
                
                # Render
                subj = render_template(st.session_state.mail_subject, row.to_dict(), global_ctx)
                body = render_template(st.session_state.mail_body, row.to_dict(), global_ctx)
                
                status = "UNKNOWN"
                
                if is_dry_run:
                    time.sleep(0.1)
                    log_container.info(f"🔁 [Dry-Run] {email} işlendi.")
                    status = "SIMULATED"
                    success_count += 1
                else:
                    try:
                        # Round-robin SMTP seçimi
                        active = conns[i % len(conns)]
                        
                        msg = MIMEMultipart()
                        msg['From'] = active['email']
                        msg['To'] = email
                        msg['Subject'] = subj
                        msg.attach(MIMEText(body, 'html'))
                        
                        # Dosya Ekleri
                        if st.session_state.files:
                            for f in st.session_state.files:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(f.getvalue())
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', f"attachment; filename={f.name}")
                                msg.attach(part)

                        active['conn'].sendmail(active['email'], email, msg.as_string())
                        
                        log_container.success(f"✅ Gönderildi: {email}")
                        status = "SENT_OK"
                        success_count += 1
                        time.sleep(1) # Spam önleme
                    except Exception as e:
                        log_container.error(f"❌ Hata ({email}): {e}")
                        status = "ERROR"
                        fail_count += 1
                
                history_logs.append({
                    "date": str(datetime.now()),
                    "email": email,
                    "status": status,
                    "campaign": campaign_name
                })
                
                bar.progress((i + 1) / total)

            # Kaydet ve Temizle
            if not is_dry_run:
                # Bağlantıları kapat
                for c in conns: c['conn'].quit()
                
                # Geçmişe yaz
                existing = load_json(HISTORY_FILE)
                existing.extend(history_logs)
                save_json(HISTORY_FILE, existing)
            
            st.success(f"İşlem Tamamlandı! Başarılı: {success_count}, Hatalı: {fail_count}")

    st.markdown("</div>", unsafe_allow_html=True)

# ================== TAB 4: RAPORLAR ==================
with tab_logs:
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    history_data = load_json(HISTORY_FILE)
    
    if history_data:
        df_hist = pd.DataFrame(history_data)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Gönderim", len(df_hist))
        c2.metric("Başarılı", len(df_hist[df_hist['status'] == 'SENT_OK']))
        c3.metric("Hatalı", len(df_hist[df_hist['status'] == 'ERROR']))
        
        st.markdown("#### Detaylı Loglar")
        st.dataframe(df_hist, use_container_width=True)
        
        st.download_button(
            "📥 Raporu İndir (CSV)",
            df_hist.to_csv(index=False).encode('utf-8'),
            "gonderim_raporu.csv",
            "text/csv"
        )
    else:
        st.info("Henüz gönderim geçmişi yok.")
    st.markdown("</div>", unsafe_allow_html=True)