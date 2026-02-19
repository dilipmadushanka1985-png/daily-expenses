import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date
import hashlib
from io import BytesIO

# For PDF download - add reportlab to requirements.txt
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("PDF download requires reportlab library (pip install reportlab)")

# ────────────────────────────────────────────────
# CONFIG & CONSTANTS
# ────────────────────────────────────────────────
SHEET_NAME = "My Daily Expenses"

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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.user_name = None

# ────────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
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
        st.error(f"Google Sheets connection error: {str(e)}")
        return None

# ────────────────────────────────────────────────
# LOGIN / LOGOUT
# ────────────────────────────────────────────────
def login_page():
    st.title("🔐 Login - Daily Expense Tracker")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username", placeholder="dileepa or nilupa")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if username in USERS:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                if input_hash == USERS[username]["password_hash"]:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.user_name = USERS[username]["display_name"]
                    st.success(f"Welcome, {st.session_state.user_name}!")
                    st.rerun()
                else:
                    st.error("Incorrect password!")
            else:
                st.error("User not found!")

def logout_button():
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("You have logged out!")
        st.rerun()

# ────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()
    st.stop()

st.set_page_config(page_title="Daily Tracker", layout="wide")
logout_button()
st.title("💰 Daily Expense Tracker")
st.markdown(f"**Welcome** — {st.session_state.user_name}")

# ────────────────────────────────────────────────
# DATA LOAD with CACHE
# ────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    sheet = connect_to_gsheet()
    if not sheet:
        return pd.DataFrame()
    all_data = sheet.get_all_values()
    if len(all_data) <= 1:
        return pd.DataFrame()
    
    headers = [h.strip() for h in all_data[0]]
    df = pd.DataFrame(all_data[1:], columns=headers)
    
    if 'Amount' in df.columns:
        df['Amount'] = df['Amount'].astype(str).str.replace(r'(Rs\.?|රු\.?|\s|,)', '', regex=True)
        df['Amount'] = df['Amount'].str.replace(r'\.+', '.', regex=True)
        df['Amount'] = df['Amount'].replace(['', '.'], '0')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    if 'Date' in df.columns:
        df['Date_converted'] = pd.to_datetime(df['Date'], errors='coerce', format='%Y-%m-%d')
    
    return df

df = load_data()

# ────────────────────────────────────────────────
# ENTRY FORM
# ────────────────────────────────────────────────
st.markdown("---")
st.subheader("➕ Add New Entry")
trans_type = st.radio("Type", ["Expense", "Income"], horizontal=True)

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        today = st.date_input("Date", date.today())
    with col2:
        user_name = st.session_state.user_name  # auto-filled

    if trans_type == "Expense":
        category = st.selectbox("Category", [
            "Food Expenses", "Transport", "Bills",
            "Essential Items", "Vehicle Maintenance", "Hospital Expenses", "Other"
        ])
        amount = st.number_input("Amount (Rs.)", min_value=0.0, step=100.0)
        payment_method = st.selectbox("Payment Method", [
            "Cash", "Card", "Online Transfer"
        ])
        bill_no = st.text_input("Bill Number")
        location = st.text_input("Location")
    else:
        category = st.selectbox("Income Type", [
            "Monthly Salary", "Allowance", "Rent Income", "Other Income"
        ])
        amount = st.number_input("Amount (Rs.)", min_value=0.0, step=100.0)
        payment_method = "Bank/Cash"
        bill_no = ""
        location = ""

    remarks = st.text_area("Remarks")
    submit = st.form_submit_button("Save")

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
                    f"{amount:.2f}",
                    payment_method,
                    bill_no,
                    location,
                    remarks
                ]
                sheet.append_row(row)
                st.success(f"✅ {trans_type} added: Rs. {amount:,.2f}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error saving data: {e}")
    else:
        st.warning("Please enter a valid amount.")

# ────────────────────────────────────────────────
# DATE RANGE FILTER & VIEW
# ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📅 Custom Date Range")

col_start, col_end = st.columns(2)
with col_start:
    default_start = date.today().replace(day=1)
    start_date = st.date_input("Start Date", value=default_start, min_value=date(2023,1,1), max_value=date.today())

with col_end:
    end_date = st.date_input("End Date", value=date.today(), min_value=start_date, max_value=date.today())

if not df.empty and 'Date_converted' in df.columns:
    filtered_df = df[
        (df['Date_converted'] >= pd.to_datetime(start_date)) &
        (df['Date_converted'] <= pd.to_datetime(end_date))
    ].copy()
else:
    filtered_df = pd.DataFrame()

st.write("Debug: Filtered rows:", len(filtered_df))

if not filtered_df.empty:
    income = filtered_df[filtered_df['Type'] == 'Income']['Amount'].sum()
    expense = filtered_df[filtered_df['Type'] == 'Expense']['Amount'].sum()
    balance = income - expense

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Income", f"Rs. {income:,.2f}")
    c2.metric("💸 Expense", f"Rs. {expense:,.2f}")
    c3.metric("💵 Balance", f"Rs. {balance:,.2f}", delta_color="normal" if balance >= 0 else "inverse")

    # Pie Chart
    st.subheader("📊 Expense Breakdown")
    expenses_only = filtered_df[filtered_df['Type'] == 'Expense']
    if not expenses_only.empty:
        pie_data = expenses_only.groupby('Category')['Amount'].sum().reset_index()
        fig = px.pie(pie_data, values='Amount', names='Category',
                     title=f'Expense Breakdown from {start_date} to {end_date}', hole=0.5)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expenses in the selected period.")

    # List View
    st.subheader("📝 Transaction List")
    filtered_df['Date'] = filtered_df['Date_converted'].dt.strftime('%Y-%m-%d')
    filtered_df = filtered_df.sort_values('Date_converted', ascending=False)

    display_cols = ['Date', 'Name', 'Type', 'Category', 'Amount', 'Payment Method', 'Remarks']
    final_cols = [c for c in display_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[final_cols].style.format({'Amount': lambda x: f"Rs. {x:,.2f}" if x > 0 else "-"}),
        use_container_width=True,
        hide_index=True
    )

    # ────────────────────────────────────────────────
    # DOWNLOAD BUTTONS
    # ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Download Data")

    # CSV
    csv_data = filtered_df[final_cols].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Download as CSV",
        data=csv_data,
        file_name=f"expenses_{start_date}_to_{end_date}.csv",
        mime="text/csv"
    )

    # PDF
    if PDF_AVAILABLE and not filtered_df.empty:
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Expense Report: {start_date} to {end_date}", styles['Title']))
        elements.append(Paragraph(f"Income: Rs. {income:,.2f} | Expense: Rs. {expense:,.2f} | Balance: Rs. {balance:,.2f}", styles['Normal']))

        # Table headers and data in English
        table_data = [final_cols] + filtered_df[final_cols].astype(str).values.tolist()
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.green),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t)
        doc.build(elements)
        pdf_buffer.seek(0)

        st.download_button(
            label="📄 Download as PDF",
            data=pdf_buffer,
            file_name=f"expenses_{start_date}_to_{end_date}.pdf",
            mime="application/pdf"
        )
else:
    st.info("No data in the selected date range or sheet is empty.")

st.markdown("---")
st.caption("App by Dilip | Powered by Streamlit & Google Sheets")
