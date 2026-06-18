import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

# הגדרת עמוד למובייל - פריסה רחבה
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- ארכיטקטורת עיצוב פרימיום למובייל (CSS נקי ויציב) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;600;700;800&display=swap');
    
    /* הגדרות כלליות ומניעת גלילה אופקית */
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    
    /* רקע האפליקציה (Dark Mode אלגנטי) */
    .stApp {
        background-color: #0F172A !important;
    }
    
    /* העלמת סרגלים מיותרים של סטרימליט */
    header, footer, #MainMenu { visibility: hidden !important; }
    
    /* כותרות ראשיות */
    h1, h2, h3 {
        color: #F8FAFC !important;
        text-align: center !important;
    }
    
    /* עיצוב תיבת הטקסט (שם הרץ) שיהיה קריא באייפון! */
    div[data-testid="stTextInput"] label p {
        color: #38BDF8 !important; /* תכלת זוהר */
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stTextInput"] input {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border: 2px solid #334155 !important;
        border-radius: 12px !important;
        padding: 15px !important;
        font-size: 1.2rem !important;
        text-align: right !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.3) !important;
    }

    /* עיצוב הלשוניות העליונות */
    div[data-testid="stTabs"] button {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 20px;
        color: #94A3B8;
        padding: 10px 20px;
        margin: 0 5px;
        font-weight: bold;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6, #1D4ED8) !important;
        color: #FFFFFF !important;
        border: none;
    }
    
    /* עיצוב כפתורי הענק */
    div.stButton > button { 
        border-radius: 16px !important; 
        font-weight: 800 !important; 
        font-size: 1.2rem !important; 
        padding: 15px !important; 
        border: none !important;
        width: 100% !important;
        color: white !important;
        margin-top: 10px !important;
    }
    
    /* צבעים ספציפיים לכפתורים לפי הטקסט שלהם */
    div.stButton > button:contains("התחל ריצה") {
        background: linear-gradient(135deg, #10B981, #059669) !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
    }
    div.stButton > button:contains("רשום הקפה") {
        background: linear-gradient(135deg, #F59E0B, #D97706) !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3) !important;
    }
    div.stButton > button:contains("סיימתי ריצה") {
        background: linear-gradient(135deg, #EF4444, #DC2626) !important;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4) !important;
    }
    
    /* מדדים של המנהל (KPI) */
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 15px;
        text-align: center;
    }
    div[data-testid="stMetricValue"] {
        color: #38BDF8 !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
    }
    
    /* עיצוב טבלאות נקי */
    table { width: 100% !important; background-color: #1E293B !important; color: white !important; border-radius: 10px; overflow: hidden; }
    th { background-color: #0F172A !important; color: #38BDF8 !important; text-align: right !important; padding: 12px !important;}
    td { padding: 12px !important; border-bottom: 1px solid #334155 !important; }
    
    /* התראות והודעות (Success/Error/Info) */
    div[data-testid="stAlert"] {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

def send_email_notification(runner_name, duration, laps):
    try:
        sender_email = st.secrets.get("EMAIL_SENDER")
        sender_password = st.secrets.get("EMAIL_PASSWORD")
        receiver_email = st.secrets.get("EMAIL_RECEIVER")
        
        if not sender_email or not sender_password or not receiver_email:
            return 
            
        msg = EmailMessage()
        msg['Subject'] = f"🏃‍♂️ עדכון מהמסלול: {runner_name} סיים כעת!"
        msg['From'] = sender_email
        msg['To'] = receiver_email
        
        content = f"""
        שלום למנהל,
        
        הרץ {runner_name} סיים כעת את האימון בהצלחה.
        
        ⏱️ זמן נטו: {duration}
        🔄 מספר הקפות שנרשמו: {laps}
        
        המערכת,
        RunningClub Pro
        """
        msg.set_content(content)
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            clean_password = sender_password.replace(" ", "")
            smtp.login(sender_email, clean_password)
            smtp.send_message(msg)
    except Exception as e:
        pass

@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "google_json" in st.secrets:
            raw_creds = st.secrets["google_json"]
            if isinstance(raw_creds, str):
                creds_dict = json.loads(raw_creds)
            else:
                creds_dict = dict(raw_creds)
        else:
            creds_dict = dict(st.secrets)
            
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RunningClub_DB").sheet1
    except Exception as e:
        return None

sheet = init_gsheets()

if 'runners_db' not in st.session_state:
    st.session_state.runners_db = {}

# כותרת ראשית של האפליקציה
st.title("🏃‍♂️ RunningClub Pro")
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.1rem; margin-top: -15px; margin-bottom: 30px;'>מערכת ניהול ריצה חכמה</p>", unsafe_allow_html=True)

if not sheet:
    st.error("⚠️ חיבור לענן נכשל. הנתונים לא יישמרו באקסל. ודא שהסודות שמורים ב-Streamlit.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

with tab_runners:
    st.subheader("⏱️ רישום וזינוק אישי")
    
    current_runner_input = st.text_input("הקלד/י שם מלא ולחץ/י Enter:")
    current_runner = current_runner_input.strip()

    if current_runner:
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {"start": None, "laps": [], "end": None, "duration": None}
        
        runner_data = st.session_state.runners_db[current_runner]
        location_allowed = True

        if runner_data["start"] is None:
            if st.button("🟢 התחל ריצה (זינוק!)", use_container_width=True, disabled=not location_allowed):
                st.session_state.runners_db[current_runner]["start"] = datetime.now()
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.info(f"⏱️ מעולה! זינקת בשעה: {runner_data['start'].strftime('%H:%M:%S')}")
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_time = datetime.now()
                lap_duration = lap_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                st.toast(f"הקפה נרשמה: {str(lap_duration).split('.')[0]}", icon="⏱️")
            
            if runner_data["laps"]:
                st.write("זמני ביניים:", runner_data["laps"])
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🔴 סיימתי ריצה! (עצור שעון)", use_container_width=True, disabled=not location_allowed):
                end_time = datetime.now()
                st.session_state.runners_db[current_runner]["end"] = end_time
                duration = end_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["duration"] = duration
                
                final_time_str = str(duration).split('.')[0]
                laps_count = len(runner_data["laps"])
                
                if sheet:
                    try:
                        row_data = [
                            current_runner, 
                            runner_data["start"].strftime("%d/%m/%Y %H:%M:%S"),
                            end_time.strftime("%H:%M:%S"),
                            final_time_str,
                            str(runner_data["laps"])
                        ]
                        sheet.append_row(row_data)
                        st.toast("✅ נשמר בהצלחה בענן!", icon="☁️")
                    except Exception as e:
                        st.error(f"שגיאה בשליחה: {e}")
                
                send_email_notification(current_runner, final_time_str, laps_count)
                st.balloons()
                st.rerun()
                
        else:
            final_anim = str(runner_data['duration']).split('.')[0]
            st.success("🎉 סיימת בהצלחה!")
            st.markdown(f"<h1 style='color: #10B981; font-size: 3.5rem;'>{final_anim}</h1>", unsafe_allow_html=True)

with tab_admin:
    st.subheader("🔒 מרכז שליטה")
    admin_pass = st.text_input("סיסמת מנהל:", type="password")
    
    if admin_pass == "1234":
        records = []
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                total_sec = data["duration"].total_seconds() if data["duration"] else 999999
                records.append({
                    "שם הרץ": name,
                    "שעת התחלה": data["start"].strftime("%H:%M:%S"),
                    "שעת סיום": data["end"].strftime("%H:%M:%S") if data["end"] else "רץ כעת",
                    "זמן נטו": str(data["duration"]).split('.')[0] if data["duration"] else "-",
                    "הקפות": len(data["laps"]),
                    "_sort_val": total_sec 
                })
        
        if records:
            df = pd.DataFrame(records)
            df_finished = df[df["זמן נטו"] != "-"].sort_values(by="_sort_val").drop(columns=["_sort_val"])
            df_running = df[df["זמן נטו"] == "-"].drop(columns=["_sort_val"])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("זינקו", len(df))
            c2.metric("סיימו", len(df_finished))
            c3.metric("במסלול", len(df_running))
            
            if not df_finished.empty:
                st.subheader("🏆 תוצאות (המהיר ביותר)")
                df_finished = df_finished.rename(columns={"זמן נטו": "⏱️ נטו", "הקפות": "🔄 הקפות"})
                df_finished.set_index("שם הרץ", inplace=True)
                st.table(df_finished)
                
            if not df_running.empty:
                st.subheader("🏃‍♂️ רצים כעת")
                df_running.set_index("שם הרץ", inplace=True)
                st.table(df_running)
            
        else:
            st.info("המסלול פנוי. טרם נרשמו זינוקים.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ איפוס מערכת מלא (מחיקת זמנים)"):
            st.session_state.runners_db = {}
            st.rerun()
