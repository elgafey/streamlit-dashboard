import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Full Ledger", layout="wide")

st.title("Customer Account Statements (Full Data)")
st.markdown("---")

# دالة تنظيف النص لمنع الخطأ في الـ PDF
def clean_text(text):
    t = str(text).strip()
    # استبدال القيم غير الواضحة بوصف مهني
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل البيانات (عرض كل السطور)
# -----------------------------
@st.cache_data 
def load_full_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    # قراءة البيانات مع منع تحويل الفراغات لـ False
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # تحويل التواريخ والأرقام لضمان دقة الحسابات
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # لن نستخدم drop_duplicates هنا لضمان عدم إخفاء أي عملة أو حركة
    return df

# -----------------------------
# إنشاء الـ PDF المجمع
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية العميل وترتيب حركاته حسب التاريخ
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        
        # حساب الرصيد التراكمي لكل الحركات المتاحة
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # الهيدر
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Statement Balance: {final_bal:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # رأس الجدول
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # محتوى الجدول
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# واجهة المستخدم
# -----------------------------
try:
    df_main = load_full_data()
    partners = sorted(df_main['partner_id'].unique().tolist())
    
    st.sidebar.header("PDF Export")
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Download PDF Statement"):
            pdf_bytes = generate_pdf(df_main, selected_partners)
            st.sidebar.download_button(
                label="📥 Save PDF File",
                data=bytes(pdf_bytes),
                file_name="Full_Ledger_Statements.pdf",
                mime="application/pdf"
            )

        for p in selected_partners:
            with st.expander(f"Full Ledger Preview: {p}", expanded=True):
                p_df = df_main[df_main['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                # استخدام st.dataframe لإظهار كل البيانات بدون حذف
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("Please select a customer to display their full transaction history.")

except Exception as e:
    st.error(f"Error: {e}")
