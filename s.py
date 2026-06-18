import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="בדיקת התחברות לגוגל", layout="centered")

st.markdown("### 🕵️‍♂️ מערכת רנטגן: בודק חיבור לגוגל אקסל... ⏳")
st.markdown("---")

try:
    # 1. האם יש סודות בכלל?
    if not st.secrets:
        st.error("❌ תקלה שלב 1: לא נמצאו סודות בכלל. התיבה של ה-Secrets ב-Streamlit ריקה.")
        st.stop()
        
    # 2. האם יש את גוגל ג'ייסון?
    if "google_json" in st.secrets:
        raw_creds = st.secrets["google_json"]
    else:
        raw_creds = st.secrets
        
    # 3. האם הפורמט תקין?
    if isinstance(raw_creds, str):
        try:
            creds_dict = json.loads(raw_creds)
        except Exception as e:
            st.error(f"❌ תקלה שלב 2: התיבה לא ריקה, אבל יש שגיאה בפורמט של הטקסט (ה-JSON שבור): {e}")
            st.stop()
    else:
        creds_dict = dict(raw_creds)

    # 4. התחברות לגוגל
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        st.success("✅ שלב 3 עבר: הבוט הצליח להתחבר לחשבון הגוגל שלו!")
    except Exception as e:
        st.error(f"❌ תקלה שלב 3: הסודות תקינים, אבל גוגל דוחה את ההתחברות: {e}")
        st.stop()
        
    # 5. מציאת האקסל
    try:
        sheet = client.open("RunningClub_DB")
        st.success("✅✅ שלב 4 עבר: הכל עובד מושלם! התחברנו בהצלחה לקובץ RunningClub_DB! אפשר להחזיר את האפליקציה.")
        st.balloons()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ תקלה שלב 4: התחברנו לגוגל בהצלחה, **אבל הבוט לא מוצא קובץ בשם 'RunningClub_DB'**.")
        st.warning("האם זכרת לשתף את קובץ האקסל עם כתובת האימייל של הבוט ונתת לו הרשאת עורך (Editor)?")
        st.info(f"כתובת האימייל שאיתה אתה חייב לשתף את האקסל היא:\n\n**{creds_dict.get('client_email', 'לא נמצא אימייל')}**")
    except Exception as e:
        st.error(f"❌ תקלה שלב 5: שגיאה לא צפויה מול הקובץ: {e}")

except Exception as e:
    st.error(f"שגיאת מערכת קריטית: {e}")
