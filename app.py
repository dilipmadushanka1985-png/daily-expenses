import streamlit as st
import gspread
import pandas as pd
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

# --- App Layout ---
st.set_page_config(page_title="Daily Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්")

# --- Transaction Type ---
trans_type = st.radio("ගනුදෙනු වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

# --- Entry Form ---
with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        today = st.date_input("දිනය", date.today())
    with col2:
        user_name = st.selectbox("නම", ["Mr. Dileepa", "Mrs. Nilupa"])

    if trans_type == "වියදම්":
        category = st.selectbox("කාණ්ඩය", ["ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්", "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "වෙනත්"])
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = st.selectbox("ගෙවූ ක්‍රමය", ["Cash", "Card", "Online Transfer"])
        bill_no = st.text_input("බිල් අංකය")
        location = st.text_input("ස්ථානය")
    else:
        category = st.selectbox("ආදායම් වර්ගය", ["Salary", "Bata", "Rent Income", "Other"])
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = "Bank/Cash"
        bill_no = ""
        location = ""

    remarks = st.text_area("සටහන්")
    submit = st.form_submit_button("සේව් කරන්න")

if submit:
    if amount > 0:
        try:
            sheet = connect_to_gsheet()
            row = [str(today), user_name, trans_type, category, amount, payment_method, bill_no, location, remarks]
            sheet.append_row(row)
            st.success(f"✅ {trans_type} ඇතුළත් කළා: රු. {amount}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 📊 MONTHLY SUMMARY (Calculation Fix) ---
st.markdown("---")
st.subheader("📅 මාසික සාරාංශය")

try:
    sheet = connect_to_gsheet()
    data = sheet.get_all_records()
    
    if len(data) > 0:
        df = pd.DataFrame(data)
        
        # 1. Headers සුද්ද කිරීම (Spaces අයින් කිරීම)
        df.columns = df.columns.str.strip()
        
        # 2. 'මුදල' තීරුව ඉලක්කම් බවට හැරවීම (Rs. සහ , අයින් කිරීම)
        # මුදල තීරුව Text එකක් විදියට තිබුනොත් එය clean කරනවා
        if 'මුදල' in df.columns:
            df['මුදල'] = df['මුදල'].astype(str).str.replace('Rs.', '', regex=False).str.replace(',', '', regex=False)
            df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
        
        # 3. දිනය Filter කිරීම
        if 'දිනය' in df.columns:
            df['දිනය'] = pd.to_datetime(df['දිනය'], errors='coerce')
            
            current_month = date.today().month
            current_year = date.today().year
            
            # මේ මාසයේ දත්ත පමණක් තෝරා ගැනීම
            mask = (df['දිනය'].dt.month == current_month) & (df['දිනය'].dt.year == current_year)
            this_month_df = df[mask]
            
            # 4. එකතුව හැදීම
            if not this_month_df.empty:
                # 'වර්ගය' තීරුවේ නම හරියටම Sheet එකේ තියෙන විදියටම වෙන්න ඕනේ
                income = this_month_df[this_month_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                expense = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                balance = income - expense
                
                # පෙන්වීම
                c1, c2, c3 = st.columns(3)
                c1.metric("මුළු ආදායම", f"Rs. {income:,.2f}")
                c2.metric("මුළු වියදම", f"Rs. {expense:,.2f}")
                c3.metric("ඉතිරිය", f"Rs. {balance:,.2f}")
                
                with st.expander("මේ මාසයේ විස්තර"):
                    st.dataframe(this_month_df)
            else:
                st.info("මේ මාසය සඳහා දත්ත තවම නැත.")
        else:
            st.error("Sheet එකේ 'දිනය' කියලා Column එකක් සොයාගත නොහැක.")
            
        # --- Debugging Help ---
        # මෙය තියෙන්නේ මොකක් හරි අවුලක් ගියොත් බලාගන්න
        with st.expander("🛠️ තාක්ෂණික දෝෂ පරීක්ෂාව (Raw Data Check)"):
            st.write("Columns detected:", df.columns.tolist())
            st.write("First 5 rows:", df.head())
            
    else:
        st.info("Sheet එකේ දත්ත කිසිවක් නැත.")

except Exception as e:
    st.error(f"Calculation Error: {e}")
