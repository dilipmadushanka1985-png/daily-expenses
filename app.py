import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date
import hashlib
from io import BytesIO

# PDF සඳහා reportlab → requirements.txt එකට එකතු කරන්න: reportlab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("PDF download සඳහා reportlab library එක install කරගන්න (pip install reportlab)")

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
        st.error(f"Google Sheets සම්බන්ධතාවේ දෝෂයක්: {str(e)}")
        return None

# ────────────────────────────────────────────────
# LOGIN / LOGOUT
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
# MAIN APP
# ────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()
    st.stop()

st.set_page_config(page_title="Daily Tracker", layout="wide")
logout_button()
st.title("💰 දෛනික වියදම් ලේඛණය")
st.markdown(f"**සාදරයෙන් පිළිගන්නවා** — {st.session_state.user_name}")

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
    
    if 'මුදල' in df.columns:
        # Fixed cleaning for "Rs.840.00", "Rs.3,288.00" etc.
        df['මුදල'] = df['මුදල'].astype(str).str.replace(r'(Rs\.?|රු\.?|\s|,)', '', regex=True)
        df['මුදල'] = df['මුදල'].str.replace(r'\.+', '.', regex=True)
        df['මුදල'] = df['මුදල'].replace(['', '.'], '0')
        df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
    
    if 'දිනය' in df.columns:
        df['දිනය_converted'] = pd.to_datetime(df['දිනය'], errors='coerce', format='%Y-%m-%d')
    
    return df

df = load_data()

# Debug lines
#st.write("Debug: මුදල column dtype:", df['මුදල'].dtype if 'මුදල' in df.columns else "Column not found")
#if 'මුදල' in df.columns:
    #st.write("Debug: මුදල raw sample (sheet එකෙන්):", df['මුදල'].head(5).tolist())
    #st.write("Debug: මුදල cleaned sample:", df['මුදල'].head(5).tolist())
    #st.write("Debug: මුදල total sum:", df['මුදල'].sum())

# ────────────────────────────────────────────────
# ENTRY FORM
# ────────────────────────────────────────────────
st.markdown("---")
st.subheader("➕ නව ඇතුළත් කිරීමක්")
trans_type = st.radio("වර්ගය", ["වියදම්", "ආදායම්"], horizontal=True)

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        today = st.date_input("දිනය", date.today())
    with col2:
        user_name = st.session_state.user_name  # auto-filled

    if trans_type == "වියදම්":
        category = st.selectbox("කාණ්ඩය", [
            "ආහාර වියදම්", "ගමන් වියදම්", "බිල්පත් ගෙවීම්",
            "අත්‍යාවශ්‍ය ද්‍රව්‍ය", "වාහන නඩත්තු", "රෝහල් වියදම්", "වෙනත්"
        ])
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = st.selectbox("ගෙවූ ක්‍රමය", [
            "මුදලින් ගෙවීම්", "කාඩ්පත් ගෙවීම්", "අන්තර්ජාල ගෙවීම්"
        ])
        bill_no = st.text_input("බිල් අංකය")
        location = st.text_input("ස්ථානය")
    else:
        category = st.selectbox("ආදායම් වර්ගය", [
            "මාසික වැටුප", "සංයුක්ත දීමනාව", "ගෙවල් කුලිය", "වෙනත් ආදායම්"
        ])
        amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=100.0)
        payment_method = "බැංකුව / මුදල"
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
                    f"{amount:.2f}",  # Clean string without Rs. or commas
                    payment_method,
                    bill_no,
                    location,
                    remarks
                ]
                sheet.append_row(row)
                st.success(f"✅ {trans_type} ඇතුළත් කළා: රු. {amount:,.2f}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"දත්ත සේව් කිරීමේ දෝෂයක්: {e}")
    else:
        st.warning("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# ────────────────────────────────────────────────
# DATE RANGE FILTER & VIEW
# ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📅 Custom Date Range බලන්න")

col_start, col_end = st.columns(2)
with col_start:
    default_start = date.today().replace(day=1)
    start_date = st.date_input("ආරම්භය", value=default_start, min_value=date(2023,1,1), max_value=date.today())

with col_end:
    end_date = st.date_input("අවසානය", value=date.today(), min_value=start_date, max_value=date.today())

if not df.empty and 'දිනය_converted' in df.columns:
    filtered_df = df[
        (df['දිනය_converted'] >= pd.to_datetime(start_date)) &
        (df['දිනය_converted'] <= pd.to_datetime(end_date))
    ].copy()
else:
    filtered_df = pd.DataFrame()

st.write("Debug: Filtered rows:", len(filtered_df))

if not filtered_df.empty:
    income = filtered_df[filtered_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
    expense = filtered_df[filtered_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
    balance = income - expense

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 ආදායම", f"Rs. {income:,.2f}")
    c2.metric("💸 වියදම", f"Rs. {expense:,.2f}")
    c3.metric("💵 ඉතිරිය", f"Rs. {balance:,.2f}", delta_color="normal" if balance >= 0 else "inverse")

    # Pie Chart
    st.subheader("📊 වියදම් විග්‍රහය")
    expenses_only = filtered_df[filtered_df['වර්ගය'] == 'වියදම්']
    if not expenses_only.empty:
        pie_data = expenses_only.groupby('කාණ්ඩය')['මුදල'].sum().reset_index()
        fig = px.pie(pie_data, values='මුදල', names='කාණ්ඩය',
                     title=f'{start_date} සිට {end_date} දක්වා වියදම් breakdown', hole=0.5)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("තෝරාගත් කාලය තුළ වියදම් නැහැ.")

    # List View
    st.subheader("📝 ලැයිස්තුව")
    filtered_df['දිනය'] = filtered_df['දිනය_converted'].dt.strftime('%Y-%m-%d')
    filtered_df = filtered_df.sort_values('දිනය_converted', ascending=False)

    display_cols = ['දිනය', 'නම', 'වර්ගය', 'කාණ්ඩය', 'මුදල', 'ගෙවූ ක්‍රමය', 'සටහන්']
    final_cols = [c for c in display_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[final_cols].style.format({'මුදල': lambda x: f"Rs. {x:,.2f}" if x > 0 else "-"}),
        use_container_width=True,
        hide_index=True
    )

    # ────────────────────────────────────────────────
    # DOWNLOAD BUTTONS
    # ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("බාගත කරගන්න")

    # CSV
    csv_data = filtered_df[final_cols].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 CSV ලෙස බාගත කරන්න",
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
        elements.append(Paragraph(f"වියදම් වාර්තාව: {start_date} සිට {end_date} දක්වා", styles['Title']))
        elements.append(Paragraph(f"ආදායම: Rs. {income:,.2f} | වියදම: Rs. {expense:,.2f} | ඉතිරිය: Rs. {balance:,.2f}", styles['Normal']))

        table_data = [final_cols] + filtered_df[final_cols].astype(str).values.tolist()
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.green),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t)
        doc.build(elements)
        pdf_buffer.seek(0)

        st.download_button(
            label="📄 PDF ලෙස බාගත කරන්න",
            data=pdf_buffer,
            file_name=f"expenses_{start_date}_to_{end_date}.pdf",
            mime="application/pdf"
        )
else:
    st.info("තෝරාගත් කාල පරාසය තුළ දත්ත නැහැ හෝ sheet එක හිස් යි.")

st.markdown("---")
st.caption("App by Machan Dilip | Powered by Streamlit & Google Sheets")

