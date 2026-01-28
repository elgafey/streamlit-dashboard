import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import re

# 1. إعدادات الصفحة
st.set_page_config(page_title="Suhul Albeeah | Financial Portal", layout="wide")

def fix_arabic(text):
    """تعديل النصوص العربية لتظهر بشكل صحيح في الـ PDF"""
    if not text or str(text).lower() in ['nan', 'none']:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        # فلترة الحسابات للمطابقة مع أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    # استخدام FPDF2 لدعم الـ Unicode
    pdf = FPDF()
    # إضافة خط يدعم العربية (يجب أن يكون ملف الخط متوفراً في السيرفر أو مجلد المشروع)
    # ملاحظة: سنستخدم الخطوط الافتراضية هنا ولكن يفضل رفع ملف ttf للحصول على مظهر مثالي
    try:
        pdf.add_font('Arial', '', 'https://github.com/reingart/pyfpdf/raw/master/font/arial.ttf', uni=True)
        pdf.set_font('Arial', '', 12)
    except:
        pdf.set_font("Helvetica", size=12)
    
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # الهيدر
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 8, "SUHUL ALBEEAH", ln=True, align='L')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 5, "VAT: 300451393600003", ln=True); pdf.ln(10)
        
        # العنوان والاسم العربي
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        
        # هنا تظهر أسماء العملاء بالعربي
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 10, f"Customer: {fix_arabic(partner)}", ln=True, align='R'); pdf.ln(5)
        
        # الجدول
        pdf.set_fill_color(230, 230, 230)
        header_cols = [("Date", 30), ("Move Name", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in header_cols:
            pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", '', 9)
        for _, r in cust_df.iterrows():
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1)
            pdf.cell(70, 8, fix_arabic(r['move_name'])[:40], 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['Running_Balance']:,.2f}", 1, 1, 'R')
            
    return bytes(pdf.output())

df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 Ledger", "⚖️ Trial Balance"])

    # --- TAB 1: LEDGER (فلاتر مستقلة) ---
    with tab1:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            date_range = st.date_input("Period:", [df['date'].min(), df['date'].max()], key="L1")
        with col_f2:
            all_p = sorted(df['partner_id'].unique().tolist())
            selected = st.multiselect("Customers:", options=all_p)
            s_all = st.checkbox("Select All")
            if s_all: selected = all_p

        if selected:
            mask = (df['date'] >= pd.Timestamp(date_range[0])) & \
                   (df['date'] <= pd.Timestamp(date_range[1])) & \
                   (df['partner_id'].isin(selected))
            f_df = df[mask].copy()

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Debit", f"{f_df['debit'].sum():,.2f}")
            m2.metric("Total Credit", f"{f_df['credit'].sum():,.2f}")
            m3.metric("Balance", f"{f_df['net'].sum():,.2f}")
            
            if st.button("Generate Arabic PDF"):
                st.session_state['arabic_pdf'] = generate_pdf(f_df, selected)
            
            if 'arabic_pdf' in st.session_state:
                st.download_button("📥 Download", st.session_state['arabic_pdf'], "Suhul_Arabic.pdf")

    # --- TAB 2: TRIAL BALANCE (سنة مستقلة) ---
    with tab2:
        y_col, _ = st.columns([1, 3])
        with y_col:
            years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
            sel_y = st.selectbox("Year:", years, key="Y1")

        init = df[df['date'].dt.year < sel_y].groupby('partner_id')['net'].sum().reset_index(name='Initial')
        peri = df[df['date'].dt.year == sel_y].groupby('partner_id')['net'].sum().reset_index(name='Period')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['Ending'] = tb['Initial'] + tb['Period']
        
        st.dataframe(tb.sort_values('Ending', ascending=False), use_container_width=True)
