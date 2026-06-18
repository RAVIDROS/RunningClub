import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.message import EmailMessage
import ssl

# הגדרת עמוד למובייל ומחשב - פריסה מותאמת
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- ארכיטקטורת עיצוב פרימיום ספורט (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;600;700;800&display=swap');
    
    /* הגדרות כלליות */
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    
    /* רקע אקסטרים דארק */
    .stApp { background-color: #0F172A !important; }
    
    header, footer, #MainMenu { visibility: hidden !important; }
    
    h1, h2, h3, h4 { color: #F8FAFC !important; text-align: center !important; font-weight: 800; }
    
    /* עיצוב כרטיסיות הרצים המעוצבות (כמו Strava) */
    .runner-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 24px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    
    .runner-header {
        font-size: 20px;
        font-weight: 800;
        color: #38BDF8;
        border-bottom: 1px solid #334155;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    
    .stat-line {
        font-size: 16px;
        color: #E2E8F0;
        margin-bottom: 8px;
    }

    /* תיבת קלט שם */
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
    
    /* כפתורי ריצה ענקיים */
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
    
    /* קוביות סטטיסטיקה */
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 15px;
    }
    div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-size: 2.2rem !important; font-weight: 800 !important; }
    
    /* עיצוב אלמנט המפה של סטרימליט שיתאים לרקע */
    .stMap { border-radius: 16px; overflow: hidden; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

def send_email_notification(runner_name, duration, laps):
    try:
        sender_email = st.secrets.get("EMAIL_SENDER")
        sender_password = st.secrets.get("EMAIL_PASSWORD")
        receiver_email = st.secrets.get("EMAIL_RECEIVER")
        if sender_email and sender_password and receiver_email:
            msg = EmailMessage()
            msg['Subject'] = f"🏃‍♂️ עדכון מהמסלול: {runner_name} סיים כעת!"
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg.set_content(f"שלום למנהל,\n\nהרץ {runner_name} סיים את האימון.\n\n⏱️ זמן נטו: {duration}\n🔄 הקפות: {laps}\n\nRunningClub Pro")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(sender_email, sender_password.replace(" ", ""))
                smtp.send_message(msg)
    except:
        pass

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
if 'runners_db' not in st.session_state: st.session_state.runners_db = {}

st.markdown("<h1 style='font-size: 2.5rem; background: linear-gradient(135deg, #38BDF8, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>RunningClub Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; margin-top:-15px; margin-bottom:25px;'>מערכת ניהול ומעקב אימונים דינמית</p>", unsafe_allow_html=True)

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

# ==========================================
# 📱 לשונית הרצים
# ==========================================
with tab_runners:
    st.markdown("<div class='runner-card'>", unsafe_allow_html=True)
    current_runner_input = st.text_input("הקלד/י שם מלא ולחץ/י Enter לזינוק:")
    current_runner = current_runner_input.strip()

    if current_runner:
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {"start": None, "laps": [], "end": None, "duration": None}
        
        runner_data = st.session_state.runners_db[current_runner]

        if runner_data["start"] is None:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🟢 התחל ריצה (זינוק!)", use_container_width=True):
                st.session_state.runners_db[current_runner]["start"] = datetime.now()
                st.rerun()
                
        elif runner_data["start"] is not None and runner_data["end"] is None:
            st.markdown(f"<div style='background-color: rgba(56,189,248,0.1); border: 1px solid #38BDF8; padding:15px; border-radius:14px; color:#38BDF8; text-align:center; font-weight:bold; margin-bottom:15px;'>⏱️ השעון רץ! זינקת בשעה: {runner_data['start'].strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
            
            if st.button("🟡 רשום הקפה / זמן ביניים", use_container_width=True):
                lap_duration = datetime.now() - runner_data["start"]
                st.session_state.runners_db[current_runner]["laps"].append(str(lap_duration).split('.')[0])
                st.toast(f"הקפה נרשמה!", icon="⏱️")
            
            if runner_data["laps"]: st.write("זמני ביניים:", runner_data["laps"])
                
            st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)
            if st.button("🔴 סיימתי ריצה! (עצור שעון)", use_container_width=True):
                end_time = datetime.now()
                st.session_state.runners_db[current_runner]["end"] = end_time
                duration = end_time - runner_data["start"]
                st.session_state.runners_db[current_runner]["duration"] = duration
                
                final_time_str = str(duration).split('.')[0]
                laps_count = len(runner_data["laps"])
                
                if sheet:
                    try:
                        sheet.append_row([current_runner, runner_data["start"].strftime("%d/%m/%Y %H:%M:%S"), end_time.strftime("%H:%M:%S"), final_time_str, str(runner_data["laps"])])
                        st.toast("✅ נשמר באקסל!", icon="☁️")
                    except: pass
                
                send_email_notification(current_runner, final_time_str, laps_count)
                st.balloons()
                st.rerun()
        else:
            st.markdown(f"<div style='background: linear-gradient(135deg, #064E3B, #065F46); padding: 25px; border-radius: 20px; text-align:center; border: 1px solid #10B981;'><h2 style='color: #34D399; margin:0;'>אימון בוצע בהצלחה! 🎉</h2><h1 style='color: white; font-size: 3.5rem; margin-top: 10px;'>{str(runner_data['duration']).split('.')[0]}</h1></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 📊 דשבורד מנהל (עם מפות)
# ==========================================
with tab_admin:
    admin_pass = st.text_input("סיסמת מנהל לגישה לנתונים:", type="password")
    
    if admin_pass == "1234":
        finished_runners = []
        running_count = 0
        
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                if data["end"]:
                    finished_runners.append({
                        "שם": name, "התחלה": data["start"].strftime("%H:%M:%S"),
                        "סיום": data["end"].strftime("%H:%M:%S"), "נטו": str(data["duration"]).split('.')[0],
                        "הקפות": len(data["laps"]), "שניות": data["duration"].total_seconds()
                    })
                else:
                    running_count += 1
                    
        # קוביות מדדים חיות עליונות
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("סה״כ זינקו", len(finished_runners) + running_count)
        c2.metric("סיימו אימון", len(finished_runners))
        c3.metric("במסלול כעת", running_count)
        st.markdown("---")
        
        if finished_runners:
            st.markdown("<h3 style='text-align:right; color:#38BDF8; margin-bottom:20px;'>🏆 כרטיסיות תוצאות ומסלולי רצים</h3>", unsafe_allow_html=True)
            
            # מיון הרצים מהמהיר ביותר לאיטי ביותר
            df = pd.DataFrame(finished_runners).sort_values(by="שניות")
            
            for index, runner in df.iterrows():
                # יצירת קופסת Strava יוקרתית לכל רץ בנפרד
                st.markdown(f"""
                <div class='runner-card'>
                    <div class='runner-header'>🏅 מקום {index+1}: {runner['שם']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # חלוקה לשני טורים בפנים: ימין נתונים, שמאל מפה!
                col_data, col_map = st.columns([1, 1.2])
                
                with col_data:
                    st.markdown(f"<div class='stat-line'>⏱️ **זמן סופי:** <span style='color:#10B981; font-weight:bold; font-size:1.2rem;'>{runner['נטו']}</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='stat-line'>🔄 **הקפות שנרשמו:** {runner['הקפות']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='stat-line'>🛫 **שעת זינוק:** {runner['התחלה']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='stat-line'>🏁 **שעת הגעה:** {runner['סיום']}</div>", unsafe_allow_html=True)
                    
                with col_map:
                    # 📍 הגדרת נקודות הציון של המפה (תוכל להחליף את המספרים פה במסלול האמיתי שלכם)
                    # המסלול כרגע מוגדר כטבעת היקפית סביב נקודת הבסיס
                    route_data = pd.DataFrame({
                        'lat': [32.0853, 32.0865, 32.0865, 32.0853, 32.0853],
                        'lon': [34.7818, 34.7818, 34.7835, 34.7835, 34.7818]
                    })
                    # הצגת המפה הקטנה והאינטראקטיבית ליד הרץ
                    st.map(route_data, zoom=14, use_container_width=True)
                    
                st.markdown("<div style='margin-bottom:30px;'></div>", unsafe_allow_html=True)
        else:
            st.info("ממתין לסיום הרץ הראשון כדי להציג מפות ותוצאות.")
            
        if st.button("🗑️ איפוס אימון מלא"):
            st.session_state.runners_db = {}
            st.rerun()
