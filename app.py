import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- සැකසුම් ---
SHEET_NAME = "My Daily Expenses"

# --- Google Sheets සම්බන්ධ කිරීම ---
def connect_to_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        st.error(f"Google Sheet සම්බන්ධතා දෝෂයක්: {e}")
        return None

# --- App Layout ---
st.set_page_config(page_title="Daily Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්")

# --- Input Form ---
trans_type = st.radio("ගනුදෙනු වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

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
        sheet = connect_to_gsheet()
        if sheet:
            try:
                row = [str(today), user_name, trans_type, category, amount, payment_method, bill_no, location, remarks]
                sheet.append_row(row)
                st.success(f"✅ {trans_type} ඇතුළත් කළා: රු. {amount}")
            except Exception as e:
                st.error(f"දත්ත යැවීමේ දෝෂයක්: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# --- 📊 MONTHLY SUMMARY & CHARTS ---
st.markdown("---")
st.subheader("📅 මාසික සාරාංශය")

sheet = connect_to_gsheet()
if sheet:
    try:
        data = sheet.get_all_records()
        
        if len(data) > 0:
            df = pd.DataFrame(data)
            
            # 1. Headers සුද්ද කිරීම
            df.columns = df.columns.str.strip()

            # 2. 'මුදල' තීරුව සුද්ද කිරීම
            if 'මුදල' in df.columns:
                df['මුදල'] = df['මුදල'].astype(str).str.replace(r'[^\d.]', '', regex=True)
                df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
            
            # 3. දිනය Filter කිරීම
            if 'දිනය' in df.columns:
                df['දිනය'] = pd.to_datetime(df['දිනය'], errors='coerce')
                
                current_month = date.today().month
                current_year = date.today().year
                
                this_month_df = df[
                    (df['දිනය'].dt.month == current_month) & 
                    (df['දිනය'].dt.year == current_year)
                ]
                
                if not this_month_df.empty:
                    # Metrics Calculation
                    income = this_month_df[this_month_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                    expense = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                    balance = income - expense
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("💰 ආදායම", f"Rs. {income:,.2f}")
                    c2.metric("💸 වියදම", f"Rs. {expense:,.2f}")
                    c3.metric("💵 ඉතිරිය", f"Rs. {balance:,.2f}")
                    
                    # --- CHART SECTION (Updated) ---
                    st.write("---")
                    st.subheader("📊 වියදම් විග්‍රහය")
                    
                    expenses_only = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']
                    
                    if not expenses_only.empty:
                        # කාණ්ඩ අනුව එකතු කිරීම (Group By)
                        pie_data = expenses_only.groupby('කාණ්ඩය')['මුදල'].sum().reset_index()

                        # Pie Chart
                        fig = px.pie(pie_data, values='මුදල', names='කාණ්ඩය', 
                                     title='මේ මාසයේ වියදම් වර්ගීකරණය',
                                     hole=0.5)
                        
                        # ප්‍රතිශතය සහ නම චාට් එක ඇතුළේ පෙන්වීම
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ප්‍රස්තාරය පෙන්වීමට තරම් වියදම් දත්ත නැත.")
                        
                else:
                    st.info("මේ මාසය සඳහා දත්ත තවම නැත.")
            else:
                st.error("Error: 'දිනය' Column එක හමුවුනේ නැත.")
        else:
            st.info("Sheet එකේ දත්ත කිසිවක් නැත.")

    except Exception as e:
        st.error(f"Error loading summary: {e}")
