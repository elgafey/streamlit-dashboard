import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Suhul Albeeah Financial System", layout="wide")

# دالة لتنسيق النصوص العربية للـ PDF
def fix_ar(text):
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
        
        # فلترة الحسابات للمطابقة مع أودو (الأكواد اللي في صورتك)
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    
    # تحميل الخط مباشرة من الإنترنت في الذاكرة (بدون حفظ ملفات) لضمان الاستقرار
    font_url = "https://github.com/googlefonts/amiri/raw/main/fonts/ttf/Amiri-Regular.ttf"
    try:
        response = requests.get(font_url)
        font_data = io.BytesIO(response.content)
        # حفظ مؤقت للخط في السيرفر لتقرأه المكتبة
        with open("Amiri.ttf", "wb") as f:
            f.write(response.content)
        pdf.add_font("Amiri", "", "Amiri.ttf")
        has_font = True
    except:
        has_font = False

    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        
        if has_font:
            pdf.set_font("Amiri", size=16)
            pdf.cell(0, 10, fix_ar("شركة سهول البيئة لتدوير المواد الأولية"), ln=True, align='C')
            pdf.set_font("Amiri", size=12)
            pdf.cell(0, 10, f"{fix_ar('كشف حساب للعميل')}: {fix_ar(partner)}", ln=True, align='R')
        else:
            pdf.set_font("Helvetica", size=14)
            pdf.cell(0, 10, f"Statement for: {partner}", ln=True)

        pdf.ln(5)
        # تصميم الجدول
        pdf.set_fill_color(230, 230, 230)
        cols = [("الرصيد", 35), ("دائن", 30), ("مدين", 30), ("البيان", 65), ("التاريخ", 30)]
        
        if has_font: pdf.set_font("Amiri", size=10)
        for h, w in cols:
            pdf.cell(w, 10, fix_ar(h) if has_font else h, 1, 0, 'C', True)
        pdf.ln()

        if has_font: pdf.set_font("Amiri", size=9)
        for _, r in cust_df.iterrows():
            pdf.cell(35, 8, f"{r['Running_Balance']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(65, 8, fix_ar(r['move_name'])[:40] if has_font else str(r['move_name'])[:30], 1, 0, 'R')
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- التطبيق الرئيسي ---
df = load_data()
if not df.empty:
    tab1, tab2 = st.tabs(["📑 كشوف الحسابات", "⚖️ ميزان المراجعة"])
    
    with tab1:
        # فلتر تاريخ خاص بالتابة الأولى
        d_range = st.date_input("فترة كشف الحساب:", [df['date'].min(), df['date'].max()], key="date_l")
        all_p = sorted(df['partner_id'].unique().tolist())
        selected = st.multiselect("اختر العميل:", options=all_p)
        
        if selected:
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1])) & (df['partner_id'].isin(selected))
            f_df = df[mask].copy()
            
            # إجماليات لمطابقة أودو
            st.columns(3)[0].metric("إجمالي المدين", f"{f_df['debit'].sum():,.2f}")
            st.columns(3)[1].metric("إجمالي الدائن", f"{f_df['credit'].sum():,.2f}")
            st.columns(3)[2].metric("الرصيد الحالي", f"{f_df['net'].sum():,.2f}")

            if st.button("تحميل كشف الحساب (PDF)"):
                pdf_bytes = generate_pdf(f_df, selected)
                st.download_button("📥 اضغط هنا للحفظ", pdf_bytes, "Statement.pdf")

    with tab2:
        # تابة ميزان المراجعة بفلتر سنة مستقل
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        s_year = st.selectbox("السنة المالية لميزان المراجعة:", years)
        
        init = df[df['date'].dt.year < s_year].groupby('partner_id')['net'].sum().reset_index(name='الافتتاحي')
        peri = df[df['date'].dt.year == s_year].groupby('partner_id')['net'].sum().reset_index(name='الحركة')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['الرصيد الختامي'] = tb['الافتتاحي'] + tb['الحركة']
        
        st.dataframe(tb.sort_values('الرصيد الختامي', ascending=False), use_container_width=True)
else:
    st.error("فشل في تحميل البيانات.")
