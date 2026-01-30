import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- සැකසුම් ---
SHEET_NAME = "My Daily Expenses"

# --- Google Sheets සම්බන්ධ කිරීම ---
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# --- App එකේ පෙනුම ---
st.set_page_config(page_title="Daily Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්")

# --- 1. ගනුදෙනු වර්ගය තේරීම (Form එකෙන් පිටතට ගත්තා) ---
# මේක Form එකෙන් එළියට ගත්තේ, මෙය මාරු කරනකොටම යට Form එකේ Fields වෙනස් වෙන්න ඕනේ නිසා.
trans_type = st.radio("ඔයාට ඇතුළත් කරන්න ඕනේ මොකක්ද?", ["වියදම්", "ආදායම්"], horizontal=True)

# --- 2. Input Form එක ---
with st.form("entry_form", clear_on_submit=True):
    
    # දිනය (දෙකටම පොදුයි)
    today = st.date_input("දිනය", date.today())

    # --- කාණ්ඩය (Category) සැකසීම ---
    if trans_type == "වියදම්":
        # වියදම් සඳහා ලිස්ට් එක
        category_list = [
            "ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්", 
            "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "වෙනත්"
        ]
        category = st.selectbox("වියදම් කාණ්ඩය", category_list)
        
        # වියදම් වලට විතරක් අදාළ අමතර Fields
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = st.selectbox("ගෙවූ ක්‍රමය", ["Cash", "Card", "Online Transfer"])
        bill_no = st.text_input("බිල් අංකය (තිබේ නම්)")
        location = st.text_input("ස්ථානය/කඩේ නම")
        
    else:
        # ආදායම් සඳහා ඔයා ඉල්ලපු සරල ලිස්ට් එක (Minimum Inputs)
        category = st.selectbox("ආදායම් වර්ගය", ["Salary", "Bata", "Other"])
        
        amount = st.number_input("ලැබුණු මුදල (Rs.)", min_value=0.0, step=100.0)
        
        # ආදායම් වලට බිල් අංක/ස්ථාන ඕනේ නෑනේ. ඒ නිසා ඒවා හිස්ව තියනවා.
        # නමුත් Sheet එකේ Columns ගාණ සමාන වෙන්න ඕනේ නිසා අපි යවද්දී හිස් වචන යවනවා.
        payment_method = "Bank/Cash" # ආදායම් වලට මේක ඔටෝ දානවා (නැත්නම් dropdown එකක් දාන්නත් පුළුවන්)
        bill_no = ""
        location = ""

    # සටහන් (දෙකටම පොදුයි)
    remarks = st.text_area("Remarks/සටහන්")

    # Submit Button
    submit = st.form_submit_button("සේව් කරන්න")

# --- දත්ත යැවීම ---
if submit:
    if amount > 0:
        try:
            sheet = connect_to_gsheet()
            # අපි කොහොම හරි Sheet එකේ තීරු 8 ටම දත්ත යවන්න ඕනේ.
            # ආදායම් වලදී bill_no සහ location හිස්ව යයි.
            sheet.append_row([
                str(today), 
                trans_type, 
                category, 
                amount, 
                payment_method, 
                bill_no, 
                location, 
                remarks
            ])
            
            if trans_type == "ආදායම්":
                st.success(f"✅ {category} ආදායම (රු. {amount}) ඇතුළත් කළා!")
            else:
                st.success(f"📉 {category} වියදම (රු. {amount}) ඇතුළත් කළා!")
                
        except Exception as e:
            st.error(f"දෝෂයක් සිදුවිය: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")
