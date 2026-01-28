import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- සැකසුම් ---
SHEET_NAME = "My Daily Expenses"  # ඔයා Google Sheet එකට දුන් නම මෙතනට දාන්න

# --- Google Sheets සම්බන්ධ කිරීම ---
def connect_to_gsheet():
    # Streamlit Secrets වලින් Key එක ලබාගැනීම
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"]) # අපි පහල පියවරේදී මේක හදනවා
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# --- App එකේ පෙනුම ---
st.set_page_config(page_title="Daily Expense Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම් (Google Sheets)")

# වියදම් ඇතුළත් කරන කොටස
with st.form("expense_form", clear_on_submit=True):
    today = st.date_input("දිනය", date.today())
    category = st.selectbox("වර්ගය", ["ආහාර", "ගමන් වියදම්", "බිල්පත්", "අත්‍යවශ්‍ය ද්‍රව්‍ය", "වෙනත්"])
    desc = st.text_input("විස්තරය")
    amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=10.0)
    
    submit = st.form_submit_button("එකතු කරන්න")

if submit:
    if amount > 0:
        try:
            sheet = connect_to_gsheet()
            # Google Sheet එකට දත්ත යැවීම
            sheet.append_row([str(today), category, desc, amount])
            st.success("✅ වියදම Google Sheet එකට සාර්ථකව ඇතුළත් කළා!")
        except Exception as e:
            st.error(f"දෝෂයක් සිදුවිය: {e}")
    else:
        st.error("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# Google Sheet එකේ ඇති දත්ත පෙන්වීම (අවශ්‍ය නම් පමණක්)
if st.checkbox("ඇතුළත් කළ දත්ත බලන්න"):
    try:
        sheet = connect_to_gsheet()
        data = sheet.get_all_records()
        st.dataframe(data)
    except:
        st.warning("දත්ත පෙන්වීමට නොහැක. Sheet එක හිස් විය හැක.")
