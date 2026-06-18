import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;700&display=swap');
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 8px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #0066cc !important; color: white !important; }
    div.stButton > button { border-radius: 12px; font-weight: bold; font-size: 16px; padding: 12px; transition: all 0.3s; }
    [data-testid="stMetricValue"] { font-size: 2rem; color: #0066cc; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציה לשליחת אימייל ---
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

st.markdown("<h1 style='text-align: center; color: #111;'>🏃‍♂️ RunningClub Pro</h1>", unsafe_allow_html=True)

if not sheet:
    st.error("⚠️ חיבור לענן נכשל. הנתונים לא יישמרו באקסל. ודא שהסודות שמורים ב-Streamlit.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

with tab_runners:
    st.subheader("⏱️ רישום אישי")
    
    current_runner_input = st.text_input("📝 הקלד/י את שמך המלא ולחץ/י Enter:")
    current_runner = current_runner_input.strip()

    if current_runner:
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {"start": None, "laps": [], "end": None, "duration": None}
        
        runner_data = st.session_state.runners_db[current_runner]
        location_allowed = True

        if runner_data["start"] is None:
            if st.button("🟢 התחל ריצה", use_container_width=True, disabled=not location_allowed):
                st.session_state.runners_db[current_runner]["start"] = datetime.now()
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.success(f"⏱️ אתה על המסלול! זינקת בשעה: {runner_data['start'].strftime('%H:%M:%S')}")
            st.info("💡 הקפד להשאיר את השם שלך מוקלד בתיבה כדי לראות את כפתור הסיום.")
            
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
            st.markdown(f"<h3 style='color: #2ed573; text-align:center;'>כל הכבוד! סיימת בהצלחה! 🎉</h3>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align:center;'>זמן כולל: {final_anim}</h4>", unsafe_allow_html=True)

with tab_admin:
    st.subheader("🔒 דשבורד מנהל")
    admin_pass = st.text_input("סיסמת מנהל:", type="password")
    
    if admin_pass == "1234":
        st.markdown("---")
        records = []
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                total_sec = data["duration"].total_seconds() if data["duration"] else 999999
                records.append({
                    "שם הרץ": name,
                    "שעת התחלה": data["start"].strftime("%H:%M:%S"),
                    "שעת סיום": data["end"].strftime("%H:%M:%S") if data["end"] else "🏃‍♂️ על המסלול",
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
            
            st.markdown("### 🏆 טבלת תוצאות (מוינו לפי המהיר ביותר)")
            if not df_finished.empty:
                # הוספת האייקונים לשם העמודה במקום להשתמש ב-column_config ששובר את התצוגה
                df_finished = df_finished.rename(columns={"זמן נטו": "⏱️ זמן נטו", "הקפות": "🔄 הקפות"})
                
                # הצגת הטבלה ברוחב מלא וחופשי - ללא הגבלת עמודות שתמעך את הטקסט!
                st.dataframe(df_finished, use_container_width=True, hide_index=True)
            else:
                st.info("אין עדיין מסיימים להציג.")
                
            if not df_running.empty:
                st.markdown("### 🏃‍♂️ רצים פעילים כעת")
                st.dataframe(df_running, use_container_width=True, hide_index=True)
            
        else:
            st.info("טרם נרשמו זינוקים לאימון זה.")
            
        st.markdown("---")
        if st.button("🗑️ איפוס מערכת מלא (מחיקת זמנים זמניים)"):
            st.session_state.runners_db = {}
            st.rerun()
