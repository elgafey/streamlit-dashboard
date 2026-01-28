import streamlit as st
import pandas as pd
from fpdf import FPDF
import re
import io

st.set_page_config(page_title="Ar Suhul - Fixed PDF", layout="wide")

st.title("📊 Customer Account Statements")
st.markdown("---")

def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']: return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_and_fix_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    # تنظيف التاريخ من الصيغة الطويلة
    df['date'] = df['date'].str.split(' GMT').str[0] 
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    # حذف التكرار
    df = df.drop_duplicates(subset=['move_name', 'partner_id', 'debit', 'credit'])
    return df

def generate_pdf_bytes(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(0, 10, f"Final Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        # رأس الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            d_str = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, d_str, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- المنطق الرئيسي ---
try:
    df_clean = load_and_fix_data()
    all_partners = sorted(df_clean['partner_id'].unique().tolist())

    st.sidebar.header("🔍 Filter Menu")
    search_term = st.sidebar.text_input("Quick Search:", "")
    filtered_list = [p for p in all_partners if search_term.lower() in p.lower()]
    selected_partners = st.sidebar.multiselect("Select Customers:", options=filtered_list)

    if selected_partners:
        # 1. زر التوليد (Generate)
        if st.sidebar.button("🛠️ Prepare PDF"):
            # حفظ الـ PDF في السيرفر مؤقتاً
            st.session_state['pdf_data'] = generate_pdf_bytes(df_clean, selected_partners)
            st.session_state['pdf_ready'] = True

        # 2. زر التحميل (يظهر فقط لو الملف جاهز ويفضل ثابت)
        if st.session_state.get('pdf_ready'):
            st.sidebar.success("✅ PDF is Ready!")
            st.sidebar.download_button(
                label="📥 Click here to Save PDF",
                data=st.session_state['pdf_data'],
                file_name="Customer_Statements.pdf",
                mime="application/pdf",
                key='download_btn'
            )

        # عرض المعاينة
        for p in selected_partners:
            with st.expander(f"View Data: {p}", expanded=True):
                p_df = df_clean[df_clean['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                disp = p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].copy()
                disp['date'] = disp['date'].dt.strftime('%Y-%m-%d')
                st.table(disp)
    else:
        st.session_state['pdf_ready'] = False
        st.info("Please select a customer to start.")

except Exception as e:
    st.error(f"Error: {e}")
