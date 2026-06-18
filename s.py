import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

# הגדרת עמוד
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- ארכיטקטורת עיצוב פרימיום למובייל (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;600;700;800&display=swap');
    
    /* הגדרת רקע האפליקציה וצמצום שוליים למובייל */
    .stApp {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    
    /* החבאת אלמנטים של מערכת השרת למראה אפליקציה נקייה */
    #MainMenu, header, footer { visibility: hidden !important; }
    
    /* גופנים וכיוון עברית */
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    
    /* כותרת ראשית מעוצבת ספורט-אקסטרים */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #38BDF8, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        text-align: center;
        color: #94A3B8;
        font-size: 16px;
        margin-bottom: 25px;
        font-weight: 400;
    }
    
    /* עיצוב לשוניות מובייל עגולות חלקות */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        border-bottom: none; 
        justify-content: center; 
        margin-bottom: 25px;
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: #1E293B; 
        border-radius: 40px; 
        padding: 12px 28px; 
        font-weight: 700;
        color: #94A3B8;
        border: 1px solid #334155;
        transition: all 0.25s ease;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(135deg, #3B82F6, #1D4ED8) !important;
        color: #FFFFFF !important;
        border: none;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
    }
    
    /* עיצוב כרטיסיות צפות (Cards) לאלמנטים השונים */
    .custom-card {
        background-color: #1E293B;
        border-radius: 24px;
        padding: 22px;
        border: 1px solid #334155;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
    }
    
    /* עיצוב תיבות הטקסט והקלטים */
    .stTextInput input {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border-radius: 16px !important;
        border: 2px solid #334155 !important;
        padding: 14px !important;
        font-size: 16px !important;
        transition: all 0.3s;
    }
    .stTextInput input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15) !important;
    }
    
    /* כפתורי ענק מעוצבים למובייל בריצה */
    div.stButton > button { 
        border-radius: 20px; 
        font-weight: 700; 
        font-size: 18px; 
        padding: 16px 20px; 
        border: none;
        width: 100% !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase;
    }
    
    /* כפתור התחלה - ירוק זוהר */
    div.stButton > button:contains("🟢") {
        background: linear-gradient(135deg, #10B981, #059669) !important;
        color: white !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3) !important;
    }
    
    /* כפתור הקפה - צהוב ספורטיבי */
    div.stButton > button:contains("🟡") {
        background: linear-gradient(135deg, #F59E0B, #D97706) !important;
        color: white !important;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.2) !important;
    }
    
    /* כפתור סיום - אדום אגרסיבי */
    div.stButton > button:contains("🔴") {
        background: linear-gradient(135deg, #EF4444, #DC2626) !important;
        color: white !important;
        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.3) !important;
    }
    
    div.stButton > button:active {
        transform: scale(0.96);
    }
    
    /* עיצוב כרטיסיות נתונים עליונות (KPIs) במנהל */
    [data-testid="metric-container"] {
        background-color: #1E293B;
        border-radius: 20px;
        padding: 16px;
        border: 1px solid #334155;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] { 
        font-size: 2.2rem !important; 
        font-weight: 800 !important;
        color: #38BDF8 !important; 
    }
    [data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-size: 14px !important;
    }
    
    /* עיצוב טבלאות פרימיום חסין קטיעות למובייל */
    .table-container {
        overflow-x: auto;
        border-radius: 18px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        margin-top: 15px;
    }
    table { 
        width: 100% !important; 
        border-collapse: collapse; 
        background-color: #1E293B;
    }
    thead th { 
        background-color: #0F172A !important; 
        color: #38BDF8 !important; 
        padding: 16px 12px !important; 
        text-align: right !important; 
        font-weight: 700;
        font-size: 15px;
        border-bottom: 2px solid #334155;
    }
    tbody td { 
        padding: 16px 12px !important; 
        border-bottom: 1px solid #334155 !important; 
        color: #E2E8F0 !important;
        font-size: 15px;
        white-space: nowrap;
    }
    tbody tr:last-child td { border-bottom: none; }
    
    /* עיצוב הודעות מערכת */
    .stAlert {
        border-radius: 16px !important;
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
    }
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

# מבנה עליון חלק ואסתטי
st.markdown("<div class='main-title'>RunningClub Pro</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>מערכת חכמה לניהול ואימוני ריצה</div>", unsafe_allow_html=True)

if not sheet:
    st.error("⚠️ חיבור לענן נכשל. הנתונים לא יישמרו באקסל. ודא שהסודות שמורים ב-Streamlit.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

with tab_runners:
    # עטיפת ממשק הרץ בתוך קופסה מעוצבת
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #38BDF8; margin-top:0; margin-bottom:15px;'>⏱️ רישום וזינוק אישי</h4>", unsafe_allow_html=True)
    
    current_runner_input = st.text_input("הקלד/י שם מלא ולחץ/י Enter במסך המקלדת:")
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
            st.markdown(f"<div style='background-color: rgba(59,130,246,0.1); border: 1px solid #3B82F6; padding:12px; border-radius:12px; color:#38BDF8; text-align:center; font-weight:600; margin-bottom:15px;'>⏱️ אתה על המסלול! זינוק: {runner_data['start'].strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_time = datetime.now()
                lap_duration = lap_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                st.toast(f"הקפה נרשמה: {str(lap_duration).split('.')[0]}", icon="⏱️")
            
            if runner_data["laps"]:
                st.markdown("<p style='color:#94A3B8; margin-top:10px; font-size:14px;'>זמני ביניים שנרשמו:</p>", unsafe_allow_html=True)
                st.write(runner_data["laps"])
                
            st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)
            
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
            st.markdown(f"<div style='background: linear-gradient(135deg, #064E3B, #065F46); padding: 25px; border-radius: 20px; text-align:center; border: 1px solid #10B981;'><h2 style='color: #34D399; margin:0; font-weight:700;'>כל הכבוד! סיימת בהצלחה! 🎉</h2><h1 style='color: #FFFFFF; font-size: 3.5rem; margin-top: 10px; font-weight:800;'>{final_anim}</h1></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_admin:
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #38BDF8; margin-top:0; margin-bottom:15px;'>🔒 אבטחת מנהל</h4>", unsafe_allow_html=True)
    admin_pass = st.text_input("סיסמת מנהל:", type="password")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if admin_pass == "1234":
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
            
            # קוביות מדדים יפהפיות
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("סה״כ זינקו", len(df))
            c2.metric("סיימו ריצה", len(df_finished))
            c3.metric("במסלול כעת", len(df_running))
            
            # טבלאות מותאמות מובייל בתוך קונטיינר גלול
            if not df_finished.empty:
                st.markdown("<br><h4 style='color: #38BDF8; margin-bottom:5px;'>🏆 טבלת תוצאות (לפי המהיר ביותר)</h4>", unsafe_allow_html=True)
                df_finished = df_finished.rename(columns={"זמן נטו": "⏱️ נטו", "הקפות": "🔄 הקפות"})
                df_finished.set_index("שם הרץ", inplace=True)
                
                st.markdown("<div class='table-container'>", unsafe_allow_html=True)
                st.table(df_finished)
                st.markdown("</div>", unsafe_allow_html=True)
                
            if not df_running.empty:
                st.markdown("<br><h4 style='color: #F59E0B; margin-bottom:5px;'>🏃‍♂️ רצים פעילים כעת</h4>", unsafe_allow_html=True)
                df_running.set_index("שם הרץ", inplace=True)
                
                st.markdown("<div class='table-container'>", unsafe_allow_html=True)
                st.table(df_running)
                st.markdown("</div>", unsafe_allow_html=True)
            
        else:
            st.markdown("<div style='text-align:center; color:#94A3B8; padding:20px;'>טרם נרשמו זינוקים לאימון זה. המסלול פנוי! 💨</div>", unsafe_allow_html=True)
            
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🗑️ איפוס מערכת מלא (מחיקת זמנים זמניים)"):
            st.session_state.runners_db = {}
            st.rerun()
