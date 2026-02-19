import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date
import hashlib

# ────────────────────────────────────────────────
#  CONFIG & CONSTANTS
# ────────────────────────────────────────────────

SHEET_NAME = "My Daily Expenses"

# Simple user database (real app එකකට secrets.toml වලට move කරන්න)
USERS = {
    "dileepa": {
        "display_name": "Mr. Dileepa",
        "password_hash": hashlib.sha256("dileepa123".encode()).hexdigest()
    },
    "nilupa": {
        "display_name": "Mrs. Nilupa",
        "password_hash": hashlib.sha256("nilupa456".encode()).hexdigest()
    }
}

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.user_name = None

# ────────────────────────────────────────────────
#  GOOGLE SHEETS CONNECTION
# ────────────────────────────────────────────────

def connect_to_gsheet():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        st.error(f"Google Sheets සම්බන්ධතාවේ දෝෂයක්: {str(e)}")
        return None

# ────────────────────────────────────────────────
#  LOGIN / LOGOUT FUNCTIONS
# ────────────────────────────────────────────────

def login_page():
    st.title("🔐 ලොග් වෙන්න - දෛනික වියදම් ට්‍රැකර්")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("පරිශීලක නම", placeholder="dileepa හෝ nilupa")
        password = st.text_input("මුරපදය", type="password")
        
        if st.button("ලොග් වෙන්න", use_container_width=True):
            if username in USERS:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                if input_hash == USERS[username]["password_hash"]:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.user_name = USERS[username]["display_name"]
                    st.success(f"සාදරයෙන් පිළිගන්නවා, {st.session_state.user_name}!")
                    st.rerun()
                else:
                    st.error("මුරපදය වැරදියි!")
            else:
                st.error("මෙම පරිශීලක නම හමු නොවුණි!")

def logout_button():
    if st.sidebar.button("🚪 ලොග් ඉවත් වෙන්න"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("ඔබ ලොග් ඉවත් වුණා!")
        st.rerun()

# ────────────────────────────────────────────────
#  MAIN APP FLOW
# ────────────────────────────────────────────────

if not st.session_state.logged_in:
    login_page()
    st.stop()

# Logged-in users only from here
st.set_page_config(page_title="Daily Tracker", layout="centered")
logout_button()

st.title("💰 දෛනික වියදම් ලේඛණය")
st.markdown(f"**සාදරයෙන් පිළිගන්නවා** — {st.session_state.user_name}")

# ────────────────────────────────────────────────
#  ENTRY FORM
# ────────────────────────────────────────────────

trans_type = st.radio("වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        today = st.date_input("දිනය", date.today())
    with col2:
        user_name = st.session_state.user_name   # auto-filled — no selectbox needed

    if trans_type == "වියදම්":
        category = st.selectbox("කාණ්ඩය", [
            "ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්",
            "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "වෙනත්"
        ])
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
                row = [
                    str(today),
                    user_name,
                    trans_type,
                    category,
                    amount,
                    payment_method,
                    bill_no,
                    location,
                    remarks
                ]
                sheet.append_row(row)
                st.success(f"✅ {trans_type} ඇතුළත් කළා: රු. {amount:,.2f}")
            except Exception as e:
                st.error(f"දත්ත සේව් කිරීමේ දෝෂයක්: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# ────────────────────────────────────────────────
#  MONTHLY SUMMARY & LIST
# ────────────────────────────────────────────────

st.markdown("---")
st.subheader("📅 මාසික සාරාංශය")

sheet = connect_to_gsheet()
if sheet:
    try:
        all_data = sheet.get_all_values()
        
        if len(all_data) > 1:
            headers = [h.strip() for h in all_data[0]]
            df = pd.DataFrame(all_data[1:], columns=headers)

            # Amount cleaning
            if 'මුදල' in df.columns:
                df['මුදල'] = (
                    df['මුදල'].astype(str)
                    .str.replace(r'Rs\.?|රු\.?|\s|,', '', regex=True)
                    .str.replace(r'[^\d.]', '', regex=True)
                    .replace('', '0')
                )
                df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)

            if 'දිනය' in df.columns:
                df['දිනය_converted'] = pd.to_datetime(df['දිනය'], errors='coerce', dayfirst=True)

                current_month = date.today().month
                current_year = date.today().year

                this_month_df = df[
                    (df['දිනය_converted'].dt.month == current_month) &
                    (df['දිනය_converted'].dt.year == current_year)
                ].copy()

                if not this_month_df.empty:
                    income = this_month_df[this_month_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                    expense = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                    balance = income - expense

                    c1, c2, c3 = st.columns(3)
                    c1.metric("💰 ආදායම", f"Rs. {income:,.2f}")
                    c2.metric("💸 වියදම", f"Rs. {expense:,.2f}")
                    c3.metric("💵 ඉතිරිය", f"Rs. {balance:,.2f}")

                    # Pie chart
                    st.subheader("📊 වියදම් විග්‍රහය")
                    expenses_only = this_month_df[this_month_df['වර්ගය'] == 'වියදම්']
                    if not expenses_only.empty:
                        pie_data = expenses_only.groupby('කාණ්ඩය')['මුදල'].sum().reset_index()
                        fig = px.pie(pie_data, values='මුදල', names='කාණ්ඩය',
                                     title='වියදම් වෙන්වූ අයුරු', hole=0.5)
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("මේ මාසයේ වියදම් තවම ඇතුළත් කර නැහැ.")

                    # List view
                    st.subheader("📝 මාසික ලැයිස්තුව")
                    this_month_df['දිනය'] = this_month_df['දිනය_converted'].dt.strftime('%Y-%m-%d')
                    this_month_df = this_month_df.sort_values('දිනය_converted', ascending=False)

                    display_cols = ['දිනය', 'නම', 'වර්ගය', 'කාණ්ඩය', 'මුදල', 'ගෙවූ ක්‍රමය', 'සටහන්']
                    final_cols = [c for c in display_cols if c in this_month_df.columns]

                    def format_rs(x):
                        return f"Rs. {x:,.2f}" if x > 0 else "-"

                    st.dataframe(
                        this_month_df[final_cols].style.format({'මුදල': format_rs}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("මේ මාසය සඳහා දත්ත තවම නැහැ.")
            else:
                st.error("'දිනය' තීරුව හමු නොවුණි.")
        else:
            st.info("Sheet එකේ දත්ත තවම නැහැ.")
    except Exception as e:
        st.error(f"දත්ත ලබාගැනීමේ දෝෂයක්: {e}")
