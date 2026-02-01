import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- සැකසුම් ---
SHEET_NAME = "My Daily Expenses"

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

st.set_page_config(page_title="BYD Daily Tracker", layout="wide")
st.markdown("<h1 style='text-align: center; color: #003366;'>💰 BYD දෛනික වියදම් කළමනාකරු</h1>", unsafe_allow_html=True)

# --- දත්ත ඇතුළත් කිරීම ---
with st.expander("➕ අලුත් ගනුදෙනුවක් ඇතුළත් කරන්න", expanded=False):
    trans_type = st.radio("වර්ගය:", ["වියදම්", "ආදායම්"], horizontal=True)
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1: entry_date = st.date_input("දිනය", date.today())
        with c2: user = st.selectbox("නම", ["Mr. Dileepa", "Mrs. Nilupa"])
        with c3:
            if trans_type == "වියදම්":
                cat = st.selectbox("කාණ්ඩය", ["ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්", "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "BYD Promotion", "වෙනත්"])
            else:
                cat = st.selectbox("ආදායම් වර්ගය", ["Salary", "Bata", "Rent Income", "Other"])
        
        amt = st.number_input("මුදල (රු.)", min_value=0.0)
        pay_method = st.selectbox("ක්‍රමය", ["Cash", "Card", "Online Transfer", "Bank/Cash"])
        location = st.text_input("ස්ථානය")
        rem = st.text_area("සටහන්")
        
        if st.form_submit_button("සේව් කරන්න") and amt > 0:
            sheet = connect_to_gsheet()
            if sheet:
                # ඔයාගේ Sheet එකේ headers වලට ගැලපෙන පිළිවෙල (B Column එක 'ඇතුළත් කළේ')
                row = [str(entry_date), user, trans_type, cat, f"Rs.{amt:.2f}", pay_method, "", location, rem]
                sheet.append_row(row)
                st.success("දත්ත සේව් කළා! ✅")
                st.rerun()

# --- වාර්තා සහ එකතුව ---
st.markdown("---")
sheet = connect_to_gsheet()
if sheet:
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        # 1. Column names පිරිසිදු කිරීම (Spaces අයින් කිරීම)
        df.columns = df.columns.str.strip()
        
        # 2. මුදල තීරුව පිරිසිදු කිරීම (Rs. කෑල්ල අයින් කර අංකයක් කිරීම)
        if 'මුදල' in df.columns:
            df['මුදල'] = df['මුදල'].astype(str).str.replace('Rs.', '', regex=False).str.replace(',', '', regex=False)
            df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
        
        # 3. දිනය හරියටම පිරිසිදු කිරීම
        if 'දිනය' in df.columns:
            df['දිනය'] = pd.to_datetime(df['දිනය']).dt.date 

            # --- Date Filter ---
            col1, col2 = st.columns(2)
            with col1: start_date = st.date_input("ආරම්භක දිනය", date(date.today().year, date.today().month, 1))
            with col2: end_date = st.date_input("අවසාන දිනය", date.today())

            # Filter Process
            mask = (df['දිනය'] >= start_date) & (df['දිනය'] <= end_date)
            filtered_df = df.loc[mask]

            if not filtered_df.empty:
                inc = filtered_df[filtered_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                exp = filtered_df[filtered_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("💰 මුළු ආදායම", f"Rs. {inc:,.2f}")
                m2.metric("💸 මුළු වියදම", f"Rs. {exp:,.2f}", delta=f"-{exp:,.2f}", delta_color="inverse")
                m3.metric("💵 ඉතිරිය", f"Rs. {inc-exp:,.2f}")

                # වර්ණ ගැන්වූ ලැයිස්තුව (Income -> Blue, Expense -> Red)
                def color_rows(row):
                    color = 'blue' if row['වර්ගය'] == 'ආදායම්' else 'red'
                    return [f'color: {color}; font-weight: bold'] * len(row)
                
                # පෙන්විය යුතු Columns ටික විතරක් තෝරමු
                display_cols = ['දිනය', 'ඇතුළත් කළේ', 'වර්ගය', 'කාණ්ඩය', 'මුදල', 'ස්ථානය', 'සටහන්']
                final_df = filtered_df[display_cols].sort_values('දිනය', ascending=False)
                
                st.dataframe(final_df.style.apply(color_rows, axis=1), use_container_width=True)
            else:
                st.warning("තෝරාගත් කාලය තුළ දත්ත නැත.")
