import streamlit as st
import pandas as pd
from datetime import date
import os

# App එකේ මාතෘකාව
st.set_page_config(page_title="Daily Expense Tracker", layout="centered")
st.title("💰 මගේ දෛනික වියදම්")

# දත්ත ගබඩා කරන file එක (Excel/CSV)
FILE_NAME = "expenses.csv"

# File එක නැත්නම් අලුතින් එකක් හදනවා
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=["දවස", "වර්ගය", "විස්තරය", "මුදල"])
    df.to_csv(FILE_NAME, index=False)

# වියදම් ඇතුළත් කරන කොටස
with st.form("expense_form", clear_on_submit=True):
    today = st.date_input("දිනය", date.today())
    category = st.selectbox("වර්ගය", ["ආහාර", "ගමන් වියදම්", "බිල්පත්", "අත්‍යවශ්‍ය ද්‍රව්‍ය", "වෙනත්"])
    desc = st.text_input("විස්තරය")
    amount = st.number_input("මුදල (Rs.)", min_value=0.0, step=10.0)
    
    submit = st.form_submit_state = st.form_submit_button("එකතු කරන්න")

if submit:
    if amount > 0:
        # අලුත් දත්ත පේළියක් සැකසීම
        new_data = pd.DataFrame([[today, category, desc, amount]], columns=["දවස", "වර්ගය", "විස්තරය", "මුදල"])
        # පරණ දත්ත වලට අලුත් ඒවා එකතු කිරීම
        new_data.to_csv(FILE_NAME, mode='a', header=False, index=False)
        st.success("වියදම සාර්ථකව ඇතුළත් කළා!")
    else:
        st.error("කරුණාකර මුදලක් ඇතුළත් කරන්න.")

# ඇතුළත් කළ වියදම් පෙන්වීම
st.subheader("📊 ඇතුළත් කළ දත්ත")
data = pd.read_csv(FILE_NAME)
st.dataframe(data.tail(10)) # අන්තිමට ඇතුළත් කළ 10 පෙන්වයි

# මුළු වියදම ගණනය කිරීම
total = data["මුදල"].sum()
st.info(f"මුළු වියදම: Rs. {total:,.2f}")