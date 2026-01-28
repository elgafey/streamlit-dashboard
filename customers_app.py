import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Accurate Statements", layout="wide")

st.title("Customer Account Statements")
st.markdown("---")

# دالة لتنظيف النصوص ومنع ظهور أي قيم وهمية مثل false
def clean_text(text):
    t = str(text).strip()
    # إذا كانت القيمة فارغة أو 'false' نحولها لنص فارغ تماماً
    if t.lower() in ['false', 'none', 'nan', '0', '']:
        return ""
    # حذف أي حروف غير إنجليزية لمنع الخطأ في الـ PDF
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل البيانات الأصلية فقط
# -----------------------------
@st.cache_data 
def load_pure_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    # قراءة الملف مع التأكد من عدم تحويل القيم الفارغة لـ 'false'
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # تحويل التاريخ للتنسيق الصحيح
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df

# -----------------------------
# دالة إصدار الـ PDF
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية البيانات للعميل المختار فقط كما هي في الملف
        cust_df = df_all[df_all['partner_id'] == partner].copy()
        cust_df = cust_df.sort_values(by='date')
        
        # حساب الرصيد التراكمي بناءً على السطور الموجودة فعلياً
        cust_df['Running_Balance'] = (pd.to_numeric(cust_df['debit']) - pd.to_numeric(cust_df['credit'])).cumsum()
        
        pdf.add_page()
        
        # الهيدر
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Final Balance: {final_bal:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{float(row['debit']):,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{float(row['credit']):,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{float(row['Running_Balance']):,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# الواجهة الرئيسية
# -----------------------------
try:
    df_final = load_pure_data()
    partners = sorted(df_final['partner_id'].unique().tolist())
    
    st.sidebar.header("Export Menu")
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Download Final PDF"):
            pdf_out = generate_pdf(df_final, selected_partners)
            st.sidebar.download_button(
                label="📥 Click to Download",
                data=bytes(pdf_out),
                file_name="Clean_Statement.pdf",
                mime="application/pdf"
            )

        for p in selected_partners:
            with st.expander(f"Data Preview: {p}", expanded=True):
                p_df = df_final[df_final['partner_id'] == p].copy()
                p_df['Running_Balance'] = (pd.to_numeric(p_df['debit']) - pd.to_numeric(p_df['credit'])).cumsum()
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
    else:
        st.info("Select a customer from the sidebar to view their actual data.")

except Exception as e:
    st.error(f"Error: {e}")
