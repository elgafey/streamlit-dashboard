import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# دالة تنظيف النص من العربي وكلمة false
def clean_for_pdf(text):
    text_str = str(text).strip()
    # إذا كانت القيمة false أو فارغة، نضع وصف افتراضي
    if not text_str or text_str.lower() in ['false', 'none', 'nan']:
        return "Opening Balance / Adjustment"
    # إزالة أي حروف غير إنجليزية لمنع الـ Error
    return re.sub(r'[^\x00-\x7F]+', ' ', text_str).strip()

# -----------------------------
# تحميل وتجهيز البيانات
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # --- حل مشكلة التكرار ---
    # حذف الصفوف المتطابقة تماماً في التاريخ، رقم القيد، المدين، والدائن
    df = df.drop_duplicates(subset=['date', 'move_name', 'debit', 'credit'])
    
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# إنشاء الـ PDF
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية البيانات وترتيبها
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        
        # إعادة حساب الرصيد التراكمي بعد حذف التكرار
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # الهيدر
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 10, f"Statement: {clean_for_pdf(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 10, f"Current Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(5)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_for_pdf(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# --- واجهة المستخدم (Streamlit UI) ---
# ... (نفس كود الاختيار والتحميل السابق)
