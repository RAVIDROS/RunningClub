import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# הגדרת עמוד
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;700&display=swap');
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 8px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #0066cc !important; color: white !important; }
    div.stButton > button { border-radius: 12px; font-weight: bold; font-size: 16px; padding: 12px; transition: all 0.3s; }
    </style>
""", unsafe_allow_html=True)

# פונקציית התחברות ל-Google Sheets (חסינת תקלות)
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # זיהוי אוטומטי של איך שהכנסת את הסודות
        if "google_json" in st.secrets:
            creds_data = st.secrets["google_json"]
        else:
            creds_data = st.secrets
            
        if isinstance(creds_data, str):
            creds_data = json.loads(creds_data)
            
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RunningClub_DB").sheet1
    except Exception as e:
        return None

sheet = init_gsheets()

# אתחול נתונים זמני
if 'runners_db' not in st.session_state:
    st.session_state.runners_db = {}

RUNNERS_LIST = ["אבי כהן", "דנה לוי", "יוסי ישראלי", "מיכל גולן", "רוני לוי", "עידו ברק"]

st.markdown("<h1 style='text-align: center; color: #111;'>🏃‍♂️ RunningClub Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>מערכת חכמה לניהול ורישום זמני ריצה</p>", unsafe_allow_html=True)

if not sheet:
    st.warning("⚠️ חיבור לענן חסר. הנתונים נשמרים זמנית בלבד.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

with tab_runners:
    st.subheader("⏱️ רישום אישי")
    current_runner = st.selectbox("אנא בחר את שמך מהרשימה:", ["בחר שם..."] + RUNNERS_LIST)

    if current_runner != "בחר שם...":
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {"start": None, "laps": [], "end": None, "duration": None}
        
        runner_data = st.session_state.runners_db[current_runner]
        
        # --- המעקף המלא: מיקום תמיד מאושר, אין המתנה ל-GPS ---
        location_allowed = True
        with st.expander("📍 בדיקת נוכחות במסלול (בוטל לטובת הבדיקה)", expanded=True):
            st.success("🚀 אימות ה-GPS בוטל זמנית. הכפתור פתוח לזינוק מכל מקום!")

        if runner_data["start"] is None:
            st.info("🏃‍♂️ מוכן לזינוק?")
            if st.button("🟢 התחל ריצה", use_container_width=True, disabled=not location_allowed):
                st.session_state.runners_db[current_runner]["start"] = datetime.now()
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.success(f"⏱️ אתה על המסלול! זינקת בשעה: {runner_data['start'].strftime('%H:%M:%S')}")
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_time = datetime.now()
                lap_duration = lap_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                st.toast(f"הקפה נרשמה: {str(lap_duration).split('.')[0]}", icon="⏱️")
            
            if runner_data["laps"]:
                st.write("זמני הביניים שלך:", runner_data["laps"])
                
            st.divider()
            
            if st.button("🔴 סיימתי ריצה!", use_container_width=True, disabled=not location_allowed):
                end_time = datetime.now()
                st.session_state.runners_db[current_runner]["end"] = end_time
                duration = end_time - runner_data["start"]
                final_duration_str = str(duration).split('.')[0]
                st.session_state.runners_db[current_runner]["duration"] = duration
                
                # שמירה ל-Google Sheets
                if sheet:
                    try:
                        row_data = [
                            current_runner, 
                            runner_data["start"].strftime("%d/%m/%Y %H:%M:%S"),
                            end_time.strftime("%H:%M:%S"),
                            final_duration_str,
                            str(runner_data["laps"])
                        ]
                        sheet.append_row(row_data)
                        st.toast("✅ הנתונים נשלחו בהצלחה לגיליון האקסל!", icon="☁️")
                    except Exception as e:
                        st.error(f"שגיאה בשליחה לגוגל: {e}")
                
                st.balloons()
                st.rerun()
                
        else:
            final_anim = str(runner_data['duration']).split('.')[0]
            st.markdown(f"<h3 style='color: #2ed573; text-align:center;'>כל הכבוד! סיימת בהצלחה! 🎉</h3>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align:center;'>זמן כולל: {final_anim}</h4>", unsafe_allow_html=True)

with tab_admin:
    st.subheader("🔒 ניהול ובקרה")
    admin_pass = st.text_input("סיסמת מנהל:", type="password")
    
    if admin_pass == "1234":
        st.markdown("---")
        records = []
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                records.append({
                    "שם הרץ": name,
                    "שעת התחלה": data["start"].strftime("%H:%M:%S"),
                    "שעת סיום": data["end"].strftime("%H:%M:%S") if data["end"] else "🏃‍♂️ רץ...",
                    "זמן נטו": str(data["duration"]).split('.')[0] if data["duration"] else "",
                    "מספר הקפות": len(data["laps"])
                })
        
        if records:
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        if st.button("🗑️ איפוס מערכת מלא"):
            st.session_state.runners_db = {}
            st.rerun()
