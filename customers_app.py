import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Ar Suhul - Accurate Ledger", layout="wide")

st.title("👥 Customer Account Statements")
st.markdown("---")

def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل البيانات مع معالجة التاريخ
# -----------------------------
@st.cache_data 
def load_and_fix_all():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    
    # 1. منع تحويل الفراغات لـ False
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # 2. معالجة التاريخ بمرونة (عشان الـ NaT تختفي)
    # بنجرب كذا تنسيق عشان نضمن القراءة الصح
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    
    # 3. تحويل المبالغ
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # 4. حذف السطور المكررة فعلياً (لو نفس رقم القيد والعميل والمبلغ)
    df = df.drop_duplicates(subset=['move_name', 'partner_id', 'debit', 'credit'])
    
    return df

# -----------------------------
# إنشاء الـ PDF
# -----------------------------
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
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            # التأكد من عرض التاريخ بشكل صحيح في الـ PDF
            date_str = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, date_str, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return pdf.output()

# -----------------------------
# الواجهة
# -----------------------------
try:
    df_clean = load_and_fix_all()
    partners = sorted(df_clean['partner_id'].unique().tolist())
    
    st.sidebar.header("🔍 Filter Menu")
    search = st.sidebar.text_input("Search Customer:", "")
    filtered = [p for p in partners if search.lower() in p.lower()]
    
    selected = st.sidebar.multiselect("Select:", options=filtered)
    
    if selected:
        if st.sidebar.button("🚀 Print Statement"):
            pdf_bytes = generate_pdf(df_clean, selected)
            st.sidebar.download_button("📥 Download PDF", data=bytes(pdf_bytes), file_name="Statement.pdf")
            
        for p in selected:
            with st.expander(f"Preview: {p}", expanded=True):
                p_df = df_clean[df_clean['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                # تنسيق التاريخ للعرض في الجدول
                p_df['date'] = p_df['date'].dt.strftime('%Y-%m-%d')
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
    else:
        st.info("Please select a customer to display data.")

except Exception as e:
    st.error(f"Error: {e}")
