import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import re
import os

st.set_page_config(page_title="Suhul Albeeah | Final Fix", layout="wide")

def fix_ar(text):
    if not text or str(text).lower() in ['nan', 'none']: return ""
    # تنظيف النص من أي رموز غريبة قد تسبب انهيار المكتبة
    text = re.sub(r'[^\w\s\.\-\(\)]+', ' ', str(text)) if not any("\u0600" <= c <= "\u06FF" for c in str(text)) else text
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # فلترة الحسابات للمطابقة مع أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    font_path = "Amiri-Regular.ttf"
    
    # محاولة تحميل الخط من رابط مباشر ومستقر جداً
    if not os.path.exists(font_path):
        try:
            url = "https://raw.githubusercontent.com/googlefonts/amiri/main/fonts/ttf/Amiri-Regular.ttf"
            r = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except: pass

    has_font = False
    if os.path.exists(font_path) and os.path.getsize(font_path) > 10000:
        try:
            pdf.add_font("Amiri", "", font_path)
            has_font = True
        except: has_font = False

    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        
        if has_font:
            pdf.set_font("Amiri", size=16)
            pdf.cell(0, 10, fix_ar("شركة سهول البيئة لتدوير المواد الأولية"), ln=True, align='C')
            pdf.set_font("Amiri", size=12)
            # التأكد من معالجة اسم الشريك بالعربي
            p_name = fix_ar(partner)
            pdf.cell(0, 10, f"Customer: {p_name}", ln=True, align='R')
        else:
            pdf.set_font("Helvetica", size=12)
            # حل أخير: لو مفيش خط، شيل العربي عشان البرنامج ميفصلش
            clean_name = re.sub(r'[\u0600-\u06FF]+', '', partner)
            pdf.cell(0, 10, f"Customer Ledger: {clean_name}", ln=True)

        pdf.ln(5)
        pdf.set_fill_color(240, 240, 240)
        # رأس الجدول
        headers = [("Balance", 35), ("Credit", 30), ("Debit", 30), ("Description", 65), ("Date", 30)]
        pdf.set_font("Amiri" if has_font else "Helvetica", size=10)
        for h, w in headers:
            pdf.cell(w, 10, fix_ar(h) if has_font else h, 1, 0, 'C', True)
        pdf.ln()

        pdf.set_font("Amiri" if has_font else "Helvetica", size=9)
        for _, r in cust_df.iterrows():
            pdf.cell(35, 8, f"{r['Running_Balance']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            desc = fix_ar(r['move_name']) if has_font else re.sub(r'[\u0600-\u06FF]+', '', str(r['move_name']))
            pdf.cell(65, 8, str(desc)[:40], 1, 0, 'R')
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- Streamlit UI ---
df = load_data()
if not df.empty:
    t1, t2 = st.tabs(["📑 Ledger", "⚖️ Trial Balance"])
    
    with t1:
        d_range = st.date_input("Select Period:", [df['date'].min(), df['date'].max()], key="L_unique")
        all_p = sorted(df['partner_id'].unique().tolist())
        selected = st.multiselect("Pick Customers:", options=all_p)
        
        if selected:
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1])) & (df['partner_id'].isin(selected))
            f_df = df[mask].copy()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Debit", f"{f_df['debit'].sum():,.2f}")
            c2.metric("Credit", f"{f_df['credit'].sum():,.2f}")
            c3.metric("Net", f"{f_df['net'].sum():,.2f}")

            if st.button("Generate PDF Report"):
                with st.spinner("Processing Arabic Fonts..."):
                    pdf_out = generate_pdf(f_df, selected)
                    st.download_button("📥 Download PDF", pdf_out, "Statement.pdf")

    with t2:
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        s_year = st.selectbox("Fiscal Year:", years)
        # ميزان المراجعة
        init = df[df['date'].dt.year < s_year].groupby('partner_id')['net'].sum().reset_index(name='Opening')
        peri = df[df['date'].dt.year == s_year].groupby('partner_id')['net'].sum().reset_index(name='Period')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['Ending'] = tb['Opening'] + tb['Period']
        st.dataframe(tb.sort_values('Ending', ascending=False), use_container_width=True)
