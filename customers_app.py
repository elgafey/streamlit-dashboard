import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Unified Statements", layout="wide")

st.title("Customer Account Statements (By Move Name)")
st.markdown("---")

# دالة تنظيف النص للـ PDF
def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']:
        return "N/A"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل وتجهيز البيانات (فلترة برقم الحركة)
# -----------------------------
@st.cache_data 
def load_fixed_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    # قراءة البيانات مع منع تحويل الفراغات لـ False
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # تحويل التواريخ والأرقام
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # الحل الجذري: تجاهل أي تكرار بناءً على رقم الحركة فقط
    # لو move_name مكرر، هياخد أول سطر بس ويمسح الباقي
    df = df.drop_duplicates(subset=['move_name'], keep='first')
    
    return df

# -----------------------------
# إنشاء الـ PDF المجمع
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية العميل وترتيب حركاته
        cust_df = df_all[df_all['partner_id'] == partner].copy()
        cust_df = cust_df.sort_values(by='date')
        
        # حساب الرصيد التراكمي الصحيح بعد حذف التكرار
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # الهيدر
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Total Balance: {final_bal:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Move Name", 1, 0, 'C', True) # ركزنا هنا على رقم الحركة
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_text(row['move_name']), 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# واجهة المستخدم
# -----------------------------
try:
    df_clean = load_fixed_data()
    partners = sorted(df_clean['partner_id'].unique().tolist())
    
    st.sidebar.header("PDF Export Menu")
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Download Combined PDF"):
            pdf_out = generate_pdf(df_clean, selected_partners)
            st.sidebar.download_button(
                label="📥 Click to Download PDF",
                data=bytes(pdf_out),
                file_name="Customer_Statements.pdf",
                mime="application/pdf"
            )

        for p in selected_partners:
            with st.expander(f"Preview: {p}", expanded=True):
                p_df = df_clean[df_clean['partner_id'] == p].copy()
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                # عرض الجدول بالبيانات المنقحة
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
    else:
        st.info("Please select a customer to start.")

except Exception as e:
    st.error(f"Error: {e}")
