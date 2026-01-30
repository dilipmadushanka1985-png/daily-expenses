import streamlit as st
import gspread
import pandas as pd
import plotly.express as px  # අලුතින් එකතු කළ Chart Library එක
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

# --- 📊 MONTHLY SUMMARY & CHARTS ---
st.markdown("---")
st.subheader("📅 මාසික සාරාංශය")

try:
    sheet = connect_to_gsheet()
    data = sheet.get_all_records()
    
    if len(data) > 0:
        df = pd.DataFrame(data)
        
        # දත්ත පිරිසිදු කිරීම
        df.columns = df.columns.str.strip()
        if 'මුදල' in df.columns:
            df['මුදල'] = df['මුදල'].astype(str).str.replace('Rs.', '', regex=False).str.replace(',', '', regex=False)
            df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
        
        if 'දිනය' in df.columns:
            df['දිනය'] = pd.to_datetime(df['දිනය'], errors='coerce')
            
            # Filter current month
            current_month = date.today().month
            current_year = date.today().year
            mask = (df['දිනය'].dt.month == current_month) & (df['දිනය'].dt.year == current_year)
            this_month_df = df[mask]
            
            if not this_month_df.empty:
                # 1. Metrics පෙන්වීම
                income = this_month_df[this_month_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                expense = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                balance = income - expense
                
                c1, c2, c3 = st.columns(3)
                c1.metric("💰 මුළු ආදායම", f"Rs. {income:,.2f}")
                c2.metric("💸 මුළු වියදම", f"Rs. {expense:,.2f}", delta=f"-{expense:,.2f}", delta_color="inverse")
                c3.metric("💵 ඉතිරිය", f"Rs. {balance:,.2f}", delta="Balance")
                
                # --- 2. Charts Section (අලුත් කොටස) ---
                st.markdown("---")
                st.subheader("📊 වියදම් විග්‍රහය")
                
                # වියදම් පමණක් වෙන් කර ගැනීම
                expenses_only = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']
                
                if not expenses_only.empty:
                    # Pie Chart: වියදම් වර්ග අනුව බෙදී ගිය හැටි
                    fig = px.pie(expenses_only, values='මුදල', names='කාණ්ඩය', 
                                 title='මේ මාසයේ වියදම් වර්ගීකරණය',
                                 hole=0.4) # මැද හිඩැසක් ඇති Donut Chart එකක්
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("පෙන්වීමට තරම් වියදම් දත්ත තවම නැත.")

                # Data Table
                with st.expander("විස්තරාත්මක වගුව බලන්න"):
                    this_month_df['දිනය'] = this_month_df['දිනය'].dt.strftime('%Y-%m-%d')
                    st.dataframe(this_month_df)
            else:
                st.info("මේ මාසය සඳහා දත්ත තවම නැත.")
        else:
            st.error("Sheet එකේ 'දිනය' Column එක හමුවුනේ නැත.")
    else:
        st.info("Sheet එකේ දත්ත කිසිවක් නැත.")

except Exception as e:
    st.error(f"Error: {e}")
