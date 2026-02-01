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
        st.error(f"සම්බන්ධතා දෝෂයක්: {e}")
        return None

# --- App Layout ---
st.set_page_config(page_title="Daily Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්")

# --- Form Section ---
trans_type = st.radio("වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

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
                st.error(f"Error: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# --- 📊 MONTHLY SUMMARY & LIST ---
st.markdown("---")
st.subheader("📅 මාසික සාරාංශය")

sheet = connect_to_gsheet()
if sheet:
    try:
        all_data = sheet.get_all_values()
        
        if len(all_data) > 1:
            headers = all_data[0]
            rows = all_data[1:]
            df = pd.DataFrame(rows, columns=headers)
            
            # --- Cleaning & Formatting ---
            df.columns = df.columns.str.strip() # Remove extra spaces from headers

            if 'මුදල' in df.columns:
                # Rs. and commas cleaning
                df['මුදල'] = df['මුදල'].astype(str).str.replace(r'Rs\.?', '', regex=True)
                df['මුදල'] = df['මුදල'].str.replace(',', '', regex=False)
                df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
            
            if 'දිනය' in df.columns:
                df['දිනය_converted'] = pd.to_datetime(df['දිනය'], errors='coerce')
                
                # Filter for current month
                current_month = date.today().month
                current_year = date.today().year
                
                this_month_df = df[
                    (df['දිනය_converted'].dt.month == current_month) & 
                    (df['දිනය_converted'].dt.year == current_year)
                ].copy() # Make a copy to avoid warnings
                
                if not this_month_df.empty:
                    # Metrics
                    income = this_month_df[this_month_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                    expense = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                    balance = income - expense
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("💰 ආදායම", f"Rs. {income:,.2f}")
                    c2.metric("💸 වියදම", f"Rs. {expense:,.2f}")
                    c3.metric("💵 ඉතිරිය", f"Rs. {balance:,.2f}")
                    
                    # --- CHART ---
                    st.write("---")
                    st.subheader("📊 වියදම් විග්‍රහය")
                    expenses_only = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']
                    
                    if not expenses_only.empty:
                        pie_data = expenses_only.groupby('කාණ්ඩය')['මුදල'].sum().reset_index()
                        fig = px.pie(pie_data, values='මුදල', names='කාණ්ඩය', title='වියදම් වෙන්වූ අයුරු', hole=0.5)
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ප්‍රස්තාරය පෙන්වීමට තරම් වියදම් දත්ත නැත.")

                    # --- LIST VIEW (අලුතින් එකතු කළ කොටස) ---
                    st.write("---")
                    st.subheader("📝 වියදම් ලැයිස්තුව")

                    # දිනය ලස්සනට පෙන්වීම (YYYY-MM-DD)
                    this_month_df['දිනය'] = this_month_df['දිනය_converted'].dt.strftime('%Y-%m-%d')
                    
                    # අලුත් දේවල් උඩින් පෙන්වන්න (Sort Descending)
                    this_month_df = this_month_df.sort_values(by='දිනය_converted', ascending=False)

                    # පෙන්විය යුතු Columns ටික තෝරා ගැනීම (අවශ්‍ය දේ පමණයි)
                    # මෙතන 'දිනය_converted' අයින් කරලා ලස්සන 'දිනය' තීරුව ගන්නවා
                    columns_to_show = ['දිනය', 'ඇතුළත් කළේ', 'වර්ගය', 'කාණ්ඩය', 'මුදල', 'ගෙවූ ක්‍රමය', 'සටහන්']
                    
                    # හරියටම තියෙන Columns ටික විතරක් පෙන්වන්න (Error නොවෙන්න)
                    final_cols = [c for c in columns_to_show if c in this_month_df.columns]
                    
                    st.dataframe(this_month_df[final_cols], use_container_width=True)

                else:
                    st.warning("මේ මාසය සඳහා දත්ත තවම හමු නොවුණි.")
            else:
                st.error("Error: 'දිනය' Column එක හමු නොවුණි.")
        else:
            st.info("Sheet එකේ දත්ත කිසිවක් නැත.")

    except Exception as e:
        st.error(f"Calculation Error: {e}")
