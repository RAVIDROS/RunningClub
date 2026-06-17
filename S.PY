import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import math
from streamlit_js_eval import streamlit_js_eval

# הגדרת מבנה עמוד ועיצוב רטרו-ספורטיבי נקי
st.set_page_config(page_title="RunningClub Pro", page_icon="🏃‍♂️", layout="centered")

# --- הזרקת עיצוב CSS מותאם אישית לחוויה מעוצבת ומקצועית ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght=300;400;700&display=swap');
    * { font-family: 'Assistant', sans-serif; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #0066cc !important;
        color: white !important;
    }
    div.stButton > button {
        border-radius: 12px;
        font-weight: bold;
        font-size: 16px;
        padding: 12px;
        transition: all 0.3s;
    }
    </style>
""", unsafe_allow_html=True)

# --- אתחול הגדרות ה-GPS בזיכרון המערכת (ערכי ברירת מחדל) ---
if 'target_lat' not in st.session_state:
    st.session_state.target_lat = 32.085300  # ברירת מחדל התחלתית
if 'target_lon' not in st.session_state:
    st.session_state.target_lon = 34.781800
if 'max_distance' not in st.session_state:
    st.session_state.max_distance = 150  # רדיוס מותר במטרים

# פונקציה לחישוב מרחק במטרים בין 2 נקודות GPS (נוסחת האברסין)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # רדיוס כדור הארץ במטרים
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- פונקציית התחברות ל-Google Sheets ---
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RunningClub_DB").sheet1
    except Exception as e:
        return None

sheet = init_gsheets()

# --- אתחול בסיס הנתונים הזמני בזיכרון המערכת ---
if 'runners_db' not in st.session_state:
    st.session_state.runners_db = {}

# רשימת הרצים הרשמית של המועדון
RUNNERS_LIST = ["אבי כהן", "דנה לוי", "יוסי ישראלי", "מיכל גולן", "רוני לוי", "עידו ברק"]

# --- בדיקת פרמטרים ב-URL (מנגנון ה-QR קוד) ---
url_params = st.query_params
suggested_runner = url_params.get("runner", "בחר שם...")

if suggested_runner in [r.replace(" ", "_") for r in RUNNERS_LIST]:
    suggested_runner = suggested_runner.replace("_", " ")

st.markdown("<h1 style='text-align: center; color: #111;'>🏃‍♂️ RunningClub Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>מערכת חכמה לניהול ורישום זמני ריצה</p>", unsafe_allow_html=True)

if not sheet:
    st.warning("⚠️ חיבור לענן חסר (credentials.json לא נמצא או לא תקין). הנתונים נשמרים זמנית בלבד.")

tab_runners, tab_admin = st.tabs(["📱 אזור הרצים", "📊 דשבורד מנהל"])

# ==========================================
# 📱 לשונית 1: ממשק הרצים (מותאם למובייל)
# ==========================================
with tab_runners:
    st.subheader("⏱️ רישום אישי")
    
    default_index = RUNNERS_LIST.index(suggested_runner) if suggested_runner in RUNNERS_LIST else 0
    current_runner = st.selectbox("אנא בחר את שמך מהרשימה:", ["בחר שם..."] + RUNNERS_LIST, index=default_index + (1 if default_index or suggested_runner in RUNNERS_LIST else 0))

    if current_runner != "בחר שם...":
        if current_runner not in st.session_state.runners_db:
            st.session_state.runners_db[current_runner] = {
                "start": None, "laps": [], "end": None, "duration": None
            }
        
        runner_data = st.session_state.runners_db[current_runner]
        
        # --- מנגנון אימות מיקום בזמן אמת ---
        location_allowed = False
        with st.expander("📍 בדיקת נוכחות במסלול (חובה)", expanded=True):
            st.write("המערכת דורשת אימות מיקום כדי לוודא הגעה למתחם.")
            
            # שימוש בשם הרץ ובגרסת המיקום הנוכחית כמפתח יציב למניעת לולאה אינסופית
            runner_safe_key = current_runner.replace(" ", "_")
            loc = streamlit_js_eval(data_of='geolocation', key=f"geo_static_{runner_safe_key}")
            
            if loc and isinstance(loc, dict) and 'coords' in loc:
                user_lat = loc['coords']['latitude']
                user_lon = loc['coords']['longitude']
                distance = calculate_distance(user_lat, user_lon, st.session_state.target_lat, st.session_state.target_lon)
                
                if distance <= st.session_state.max_distance:
                    st.success(f"✅ המיקום אומת! אתה נמצא במתחם (כ-{int(distance)} מטרים מהזינוק).")
                    location_allowed = True
                else:
                    st.error(f"❌ שגיאה: אתה רחוק מדי מהמסלול (כ-{int(distance/1000)} ק״מ מהזינוק). לא ניתן ללחוץ משם.")
            else:
                st.info("🔄 ממתין לקבלת נתוני GPS מהמכשיר... אנא ודא שאישרת גישת מיקום בדפדפן.")
        
        # תצוגת כפתורי הניהול האישיים
        if runner_data["start"] is None:
            st.info("🏃‍♂️ מוכן לזינוק? כפתור ההתחלה ייפתח ברגע שהמיקום יאומת.")
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
                        st.toast("✅ הנתונים גובו בהצלחה לענן!", icon="☁️")
                    except Exception as e:
                        st.error(f"שגיאת תקשורת מול גוגל: {e}")
                
                st.balloons()
                st.rerun()
                
        else:
            final_anim = str(runner_data['duration']).split('.')[0]
            st.markdown(f"<h3 style='color: #2ed573; text-align:center;'>כל הכבוד! סיימת בהצלחה! 🎉</h3>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align:center;'>זמן כולל: {final_anim}</h4>", unsafe_allow_html=True)
            if runner_data["laps"]:
                st.write("ריכוז זמני ההקפות שלך:", runner_data["laps"])

# ==========================================
# 📊 לשונית 2: דשבורד מנהל + הגדרות מובנות
# ==========================================
with tab_admin:
    st.subheader("🔒 ניהול ובקרה")
    admin_pass = st.text_input("סיסמת מנהל:", type="password")
    
    if admin_pass == "1234":
        
        # --- הגדרת נקודות הציון של המסלול ישירות מתוך הממשק ---
        st.markdown("---")
        st.markdown("### ⚙️ הגדרת מיקום המסלול (GPS)")
        
        col_lat, col_lon, col_rad = st.columns(3)
        with col_lat:
            new_lat = st.number_input("קו רוחב (Latitude):", value=st.session_state.target_lat, format="%.6f")
        with col_lon:
            new_lon = st.number_input("קו אורך (Longitude):", value=st.session_state.target_lon, format="%.6f")
        with col_rad:
            new_rad = st.number_input("רדיוס מותר (במטרים):", value=st.session_state.max_distance, step=10)
            
        if st.button("💾 שמור הגדרות מיקום חדשות"):
            st.session_state.target_lat = new_lat
            st.session_state.target_lon = new_lon
            st.session_state.max_distance = new_rad
            st.success("✅ נקודות הציון עודכנו בהצלחה במערכת!")
            st.rerun()
            
        st.markdown("---")
        
        # עיבוד הנתונים לטבלה מסודרת
        records = []
        for name, data in st.session_state.runners_db.items():
            if data["start"] is not None:
                records.append({
                    "שם הרץ": name,
                    "שעת התחלה": data["start"].strftime("%H:%M:%S"),
                    "שעת סיום": data["end"].strftime("%H:%M:%S") if data["end"] else "🏃‍♂️ רץ...",
                    "זמן נטו": str(data["duration"]).split('.')[0] if data["duration"] else "",
                    "מספר הקפות": len(data["laps"]),
                    "שניות נטו": data["duration"].total_seconds() if data["duration"] else None
                })
        
        if records:
            df = pd.DataFrame(records)
            total_started = len(df)
            total_finished = len(df[df["שעת סיום"] != "🏃‍♂️ רץ..."])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("רצו היום", total_started)
            c2.metric("סיימו בהצלחה", total_finished)
            c3.metric("עדיין במסלול", total_started - total_finished)
            
            st.markdown("### 🏆 טבלת מובילים (Leaderboard)")
            df_leaderboard = df.sort_values(by="שניות נטו", ascending=True).drop(columns=["שניות נטו"])
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
            
            # הצגת גרף מובנה ויציב שלא קורס
            df_finished = df[df["שניות נטו"].notna()]
            if not df_finished.empty:
                st.markdown("### 📈 התפלגות זמני סיום")
                chart_data = df_finished.set_index("שם הרץ")["שניות נטו"]
                st.bar_chart(chart_data)
        else:
            st.info("אין עדיין נתונים זמינים לאימון הנוכחי.")
            
        if st.button("🗑️ איפוס מערכת מלא (מקומי)"):
            st.session_state.runners_db = {}
            st.rerun()