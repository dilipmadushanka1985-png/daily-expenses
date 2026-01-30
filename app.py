import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- සැකසුම් ---
SHEET_NAME = "My Daily Expenses"  # Google Sheet එකේ නම මෙතන තියෙන්න ඕනේ

# --- Google Sheets සම්බන්ධ කිරීම ---
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Secrets වලින් දත්ත ගැනීම
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# --- App එකේ පෙනුම ---
st.set_page_config(page_title="Daily Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්") # ඔයා ඉල්ලපු විදියට මාතෘකාව වෙනස් කළා

# --- Input Form එක ---
with st.form("entry_form", clear_on_submit=True):
    
    # 1. ආදායම් ද වියදම් ද යන්න තෝරා ගැනීම
    trans_type = st.radio("ගනුදෙනු වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

    # 2. දිනය
    today = st.date_input("දිනය", date.today())

    # 3. කාණ්ඩය (Category) - තෝරන වර්ගය අනුව ලිස්ට් එක වෙනස් වෙයි
    if trans_type == "වියදම්":
        category_list = [
            "ආහාර වියදම්", 
            "ගමන් වියදම්", 
            "බිල්පත් ගෙවීම්", 
            "අත්‍යාවශ්‍ය ද්‍රව්‍ය වියදම්", 
            "වාහන නඩත්තු වියදම්", 
            "රෝහල් වියදම්", 
            "වෙනත් වියදම්"
        ]
    else:
        # ආදායම් වර්ග (ඔයාට කැමති නම් මේවා වෙනස් කරන්න පුළුවන්)
        category_list = ["වැටුප්", "ව්‍යාපාර", "ලාභාංශ", "වෙනත් ආදායම්"]

    category = st.selectbox("කාණ්ඩය", category_list)

    # 4. අලුත් Input Fields
    amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
    payment_method = st.selectbox("ගෙවූ/ලැබුණු ක්‍රමය", ["Cash", "Card", "Online Transfer", "Cheque"])
    bill_no = st.text_input("බිල් අංකය (තිබේ නම්)")
    location = st.text_input("ස්ථානය/කඩේ නම")
    remarks = st.text_area("Remarks/සටහන්")

    # Submit Button
    submit = st.form_submit_button("දත්ත ඇතුළත් කරන්න")

# --- දත්ත යැවීම ---
if submit:
    if amount > 0:
        try:
            sheet = connect_to_gsheet()
            # Google Sheet එකේ තීරු 8 ට අදාළව දත්ත යැවීම
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
            
            # සාර්ථක පණිවිඩය (කොළ පාටින්)
            if trans_type == "ආදායම්":
                st.success(f"✅ රු. {amount} ක ආදායමක් සාර්ථකව ඇතුළත් කළා!")
            else:
                st.success(f"📉 රු. {amount} ක වියදමක් සාර්ථකව ඇතුළත් කළා!")
                
        except Exception as e:
            st.error(f"දෝෂයක් සිදුවිය: {e}")
    else:
        st.warning("කරුණාකර වලංගු මුදලක් ඇතුළත් කරන්න.")

# --- දත්ත පෙන්වීම (පහළ කොටස) ---
st.divider()
if st.checkbox("අන්තිමට ඇතුළත් කළ දත්ත පෙන්වන්න"):
    try:
        sheet = connect_to_gsheet()
        data = sheet.get_all_records()
        if data:
            st.dataframe(data[-5:]) # අන්තිම රෙකෝඩ් 5 විතරක් පෙන්වයි
        else:
            st.info("තවම දත්ත ඇතුළත් කර නැත.")
    except:
        st.warning("දත්ත පෙන්වීමේ දෝෂයක්. Sheet එකේ Headers නිවැරදිද බලන්න.")
