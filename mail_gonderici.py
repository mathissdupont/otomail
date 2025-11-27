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

# ================== IEEE HAZIR ŞABLONLAR (EMBCAMP EKLENDİ) ==================
IEEE_DEFAULTS = [
    {
        "name": "🧬 IEEE EMBS - EMBCAMP (Biyomedikal Kampı)",
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
    "stop_sending": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
with st.sidebar:
    st.title("⚡ Heptapus SponsorBot")
    
    with st.expander("📬 SMTP Hesapları", expanded=True):
        st.info("Havuzdaki hesaplar sırayla kullanılır.")
        with st.form("smtp_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            srv = c1.text_input("Server", "smtp.gmail.com")
            prt = c2.number_input("Port", 587)
            umail = st.text_input("Email")
            upass = st.text_input("Uygulama Şifresi", type="password")
            if st.form_submit_button("Ekle"):
                if umail and upass:
                    st.session_state.smtp_accounts.append({"server": srv, "port": prt, "email": umail, "password": upass})
                    st.toast(f"{umail} eklendi!", icon="✅")
        
        if st.session_state.smtp_accounts:
            st.write(f"**Aktif:** {len(st.session_state.smtp_accounts)}")
            if st.button("Temizle"): st.session_state.smtp_accounts = []; st.rerun()

    with st.expander("⚙️ Kulüp Ayarları"):
        club_name = st.text_input("Kulüp Adı", "IEEE Öğrenci Kolu")
        st.caption("Mail şablonlarında {CLUB_NAME} olarak geçer.")

    st.caption("Heptapus SponsorBot © 2024")

# ================== ANA EKRAN ==================
st.title("⚡Heptapus SponsorBot")
st.markdown("****")

global_ctx = {
    "TODAY": datetime.now().strftime("%d.%m.%Y"),
    "CLUB_NAME": club_name
}

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
        template_names = [t["name"] for t in templates] if isinstance(templates, list) else []
        selected_template = st.selectbox("Şablon Seç", ["-- Seçiniz --"] + template_names)
        
        if selected_template != "-- Seçiniz --":
            tpl_data = next((t for t in templates if t["name"] == selected_template), None)
            if tpl_data:
                st.info(f"Konu: {tpl_data['subject']}")
                if st.button("📥 Bu Şablonu Kullan"):
                    st.session_state.mail_subject = tpl_data["subject"]
                    st.session_state.mail_body = tpl_data["body"]
                    st.session_state.subject_a = tpl_data["subject"] 
                    st.toast("Şablon editöre yüklendi!")
                    st.rerun()
        
        st.divider()
        new_name = st.text_input("Yeni Şablon Adı")
        if st.button("💾 Şablonu Kaydet"):
            new_entry = {"name": new_name, "subject": st.session_state.mail_subject, "body": st.session_state.mail_body}
            templates.append(new_entry)
            save_json(TEMPLATE_FILE, templates)
            st.success("Kaydedildi.")

    with c_left:
        st.markdown("### ✍️ Editör")
        st.session_state.mail_subject = st.text_input("Konu", st.session_state.mail_subject)
        st.session_state.mail_body = st.text_area("HTML İçerik", st.session_state.mail_body, height=400)
        st.session_state.files = st.file_uploader("Ekler", accept_multiple_files=True)
        
        with st.expander("👁️ Önizleme"):
            if df is not None and not df.empty:
                row0 = df.iloc[0].to_dict()
                prev_bod = render_template(st.session_state.mail_body, row0, global_ctx)
                st.components.v1.html(prev_bod, height=300, scrolling=True)

# --- TAB 3: GÖNDERİM ---
with tab_send:
    if df is None: st.warning("Excel yükle.")
    elif not st.session_state.smtp_accounts: st.error("SMTP ekle.")
    else:
        hist = load_json(HISTORY_FILE)
        sent_emails = [x["email"] for x in hist if x.get("status") == "SENT_OK"] if isinstance(hist, list) else []
        resume = st.toggle("Smart Resume", value=True)
        
        final_df = df[~df[email_col].isin(sent_emails)] if resume else df
        st.info(f"Gönderilecek: {len(final_df)}")
        
        if st.button("🔥 BAŞLAT", type="primary", use_container_width=True):
            st.session_state.run_sending = True
            st.session_state.target_df = final_df

        if st.session_state.get("run_sending"):
            stop = st.button("🛑 DURDUR")
            if stop: st.session_state.run_sending = False; st.stop()
            
            conns = []
            for acc in st.session_state.smtp_accounts:
                try: conns.append({"conn": open_smtp(acc), "email": acc["email"]})
                except: pass
            
            bar = st.progress(0); status = st.empty(); suc=0; fail=0
            for i, row in st.session_state.target_df.reset_index(drop=True).iterrows():
                if stop: break
                target = row[email_col]
                conn_obj = conns[i % len(conns)]
                
                try:
                    sub = render_template(st.session_state.mail_subject, row.to_dict(), global_ctx)
                    body = render_template(st.session_state.mail_body, row.to_dict(), global_ctx)
                    send_mail_single(conn_obj["conn"], conn_obj["email"], target, sub, body, st.session_state.files)
                    suc += 1; s_str = "SENT_OK"
                    status.write(f"✅ {target}")
                except Exception as e:
                    fail += 1; s_str = "ERROR"
                    status.write(f"❌ {target}: {e}")
                
                save_json(HISTORY_FILE, {"date": str(datetime.now()), "email": target, "status": s_str}, "a")
                bar.progress((i+1)/len(st.session_state.target_df))
                time.sleep(random.randint(5, 15))
            
            for c in conns: c["conn"].quit()
            st.success(f"Bitti. Başarılı: {suc}")
            st.session_state.run_sending = False

# --- TAB 4: ANALİTİK ---
with tab_analytics:
    hist = load_json(HISTORY_FILE)
    if isinstance(hist, list) and len(hist) > 0:
        dfh = pd.DataFrame(hist)
        suc = len(dfh[dfh["status"]=="SENT_OK"])
        st.metric("Toplam Başarılı", suc)
        st.dataframe(dfh)
    else: st.info("Veri yok.")