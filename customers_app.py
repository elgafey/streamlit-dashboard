import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Ar Suhul - Clean System", layout="wide")

# دالة تنظيف النصوص للـ PDF
def clean_text(text):
    t = str(text).strip()
    if not t or t.lower() in ['none', 'nan']: return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_clean_data():
    # الرابط المباشر للملف المنظف
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # تحويل التاريخ (قص منطقة GMT لضمان القراءة الصحيحة)
    df['date'] = df['date'].str.split(' GMT').str[0]
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # التأكد من نوع البيانات المالية
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    return df

# دالة توليد الـ PDF (الآن أسرع بفضل نظافة الملف)
def generate_pdf(df_all, selected_partners):
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
        # الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        for h, w in [("Date", 30), ("Move", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]:
            pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, row['date'].strftime('%Y-%m-%d'), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output(dest='S'))

# --- التشغيل الرئيسي ---
try:
    df = load_clean_data()
    
    # القائمة الجانبية
    st.sidebar.title("🔍 Search")
    if st.sidebar.button("🧹 Reset"): st.rerun()
    
    search = st.sidebar.text_input("Customer Name:", "")
    partners = sorted(df['partner_id'].unique().tolist())
    filtered = [p for p in partners if search.lower() in p.lower()]
    selected = st.sidebar.multiselect("Select:", options=filtered)

    # الداشبورد (مطابق تماماً لـ Odoo الآن)
    stats_df = df[df['partner_id'].isin(selected)] if selected else df
    t_deb, t_cre = stats_df['debit'].sum(), stats_df['credit'].sum()
    
    st.title("📂 Customer Ledger")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Debit", f"{t_deb:,.2f}")
    c2.metric("Total Credit", f"{t_cre:,.2f}")
    c3.metric("Net Balance", f"{(t_deb - t_cre):,.2f}")
    st.markdown("---")

    if selected:
        if st.sidebar.button("🛠️ Build PDF"):
            st.session_state['pdf'] = generate_pdf(df, selected)
        if 'pdf' in st.session_state:
            st.sidebar.download_button("📥 Download PDF", st.session_state['pdf'], "Report.pdf")

        for p in selected:
            with st.expander(f"View: {p}", expanded=True):
                p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                disp = p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].copy()
                disp['date'] = disp['date'].dt.strftime('%Y-%m-%d')
                st.table(disp)
except Exception as e:
    st.error(f"Error: {e}")
