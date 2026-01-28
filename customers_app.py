import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import os

st.set_page_config(page_title="Suhul Albeeah | Arabic PDF System", layout="wide")

def fix_arabic(text):
    if not text or str(text).lower() in ['nan', 'none']: return ""
    # معالجة النص العربي لضمان الاتصال والاتجاه الصحيح
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def download_font():
    """تحميل خط Amiri بشكل آمن وموثوق"""
    font_path = "Amiri-Regular.ttf"
    # رابط مباشر لملف الـ TTF الخام من مستودع موثوق
    url = "https://github.com/googlefonts/amiri/raw/main/fonts/ttf/Amiri-Regular.ttf"
    
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 1000:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
            else:
                st.error("فشل تحميل الخط من السيرفر. تأكد من اتصال الإنترنت.")
        except Exception as e:
            st.error(f"خطأ في تحميل الخط: {e}")
    return font_path

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        # فلترة الحسابات لمطابقة أرقام أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    font_p = download_font()
    
    # التحقق من وجود الخط وصحته قبل تسجيله
    if os.path.exists(font_p) and os.path.getsize(font_p) > 1000:
        pdf.add_font("Amiri", "", font_p)
        pdf.set_font("Amiri", size=12)
    else:
        st.error("ملف الخط غير صالح. سيتم استخدام الخط الافتراضي (قد لا يدعم العربي).")
        pdf.set_font("Helvetica", size=12)

    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # تنسيق الهيدر العربي
        pdf.set_font("Amiri", size=16)
        pdf.cell(0, 10, fix_arabic("شركة سهول البيئة لتدوير المواد الأولية"), ln=True, align='C')
        pdf.set_font("Amiri", size=10)
        pdf.cell(0, 5, fix_arabic("الرقم الضريبي: 300451393600003"), ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Amiri", size=14)
        pdf.cell(0, 10, fix_arabic(f"كشف حساب: {partner}"), ln=True, align='R')
        pdf.ln(5)
        
        # تصميم الجدول
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Amiri", size=10)
        cols = [("الرصيد", 35), ("دائن", 30), ("مدين", 30), ("البيان", 65), ("التاريخ", 30)]
        for h, w in cols: pdf.cell(w, 10, fix_arabic(h), 1, 0, 'C', True)
        pdf.ln()
        
        for _, r in cust_df.iterrows():
            pdf.cell(35, 8, f"{r['Running_Balance']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(65, 8, fix_arabic(r['move_name'])[:40], 1, 0, 'R')
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- الواجهة ---
df = load_data()
if not df.empty:
    tab1, tab2 = st.tabs(["📑 كشوف الحسابات", "⚖️ ميزان المراجعة"])

    with tab1:
        # فلاتر مستقلة للتابة الأولى
        d_range = st.date_input("اختر الفترة:", [df['date'].min(), df['date'].max()], key="ledger_date")
        all_p = sorted(df['partner_id'].unique().tolist())
        selected = st.multiselect("اختر العملاء:", options=all_p)
        if st.checkbox("اختيار الكل"): selected = all_p

        if selected:
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1])) & (df['partner_id'].isin(selected))
            f_df = df[mask].copy()
            
            # عرض الأرقام مطابقة لأودو
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي المدين", f"{f_df['debit'].sum():,.2f}")
            c2.metric("إجمالي الدائن", f"{f_df['credit'].sum():,.2f}")
            c3.metric("صافي الرصيد", f"{f_df['net'].sum():,.2f}")

            if st.button("تحميل PDF بالعربي"):
                with st.spinner("جاري معالجة اللغة العربية..."):
                    st.session_state['pdf_blob'] = generate_pdf(f_df, selected)
            
            if 'pdf_blob' in st.session_state:
                st.download_button("📥 حفظ الملف", st.session_state['pdf_blob'], "Suhul_Statement.pdf")

    with tab2:
        # فلاتر مستقلة لميزان المراجعة
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        s_year = st.selectbox("السنة المالية:", years, key="tb_year")
        
        init = df[df['date'].dt.year < s_year].groupby('partner_id')['net'].sum().reset_index(name='الرصيد الافتتاحي')
        peri = df[df['date'].dt.year == s_year].groupby('partner_id')['net'].sum().reset_index(name='حركة الفترة')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['الرصيد الختامي'] = tb['الرصيد الافتتاحي'] + tb['حركة الفترة']
        
        st.dataframe(tb.sort_values('الرصيد الختامي', ascending=False), use_container_width=True)
