import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Accurate Reporting", layout="wide")

st.title("Customer Account Statements")
st.markdown("---")

# دالة لتنظيف النصوص ومنع ظهور false
def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Opening Balance / Adjustment"
    # حذف أي حروف غير إنجليزية لمنع الخطأ في الـ PDF
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل وتجهيز البيانات (بدقة)
# -----------------------------
@st.cache_data 
def load_and_fix_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # 1. منع التكرار: حذف السطور التي لها نفس رقم القيد والمبلغ تماماً
    # هذا سيمنع تكرار الـ 157960.50 مرتين
    df = df.drop_duplicates(subset=['move_name', 'debit', 'credit'])
    
    # 2. تحويل التاريخ
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# دالة إصدار الـ PDF
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية البيانات لكل عميل وترتيبها زمنياً
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        
        # 3. إعادة حساب الرصيد التراكمي (Running Balance) بشكل صحيح
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # الهيدر
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
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
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
# واجهة المستخدم
# -----------------------------
try:
    df_clean = load_and_fix_data()
    partners = sorted(df_clean['partner_id'].unique().tolist())
    
    st.sidebar.header("Export Settings")
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Generate Final PDF"):
            pdf_out = generate_pdf(df_clean, selected_partners)
            st.sidebar.download_button(
                label="📥 Download PDF",
                data=bytes(pdf_out),
                file_name="Customer_Statements.pdf",
                mime="application/pdf"
            )
            st.success("PDF generated without duplicates!")

        for p in selected_partners:
            with st.expander(f"Preview: {p}"):
                p_df = df_clean[df_clean['partner_id'] == p].sort_values(by='date')
                # حساب الرصيد التراكمي للمعاينة
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("Please select a customer to see the cleaned data.")

except Exception as e:
    st.error(f"Error: {e}")
