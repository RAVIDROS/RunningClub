import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

# הגדרת עמוד - פריסה רחבה יותר לאסתטיקה
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- קסם העיצוב (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;600;800&display=swap');
    
    /* הגדרות כלליות */
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    
    /* עיצוב כותרת ראשית */
    h1 {
        background: -webkit-linear-gradient(45deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.05);
    }
    
    /* עיצוב הלשוניות (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; border-bottom: none; justify-content: center; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab"] { 
        background-color: #ffffff; 
        border-radius: 30px; 
        padding: 10px 25px; 
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        border: none;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
    }
    
    /* עיצוב כפתורים מרהיב */
    div.stButton > button { 
        border-radius: 50px; 
        font-weight: bold; 
        font-size: 18px; 
        padding: 15px 30px; 
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background-color: #ffffff;
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    /* עיצוב תיבות הקלט */
    .stTextInput input, .stSelectbox > div > div {
        border-radius: 15px;
        border: 2px solid #e5e7eb;
        padding: 12px;
        transition: border-color 0.3s;
    }
    .stTextInput input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    /* עיצוב כרטיסיות נתונים (KPIs) */
    [data-testid="metric-container"] {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        border: 1px solid #f3f4f6;
        text-align: center;
        transition: transform 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-5px);
    }
    [data-testid="stMetricValue"] { 
        font-size: 2.5rem; 
        font-weight: 800;
        color: #1e40af; 
    }
    
    /* עיצוב טבלאות מודרני */
    table { 
        width: 100% !important; 
        border-collapse: collapse; 
        border-radius: 15px; 
        overflow: hidden; 
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        margin-top: 15px;
        background-color: white;
    }
    thead th { 
        background: #1e3a8a !important; 
        color: white !important; 
        padding: 15px !important; 
        text-align: right !important; 
        font-weight: 600;
        font-size: 16px;
    }
    tbody td { 
        padding: 15px !important; 
        border-bottom: 1px solid #f3f4f6 !important; 
        color: #374151 !important;
        font-size: 16px;
    }
    tbody tr:hover { 
        background-color: #f8fafc !important; 
    }
    
    /* תיקון צבעים למצב Dark Mode (כדי שהטקסט בטבלה יישאר קריא) */
    @media (prefers-color-scheme: dark) {
        tbody td { color: #f3f4f6 !important; }
        table { background-color: #1f2937; }
        tbody tr:hover { background-color: #374151 !important; }
        [data-testid="metric-container"], .stTabs [data-baseweb="tab"] { background-color: #1f2937; border-color: #374151;}
        div.stButton > button { background-color: #1f2937; border: 1px solid #374151; color: white;}
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

st.markdown("<br><h1 style='text-align: center;'>🏃‍♂️ RunningClub Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6b7280; font-size: 18px; margin-bottom: 30px;'>מערכת חכמה לניהול ורישום זמני ריצה</p>", unsafe_allow_html=True)

if not sheet:
    st.error("⚠️ חיבור לענן נכשל. הנתונים לא יישמרו באקסל. ודא שהסודות שמורים ב-Streamlit.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

with tab_runners:
    st.markdown("<h3 style='color: #1e3a8a;'>⏱️ רישום אישי לזינוק</h3>", unsafe_allow_html=True)
    
    current_runner_input = st.text_input("📝 הקלד/י את שמך המלא ולחץ/י Enter:")
    current_runner = current_runner_input.strip()

    if current_runner:
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {"start": None, "laps": [], "end": None, "duration": None}
        
        runner_data = st.session_state.runners_db[current_runner]
        location_allowed = True

        if runner_data["start"] is None:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🟢 התחל ריצה (זינוק!)", use_container_width=True, disabled=not location_allowed):
                st.session_state.runners_db[current_runner]["start"] = datetime.now()
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.success(f"⏱️ אתה על המסלול! זינקת בשעה: {runner_data['start'].strftime('%H:%M:%S')}")
            st.info("💡 הקפד להשאיר את השם שלך מוקלד בתיבה כדי לראות את כפתור הסיום.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_time = datetime.now()
                lap_duration = lap_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                st.toast(f"הקפה נרשמה: {str(lap_duration).split('.')[0]}", icon="⏱️")
            
            if runner_data["laps"]:
                st.write("זמני הביניים שלך:", runner_data["laps"])
                
            st.markdown("<br><hr><br>", unsafe_allow_html=True)
            
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
                        st.toast("✅ הנתונים נשלחו בהצלחה לגיליון האקסל!", icon="☁️")
                    except Exception as e:
                        st.error(f"שגיאה בשליחה: {e}")
                
                send_email_notification(current_runner, final_time_str, laps_count)
                st.balloons()
                st.rerun()
                
        else:
            final_anim = str(runner_data['duration']).split('.')[0]
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: #d1fae5; padding: 20px; border-radius: 15px; text-align:center; border: 2px solid #34d399;'><h2 style='color: #065f46; margin:0;'>כל הכבוד! סיימת בהצלחה! 🎉</h2><h1 style='color: #047857; font-size: 3rem; margin-top: 10px;'>{final_anim}</h1></div>", unsafe_allow_html=True)

with tab_admin:
    st.markdown("<h3 style='color: #1e3a8a;'>🔒 מרכז שליטה ובקרה</h3>", unsafe_allow_html=True)
    admin_pass = st.text_input("סיסמת מנהל (הזן ולחץ Enter):", type="password")
    
    if admin_pass == "1234":
        st.markdown("<br>", unsafe_allow_html=True)
        records = []
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                total_sec = data["duration"].total_seconds() if data["duration"] else 999999
                records.append({
                    "שם הרץ": name,
                    "שעת התחלה": data["start"].strftime("%H:%M:%S"),
                    "שעת סיום": data["end"].strftime("%H:%M:%S") if data["end"] else "🏃‍♂️ רץ כעת...",
                    "זמן נטו": str(data["duration"]).split('.')[0] if data["duration"] else "-",
                    "הקפות": len(data["laps"]),
                    "_sort_val": total_sec 
                })
        
        if records:
            df = pd.DataFrame(records)
            df_finished = df[df["זמן נטו"] != "-"].sort_values(by="_sort_val").drop(columns=["_sort_val"])
            df_running = df[df["זמן נטו"] == "-"].drop(columns=["_sort_val"])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("סה״כ זינקו", len(df))
            c2.metric("סיימו ריצה", len(df_finished))
            c3.metric("עדיין במסלול", len(df_running))
            
            st.markdown("<br><h4 style='color: #1e40af;'>🏆 טבלת תוצאות (מוינו לפי המהיר ביותר)</h4>", unsafe_allow_html=True)
            if not df_finished.empty:
                df_finished = df_finished.rename(columns={"זמן נטו": "⏱️ זמן נטו", "הקפות": "🔄 הקפות"})
                df_finished.set_index("שם הרץ", inplace=True)
                st.table(df_finished)
            else:
                st.info("אין עדיין מסיימים להציג.")
                
            if not df_running.empty:
                st.markdown("<br><h4 style='color: #b45309;'>🏃‍♂️ רצים פעילים כעת</h4>", unsafe_allow_html=True)
                df_running.set_index("שם הרץ", inplace=True)
                st.table(df_running)
            
        else:
            st.info("טרם נרשמו זינוקים לאימון זה. המסלול ריק! 🌬️")
            
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        if st.button("🗑️ איפוס מערכת מלא (מחיקת זמנים זמניים)"):
            st.session_state.runners_db = {}
            st.rerun()
