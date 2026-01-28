import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import os

st.set_page_config(page_title="Suhul Albeeah | Arabic Financials", layout="wide")

def fix_arabic(text):
    if not text or str(text).lower() in ['nan', 'none']: return ""
    # إعادة تشكيل الحروف العربية لتناسب الـ PDF
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

@st.cache_resource
def get_font_file():
    """تحميل الخط من مصدر موثوق وتخزينه مؤقتاً"""
    font_path = "Amiri-Regular.ttf"
    # رابط جوجل فونتس الرسمي المباشر
    url = "https://raw.githubusercontent.com/googlefonts/amiri/main/fonts/ttf/Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            r = requests.get(url, allow_redirects=True)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except:
            return None
    return font_path

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        # فلترة الحسابات لمطابقة أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    font_p = get_font_file()
    
    # محاولة إضافة الخط العربي، وإذا فشل نستخدم الخط الافتراضي مع رسالة تنبيه
    if font_p and os.path.exists(font_p) and os.path.getsize(font_p) > 5000:
        pdf.add_font("Amiri", "", font_p)
        pdf.set_font("Amiri", size=12)
        using_arabic = True
    else:
        pdf.set_font("Helvetica", size=12)
        using_arabic = False
        st.warning("تحذير: لم يتم تحميل الخط العربي بشكل صحيح، قد تظهر الأسماء بشكل غير سليم.")

    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # هيدر الشركة
        pdf.set_font("Amiri" if using_arabic else "Helvetica", size=16)
        pdf.cell(0, 10, fix_arabic("شركة سهول البيئة لتدوير المواد الأولية"), ln=True, align='C')
        pdf.set_font("Amiri" if using_arabic else "Helvetica", size=10)
        pdf.cell(0, 5, "VAT: 300451393600003", ln=True, align='C')
        pdf.ln(10)
        
        # اسم العميل
        pdf.set_font("Amiri" if using_arabic else "Helvetica", size=14)
        pdf.cell(0, 10, fix_arabic(f"كشف حساب: {partner}"), ln=True, align='R')
        pdf.ln(5)
        
        # الجدول
        pdf.set_fill_color(245, 245, 245)
        cols = [("الرصيد", 35), ("دائن", 30), ("مدين", 30), ("البيان", 65), ("التاريخ", 30)]
        for h, w in cols: pdf.cell(w, 10, fix_arabic(h), 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Amiri" if using_arabic else "Helvetica", size=9)
        for _, r in cust_df.iterrows():
            pdf.cell(35, 8, f"{r['Running_Balance']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(65, 8, fix_arabic(r['move_name'])[:40], 1, 0, 'R')
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- واجهة المستخدم ---
df = load_data()
if not df.empty:
    tab1, tab2 = st.tabs(["📑 Ledger", "⚖️ Trial Balance"])

    with tab1:
        st.subheader("Individual Statements")
        d_range = st.date_input("Period:", [df['date'].min(), df['date'].max()], key="L_date")
        all_p = sorted(df['partner_id'].unique().tolist())
        selected = st.multiselect("Select Customers:", options=all_p)
        if st.checkbox("Select All (PDF)"): selected = all_p

        if selected:
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1])) & (df['partner_id'].isin(selected))
            f_df = df[mask].copy()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Debit", f"{f_df['debit'].sum():,.2f}")
            c2.metric("Credit", f"{f_df['credit'].sum():,.2f}")
            c3.metric("Net", f"{f_df['net'].sum():,.2f}")

            if st.button("تحميل كشف حساب PDF"):
                with st.spinner("جاري إنشاء التقرير..."):
                    st.session_state['pdf_report'] = generate_pdf(f_df, selected)
            
            if 'pdf_report' in st.session_state:
                st.download_button("📥 حفظ الملف", st.session_state['pdf_report'], "Suhul_Ledger.pdf")

    with tab2:
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        s_year = st.selectbox("Fiscal Year:", years, key="T_year")
        
        # حساب ميزان المراجعة
        init = df[df['date'].dt.year < s_year].groupby('partner_id')['net'].sum().reset_index(name='Opening')
        peri = df[df['date'].dt.year == s_year].groupby('partner_id')['net'].sum().reset_index(name='Movement')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['Ending'] = tb['Opening'] + tb['Movement']
        
        st.dataframe(tb.sort_values('Ending', ascending=False).style.format("{:,.2f}", subset=['Opening', 'Movement', 'Ending']), use_container_width=True)

else: st.error("Data Load Failed.")
