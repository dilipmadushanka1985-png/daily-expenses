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

# --- 1. ගනුදෙනු වර්ගය (Form එකෙන් පිටත) ---
trans_type = st.radio("ඔයාට ඇතුළත් කරන්න ඕනේ මොකක්ද?", ["වියදම්", "ආදායම්"], horizontal=True)

# --- 2. Input Form එක ---
with st.form("entry_form", clear_on_submit=True):
    
    col1, col2 = st.columns(2)
    
    with col1:
        # දිනය
        today = st.date_input("දිනය", date.today())
    
    with col2:
        # කවුද දත්ත දාන්නේ? (New Feature)
        user_name = st.selectbox("නම (කවුද ඇතුළත් කරන්නේ?)", ["Mr. Dileepa", "Mrs. Nilupa"])

    # --- කාණ්ඩය (Category) සැකසීම ---
    if trans_type == "වියදම්":
        category_list = [
            "ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්", 
            "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "වෙනත්"
        ]
        category = st.selectbox("වියදම් කාණ්ඩය", category_list)
        
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = st.selectbox("ගෙවූ ක්‍රමය", ["Cash", "Card", "Online Transfer"])
        bill_no = st.text_input("බිල් අංකය (තිබේ නම්)")
        location = st.text_input("ස්ථානය/කඩේ නම")
        
    else:
        # ආදායම් ලිස්ට් එක (Rent Income එකතු කළා)
        category = st.selectbox("ආදායම් වර්ගය", ["Salary", "Bata", "Rent Income", "Other"])
        
        amount = st.number_input("ලැබුණු මුදල (Rs.)", min_value=0.0, step=100.0)
        
        # ආදායම් වලට අනවශ්‍ය දේවල් ඔටෝ පිරවීම
        payment_method = "Bank/Cash"
        bill_no = ""
        location = ""

    # සටහන්
    remarks = st.text_area("Remarks/සටහන්")

    # Submit Button
    submit = st.form_submit_button("සේව් කරන්න")

# --- දත්ත යැවීම ---
# --- දත්ත යැවීම ---
if submit:
    if amount > 0:
        try:
            sheet = connect_to_gsheet()
            
            # 1. දත්ත ඇතුළත් කිරීම (අන්තිම පේළියට)
            sheet.append_row([
                str(today), 
                user_name, 
                trans_type, 
                category, 
                amount, 
                payment_method, 
                bill_no, 
                location, 
                remarks
            ])
            
            # 2. දිනය අනුව පිළිවෙළට හැදීම (Auto Sort)
            # A2 ඉඳන් I1000 දක්වා ප්‍රදේශය, පළමු තීරුව (දිනය) අනුව Sort කරන්න කියනවා.
            # headers (පළමු පේළිය) අතාරින්න ඕනේ නිසා අපි range එක 'A2:I1000' කියලා දෙනවා.
            sheet.sort((1, 'asc'), range='A2:I1000') 

            if trans_type == "ආදායම්":
                st.success(f"✅ {user_name} විසින් {category} ආදායම (රු. {amount:.2f}) ඇතුළත් කළා!")
            else:
                st.success(f"📉 {user_name} විසින් {category} වියදම (රු. {amount:.2f}) ඇතුළත් කළා!")
                
        except Exception as e:
            st.error(f"දෝෂයක් සිදුවිය: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

