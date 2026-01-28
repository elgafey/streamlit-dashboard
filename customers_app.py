import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import os

# 1. إعدادات الصفحة
st.set_page_config(page_title="Suhul Albeeah | Financial Portal", layout="wide")

def fix_arabic(text):
    """تجهيز النص العربي للظهور بشكل صحيح"""
    if not text or str(text).lower() in ['nan', 'none']: return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

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

def download_font():
    """تحميل خط يدعم العربية إذا لم يكن موجوداً"""
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/amiri/raw/main/fonts/ttf/Amiri-Regular.ttf"
        r = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(r.content)
    return font_path

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    font_p = download_font()
    # تسجيل الخط العربي في المكتبة لمنع الـ Unicode Error
    pdf.add_font("Amiri", "", font_p)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # استخدام خط Amiri لكل النصوص اللي فيها احتمال عربي
        pdf.set_font("Amiri", size=14)
        pdf.cell(0, 8, "SUHUL ALBEEAH - شركة سهول البيئة", ln=True, align='C')
        pdf.set_font("Amiri", size=10)
        pdf.cell(0, 5, fix_arabic("الرقم الضريبي: 300451393600003"), ln=True, align='R')
        pdf.ln(10)
        
        pdf.set_font("Amiri", size=16)
        pdf.cell(0, 10, fix_arabic("كشف حساب شريك"), ln=True, align='C')
        
        # طباعة اسم العميل بالعربي
        pdf.set_font("Amiri", size=12)
        pdf.cell(0, 10, f"Customer: {fix_arabic(partner)}", ln=True, align='R')
        pdf.ln(5)
        
        # الجدول
        pdf.set_fill_color(230, 230, 230)
        headers = [("Balance", 35), ("Credit", 30), ("Debit", 30), ("Description", 65), ("Date", 30)]
        for h, w in headers: pdf.cell(w, 10, fix_arabic(h), 1, 0, 'C', True)
        pdf.ln()
        
        for _, r in cust_df.iterrows():
            pdf.cell(35, 8, f"{r['Running_Balance']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(65, 8, fix_arabic(r['move_name'])[:35], 1, 0, 'R')
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- التطبيق ---
df = load_data()
if not df.empty:
    tab1, tab2 = st.tabs(["📑 Ledger", "⚖️ Trial Balance"])

    with tab1:
        st.subheader("Individual Statements")
        # فلتر التاريخ المنفصل
        d_range = st.date_input("Period:", [df['date'].min(), df['date'].max()], key="L_date")
        all_p = sorted(df['partner_id'].unique().tolist())
        selected = st.multiselect("Customers:", options=all_p)
        if st.checkbox("Select All"): selected = all_p

        if selected:
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1])) & (df['partner_id'].isin(selected))
            f_df = df[mask].copy()
            
            # عرض الإجماليات
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Debit", f"{f_df['debit'].sum():,.2f}")
            c2.metric("Total Credit", f"{f_df['credit'].sum():,.2f}")
            c3.metric("Net Balance", f"{f_df['net'].sum():,.2f}")

            if st.button("Download Arabic PDF"):
                st.session_state['pdf_data'] = generate_pdf(f_df, selected)
            
            if 'pdf_data' in st.session_state:
                st.download_button("📥 Save PDF", st.session_state['pdf_data'], "Suhul_Arabic_Ledger.pdf")

    with tab2:
        # تابة الميزان بفلتر سنة مستقل
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        s_year = st.selectbox("Fiscal Year:", years, key="TB_year")
        
        init = df[df['date'].dt.year < s_year].groupby('partner_id')['net'].sum().reset_index(name='Initial')
        peri = df[df['date'].dt.year == s_year].groupby('partner_id')['net'].sum().reset_index(name='Period')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['Ending'] = tb['Initial'] + tb['Period']
        
        st.dataframe(tb.sort_values('Ending', ascending=False), use_container_width=True)

else: st.error("Data Load Error.")
