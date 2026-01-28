import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Professional Ledger", layout="wide")

st.title("Customer Account Statements")
st.markdown("---")

# دالة تنظيف النص لمنع أخطاء الـ PDF واستبدال القيم الفارغة
def clean_text(text):
    t = str(text).strip()
    # إذا كانت القيمة ناتجة عن خلل في القراءة (فراغ أو False) نضع وصفاً افتراضياً
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Journal Entry"
    # حذف أي حروف غير إنجليزية لضمان عمل مكتبة FPDF
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل وتجهيز البيانات (بدون تكرار وهمي)
# -----------------------------
@st.cache_data 
def load_and_clean_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    
    # السر هنا: na_filter=False يمنع بايثون من تحويل الفراغات في الملف إلى كلمة false
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # تحويل التواريخ وتنسيق الأرقام لضمان دقة الحسابات
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # حذف أي صفوف مكررة تماماً قد تكون موجودة في قاعدة البيانات
    df = df.drop_duplicates()
    
    return df

# -----------------------------
# دالة إصدار الـ PDF المجمع
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية البيانات للعميل المختار وترتيبها زمنياً
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        
        # حساب الرصيد التراكمي بناءً على السطور الحقيقية فقط
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # ترويسة الصفحة
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Final Balance: {final_bal:,.2f} EGP", ln=True, align='C')
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
# واجهة المستخدم (Streamlit UI)
# -----------------------------
try:
    df_main = load_and_clean_data()
    partners = sorted(df_main['partner_id'].unique().tolist())
    
    selected_partners = st.sidebar.multiselect("Select Customers for Statement", options=partners)

    if selected_partners:
        if st.sidebar.button("Generate Final PDF"):
            pdf_bytes = generate_pdf(df_main, selected_partners)
            st.sidebar.download_button(
                label="📥 Download PDF",
                data=bytes(pdf_bytes),
                file_name="Customer_Statements.pdf",
                mime="application/pdf"
            )
            st.success("PDF ready for download!")

        # المعاينة على الشاشة للتأكد من عدم وجود تكرار
        for p in selected_partners:
            with st.expander(f"Data Preview: {p}", expanded=True):
                p_df = df_main[df_main['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
    else:
        st.info("Please select a customer from the sidebar to display their statement.")

except Exception as e:
    st.error(f"Error Loading Application: {e}")
