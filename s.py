import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

# הגדרת עמוד מותאמת למובייל ומחשב
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- עיצוב פרימיום ספורט כהה (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;600;700;800&display=swap');
    
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    .stApp { background-color: #0F172A !important; }
    header, footer, #MainMenu { visibility: hidden !important; }
    h1, h2, h3, h4 { color: #F8FAFC !important; text-align: center !important; font-weight: 800; }
    
    /* כרטיסיות הרצים והמנהל */
    .custom-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 24px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    
    /* תיבות קלט שם */
    div[data-testid="stTextInput"] label p {
        color: #38BDF8 !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stTextInput"] input {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border: 2px solid #334155 !important;
        border-radius: 14px !important;
        padding: 15px !important;
        font-size: 1.2rem !important;
    }

    /* לשוניות עליונות */
    div[data-testid="stTabs"] button {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 30px;
        color: #94A3B8;
        padding: 12px 25px;
        font-weight: bold;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6, #1D4ED8) !important;
        color: #FFFFFF !important;
        border: none;
        box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4);
    }
    
    /* כפתורי ריצה */
    div.stButton > button { 
        border-radius: 16px !important; 
        font-weight: 800 !important; 
        font-size: 1.2rem !important; 
        padding: 16px !important; 
        border: none !important;
        color: white !important;
    }
    div.stButton > button:contains("התחל ריצה") { background: linear-gradient(135deg, #10B981, #059669) !important; }
    div.stButton > button:contains("רשום הקפה") { background: linear-gradient(135deg, #F59E0B, #D97706) !important; }
    div.stButton > button:contains("סיימתי ריצה") { background: linear-gradient(135deg, #EF4444, #DC2626) !important; }
    
    /* קוביות מדדים */
    div[data-testid="metric-container"] { background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 15px; }
    div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-size: 2.2rem !important; font-weight: 800 !important; }
    
    .stMap { border-radius: 18px; overflow: hidden; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציה לשליחת אימייל ---
def send_email_notification(runner_name, duration, laps):
    try:
        sender_email = st.secrets.get("EMAIL_SENDER")
        sender_password = st.secrets.get("EMAIL_PASSWORD")
        receiver_email = st.secrets.get("EMAIL_RECEIVER")
        if sender_email and sender_password and receiver_email:
            msg = EmailMessage()
            msg['Subject'] = f"跑 RunningClub: {runner_name} סיימ/ה ריצה!"
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg.set_content(f"הרץ {runner_name} סיים את האימון.\n\n⏱️ זמן נטו: {duration}\n🔄 סהוחכ הקפות: {laps}")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(sender_email, sender_password.replace(" ", ""))
                smtp.send_message(msg)
    except:
        pass

# --- חיבור ל-Google Sheets ---
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_data = st.secrets["google_json"] if "google_json" in st.secrets else st.secrets
        if isinstance(creds_data, str): creds_data = json.loads(creds_data)
        if "private_key" in creds_data: creds_data["private_key"] = creds_data["private_key"].replace("\\n", "\n")
        client = gspread.authorize(Credentials.from_service_account_info(creds_data, scopes=scopes))
        return client.open("RunningClub_DB").sheet1
    except:
        return None

sheet = init_gsheets()

# ✨ פריצת הדרך: בסיס נתונים גלובלי משותף לכל המכשירים במקביל ✨
@st.cache_resource
def get_global_db():
    return {} # מילון מרכזי שחי על השרת ומשותף לכל מי שנכנס לאתר
global_db = get_global_db()

st.markdown("<h1 style='font-size: 2.5rem; background: linear-gradient(135deg, #38BDF8, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>RunningClub Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; margin-top:-15px; margin-bottom:25px;'>מערכת מעקב וניהול זמנים חיה</p>", unsafe_allow_html=True)

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

# ==========================================
# 📱 אזור הרץ
# ==========================================
with tab_runners:
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    current_runner_input = st.text_input("הקלד/י שם מלא ולחץ/י Enter לרישום:")
    current_runner = current_runner_input.strip()

    if current_runner:
        # אם הרץ לא קיים במסד הנתונים המרכזי - נוסיף אותו
        if current_runner not in global_db:
            global_db[current_runner] = {
                "start": None, "laps": [], "end": None, "duration": None,
                "lat": 32.0853, "lon": 34.7818, "status": "רשום"
            }
        
        runner_data = global_db[current_runner]

        if runner_data["start"] is None:
            if st.button("🟢 התחל ריצה (זינוק!)", use_container_width=True):
                global_db[current_runner]["start"] = datetime.now()
                global_db[current_runner]["status"] = "במסלול"
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.markdown(f"<div style='background-color: rgba(16,185,129,0.1); border: 1px solid #10B981; padding:15px; border-radius:14px; color:#10B981; text-align:center; font-weight:bold; margin-bottom:15px;'>⏱️ השעון שלך רץ! זינוק: {runner_data['start'].strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_duration = datetime.now() - runner_data["start"]
                global_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                
                # סימולציית התקדמות גיאוגרפית על המסלול בכל הקפה
                global_db[current_runner]["lat"] += 0.0004
                global_db[current_runner]["lon"] += 0.0005
                st.toast(f"הקפה נרשמה והמיקום עודכן!", icon="⏱️")
            
            if runner_data["laps"]: 
                st.write("זמני ביניים:", runner_data["laps"])
                
            st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)
            if st.button("🔴 סיימתי ריצה! (עצור שעון)", use_container_width=True):
                end_time = datetime.now()
                global_db[current_runner]["end"] = end_time
                duration = end_time - runner_data["start"]
                global_db[current_runner]["duration"] = duration
                global_db[current_runner]["status"] = "סיום"
                
                final_time_str = str(duration).split('.')[0]
                laps_count = len(runner_data["laps"])
                
                if sheet:
                    try:
                        sheet.append_row([current_runner, runner_data["start"].strftime("%d/%m/%Y %H:%M:%S"), end_time.strftime("%H:%M:%S"), final_time_str, str(runner_data["laps"])])
                        st.toast("✅ נשמר בהצלחה באקסל!", icon="☁️")
                    except: pass
                
                send_email_notification(current_runner, final_time_str, laps_count)
                st.balloons()
                st.rerun()
        else:
            st.markdown(f"<div style='background: linear-gradient(135deg, #064E3B, #065F46); padding: 25px; border-radius: 20px; text-align:center; border: 1px solid #10B981;'><h2 style='color: #34D399; margin:0;'>כל הכבוד! סיימת! 🎉</h2><h1 style='color: white; font-size: 3.5rem; margin-top: 10px;'>{str(runner_data['duration']).split('.')[0]}</h1></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 📊 דשבורד מנהל (מעקב מפות חי בזמן אמת)
# ==========================================
with tab_admin:
    admin_pass = st.text_input("סיסמת מנהל לצפייה במפת המסלול:", type="password")
    
    if admin_pass == "1234":
        active_map_data = []
        finished_runners = []
        running_count = 0
        
        for name, data in global_db.items():
            if data["start"] is not None:
                if data["end"] is None:
                    running_count += 1
                    # רץ פעיל - מוסיפים אותו למפת המעקב החיה
                    active_map_data.append({"שם הרץ": name, "lat": data["lat"], "lon": data["lon"], "סטטוס": "🏃‍♂️ במסלול"})
                else:
                    finished_runners.append({
                        "שם": name, "נטו": str(data["duration"]).split('.')[0], "הקפות": len(data["laps"])
                    })
                    # רץ שסיים - מציגים את נקודת הסיום שלו על המפה בצבע אחר
                    active_map_data.append({"שם הרץ": name, "lat": data["lat"], "lon": data["lon"], "סטטוס": "🏁 סיום"})
                    
        # מדדים עליונים
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("סה״כ זינקו", len(global_db))
        c2.metric("סיימו אימון", len(finished_runners))
        c3.metric("במסלול כעת", running_count)
        
        # 📍 מפת המעקב החיה המרכזית 📍
        st.markdown("<br><h3 style='text-align:right; color:#38BDF8;'>🗺️ מפת מעקב רצים חיה (זמן אמת)</h3>", unsafe_allow_html=True)
        if active_map_data:
            df_map = pd.DataFrame(active_map_data)
            # מציג מפת לווין חיה שמציגה את המיקום של כל רץ ורץ שנמצא כרגע על המסלול!
            st.map(df_map, zoom=14, use_container_width=True)
            st.dataframe(df_map[["שם הרץ", "סטטוס"]], use_container_width=True, hide_index=True)
        else:
            st.info("אין כרגע רצים פעילים על המסלול כדי להציג על המפה.")
            
        # טבלת תוצאות סופיות
        if finished_runners:
            st.markdown("<br><h4 style='text-align:right; color:#10B981;'>🏆 רצים שסיימו את המסלול</h4>", unsafe_allow_html=True)
            df_fin = pd.DataFrame(finished_runners).set_index("שם")
            st.table(df_fin)
            
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        if st.button("🗑️ איפוס אימון מלא ונקיון מפה"):
            global_db.clear()
            st.rerun()
