import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Unified Statements", layout="wide")

st.title("Customer Account Statements")
st.markdown("---")

# دالة تنظيف النص لمنع أخطاء الـ PDF
def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل البيانات (الحل النهائي للتكرار)
# -----------------------------
@st.cache_data 
def load_fixed_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    # 1. قراءة الخام ومنع تحويل الفراغات لـ false
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # 2. تحويل أنواع البيانات لضمان دقة الفلترة
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # 3. الطلب اللي أنت قولته: "يبص على رقم الحركة والبارتنر"
    # السطر ده بيمسح أي تكرار لو رقم القيد والعميل هما هما
    df = df.drop_duplicates(subset=['move_name', 'partner_id'], keep='first')
    
    return df

# -----------------------------
# دالة إصدار الـ PDF
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية العميل وترتيبه
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        
        # حساب الرصيد التراكمي بعد الحذف
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Current Balance: {final_bal:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Move Name", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# الواجهة (Streamlit)
# -----------------------------
try:
    df_clean = load_fixed_data()
    partners = sorted(df_clean['partner_id'].unique().tolist())
    
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Download Correct PDF"):
            pdf_bytes = generate_pdf(df_clean, selected_partners)
            st.sidebar.download_button("📥 Save PDF", data=bytes(pdf_bytes), file_name="Corrected_Statement.pdf")

        for p in selected_partners:
            with st.expander(f"Preview: {p}", expanded=True):
                p_df = df_clean[df_clean['partner_id'] == p].copy()
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                # هنا لازم يظهر سطر واحد بس زي Odoo
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
except Exception as e:
    st.error(f"Error: {e}")
