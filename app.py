import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, timedelta

# --- සැකසුම් (Settings) ---
SHEET_NAME = "My Daily Expenses"

# --- Google Sheets සම්බන්ධ කිරීම ---
def connect_to_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Streamlit Secrets මගින් credentials ලබා ගැනීම
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        st.error(f"සම්බන්ධතා දෝෂයක්: {e}")
        return None

# --- Page Layout සැකසීම ---
st.set_page_config(page_title="BYD Daily Tracker", layout="wide", page_icon="📈")

# Header
st.markdown("<h1 style='text-align: center; color: #003366;'>💰 BYD දෛනික වියදම් කළමනාකරු</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- 1. දත්ත ඇතුළත් කිරීමේ පෝරමය (Data Entry) ---
with st.expander("➕ අලුත් ගනුදෙනුවක් ඇතුළත් කරන්න (මෙතැන ඔබන්න)", expanded=False):
    trans_type = st.radio("ගනුදෙනු වර්ගය:", ["වියදම්", "ආදායම්"], horizontal=True)
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            entry_date = st.date_input("දිනය", date.today())
        with c2:
            user = st.selectbox("නම", ["Mr. Dileepa", "Mrs. Nilupa"])
        with c3:
            # BYD Promotion සඳහා වෙනම කාණ්ඩයක් එකතු කර ඇත
            if trans_type == "වියදම්":
                cat = st.selectbox("කාණ්ඩය", ["ආහාර", "ගමන්", "බිල්පත්", "අත්‍යාවශ්‍ය", "වාහන", "රෝහල්", "BYD Promotion", "වෙනත්"])
            else:
                cat = st.selectbox("ආදායම් වර්ගය", ["Salary", "Bata", "Rent", "Other"])

        c4, c5 = st.columns(2)
        with c4:
            amt = st.number_input("මුදල (රු.)", min_value=0.0, step=100.0)
        with c5:
            pay_method = st.selectbox("ක්‍රමය", ["Cash", "Card", "Online"])

        rem = st.text_area("අමතර සටහන්")
        
        submit_btn = st.form_submit_button("සේව් කරන්න")

        if submit_btn and amt > 0:
            sheet = connect_to_gsheet()
            if sheet:
                try:
                    # Google Sheet එකේ Headers: දිනය, නම, වර්ගය, කාණ්ඩය, මුදල, ගෙවූ ක්‍රමය, සටහන්
                    row = [str(entry_date), user, trans_type, cat, amt, pay_method, rem]
                    sheet.append_row(row)
                    st.success(f"✅ {trans_type} ඇතුළත් කළා: රු. {amt}")
                    # දත්ත යැවූ පසු පිටුව refresh වේ
                    st.rerun()
                except Exception as e:
                    st.error(f"දත්ත යැවීමේ දෝෂයක්: {e}")

# --- 2. වාර්තා සහ සාරාංශය (Dashboard) ---
st.subheader("📊 වාර්තා සහ විග්‍රහය")

sheet = connect_to_gsheet()
if sheet:
    # සියලු දත්ත ලබා ගැනීම
    data = sheet.get_all_records()
    
    if data:
        df = pd.DataFrame(data)
        
        # දත්ත පිරිසිදු කිරීම (Data Cleaning)
        # මුදල තීරුව අංක බවට පත් කිරීම
        if 'මුදල' in df.columns:
            df['මුදල'] = pd.to_numeric(df['මුදල'], errors='coerce').fillna(0)
        
        # දිනය තීරුව Date Format එකට හැරවීම
        if 'දිනය' in df.columns:
            df['දිනය'] = pd.to_datetime(df['දිනය'], errors='coerce')

            # --- Date Range Filter (දින පරාසය තේරීම) ---
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                # Default: මේ මාසයේ මුල සිට
                default_start = date(date.today().year, date.today().month, 1)
                start_date = st.date_input("ආරම්භක දිනය", default_start)
            with col_date2:
                # Default: අද දිනය දක්වා
                end_date = st.date_input("අවසාන දිනය", date.today())

            # දින පරාසයට අදාළ දත්ත පමණක් වෙන් කර ගැනීම
            mask = (df['දිනය'].dt.date >= start_date) & (df['දිනය'].dt.date <= end_date)
            filtered_df = df.loc[mask]

            if not filtered_df.empty:
                # Metrics ගණනය කිරීම
                inc = filtered_df[filtered_df['වර්ගය'] == 'ආදායම්']['මුදල'].sum()
                exp = filtered_df[filtered_df['වර්ගය'] == 'වියදම්']['මුදල'].sum()
                bal = inc - exp

                # කාඩ්පත් (Metrics) පෙන්වීම
                m1, m2, m3 = st.columns(3)
                m1.metric("මුළු ආදායම (Income)", f"රු. {inc:,.2f}")
                m2.metric("මුළු වියදම (Expense)", f"රු. {exp:,.2f}", delta=f"-{exp:,.2f}", delta_color="inverse")
                m3.metric("ඉතිරිය (Balance)", f"රු. {bal:,.2f}")

                st.markdown("---")

                # --- කොටස් දෙකකට බෙදීම (ප්‍රස්ථාරය සහ ලිස්ට් එක) ---
                chart_col, list_col = st.columns([1, 2])

                # 1. පයි ප්‍රස්ථාරය (Pie Chart)
                with chart_col:
                    st.write("##### 📉 වියදම් බෙදී ගිය ආකාරය")
                    expenses_only = filtered_df[filtered_df['වර්ගය'] == 'වියදම්']
                    
                    if not expenses_only.empty:
                        fig = px.pie(expenses_only, values='මුදල', names='කාණ්ඩය', hole=0.4)
                        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("තෝරාගත් කාලය තුළ වියදම් නැත.")

                # 2. වර්ණ ගැන්වූ දත්ත ලැයිස්තුව (Colored Data Table)
                with list_col:
                    st.write("##### 📝 ගනුදෙනු ලැයිස්තුව")
                    
                    # වර්ණ ගැන්වීමේ Function එක
                    def color_rows(row):
                        if row['වර්ගය'] == 'ආදායම්':
                            # ආදායම් -> නිල් පාට (Blue)
                            return ['color: blue; font-weight: bold'] * len(row)
                        elif row['වර්ගය'] == 'වියදම්':
                            # වියදම් -> රතු පාට (Red)
                            return ['color: red'] * len(row)
                        else:
                            return ['color: black'] * len(row)

                    # දින පරාසයට අදාළ දත්ත Sort කිරීම (අලුත් දේවල් උඩින්)
                    display_df = filtered_df.sort_values(by='දිනය', ascending=False).copy()
                    # දිනය පෙන්වන Format එක වෙනස් කිරීම (YYYY-MM-DD)
                    display_df['දිනය'] = display_df['දිනය'].dt.strftime('%Y-%m-%d')
                    
                    # පෙන්විය යුතු තීරු පමණක් තෝරා ගැනීම
                    final_cols = ['දිනය', 'නම', 'වර්ගය', 'කාණ්ඩය', 'මුදල', 'සටහන්']
                    # තීරු තිබේ දැයි පරීක්ෂා කර පෙන්වීම
                    cols_to_use = [c for c in final_cols if c in display_df.columns]
                    
                    # වර්ණ යෙදීම (Pandas Styler)
                    styled_df = display_df[cols_to_use].style.apply(color_rows, axis=1)
                    
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)

            else:
                st.warning(f"{start_date} සිට {end_date} දක්වා දත්ත කිසිවක් හමු නොවුණි.")
        else:
            st.error("Sheet එකේ 'දිනය' හෝ 'මුදල' තීරු සොයාගත නොහැක. කරුණාකර Headers පරීක්ෂා කරන්න.")
    else:
        st.info("Sheet එකේ දත්ත කිසිවක් නැත.")
