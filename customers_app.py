import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# 1. إعدادات الصفحة الأساسية لتجنب التهنيج
st.set_page_config(page_title="Ar Suhul - Official Ledger", layout="wide")

def clean_text(text):
    t = str(text).strip()
    if not t or t.lower() in ['none', 'nan']: return "Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# 2. تحميل البيانات مع معالجة الأخطاء لضمان ظهور الشاشة
@st.cache_data 
def load_final_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        # قراءة الملف مع التأكد من عدم وجود مشاكل في الترميز
        df = pd.read_csv(url, encoding='utf-8')
        
        # تحويل التاريخ بأمان
        if 'date' in df.columns:
            df['date'] = df['date'].str.split(' GMT').str[0]
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # تحويل المبالغ
        df["debit"] = pd.to_numeric(df.get("debit", 0), errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df.get("credit", 0), errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        return pd.DataFrame()

# 3. دالة الـ PDF مع الهيدر الرسمي
def generate_official_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        # الهيدر الرسمي لشركة سهول البيئة
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 6, "Environmental Plains for Raw Material Recycling", ln=True)
        pdf.set_font("Helvetica", '', 9)
        pdf.cell(0, 5, "Eastern Ring Road - Ar Rayyan, Riyadh, Saudi Arabia", ln=True)
        pdf.cell(0, 5, "VAT Number: 300451393600003", ln=True)
        pdf.ln(5)
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 10, f"Customer: {clean_text(partner)}", ln=True)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(230, 230, 230)
        cols = [("Date", 30), ("Move Name", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in cols: pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A", 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output(dest='S'))

# --- المنطق الرئيسي للواجهة ---
df = load_final_data()

if not df.empty:
    st.sidebar.title("⚙️ Control Center")
    
    # اختيار الكل
    select_all = st.sidebar.checkbox("Select All Customers (اختيار كل العملاء)")
    all_p = sorted(df['partner_id'].unique().tolist())
    
    if select_all:
        selected = all_p
    else:
        search = st.sidebar.text_input("Quick Search:", "")
        filtered = [p for p in all_p if search.lower() in p.lower()]
        selected = st.sidebar.multiselect("Pick Customers:", options=filtered)

    # حساب الإجماليات للداشبورد
    view_df = df[df['partner_id'].isin(selected)] if selected else df
    t_deb, t_cre = view_df['debit'].sum(), view_df['credit'].sum()

    st.title("📊 Ar Suhul Ledger Dashboard")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Debit", f"{t_deb:,.2f}")
    c2.metric("Total Credit", f"{t_cre:,.2f}")
    c3.metric("Net Exposure", f"{(t_deb - t_cre):,.2f}")
    st.markdown("---")

    if selected:
        if st.sidebar.button(f"📄 Build Report ({len(selected)} Customers)"):
            with st.spinner("Processing PDF..."):
                st.session_state['master_pdf'] = generate_official_pdf(df, selected)
        
        if 'master_pdf' in st.session_state:
            st.sidebar.download_button("📥 Save PDF Report", st.session_state['master_pdf'], "Ledger_Report.pdf")

        # عرض المعاينة
        for p in selected[:5]: # عرض أول 5 فقط لسرعة الواجهة
            with st.expander(f"Preview: {p}"):
                p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
else:
    st.warning("⚠️ Waiting for data... Please check your internet connection or GitHub link.")
