import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات واجهة المستخدم
st.set_page_config(page_title="شركة سهول البيئة - نظام كشوفات الحساب", layout="wide")

def clean_text(text):
    t = str(text).strip()
    if not t or t.lower() in ['none', 'nan']: return "قيد محاسبي"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        # معالجة التاريخ لضمان عدم ظهور NaT
        df['date'] = df['date'].str.split(' GMT').str[0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # التأكد من صحة المبالغ المالية
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        return df
    except:
        return pd.DataFrame()

def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        # الهيدر الرسمي بالاسم الصحيح
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 8, "Environmental Plains for Raw Material Recycling", ln=True, align='L')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 6, "Saudi Arabia - Riyadh - VAT: 300451393600003", ln=True, align='L')
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, f"Customer: {clean_text(partner)}", ln=True)
        
        # جدول البيانات بتنسيق احترافي
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        cols = [("Date", 30), ("Description", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in cols: pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            d = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, d, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output(dest='S'))

# --- الواجهة البرمجية ---
df = load_data()
if not df.empty:
    st.sidebar.title("شركة سهول البيئة لتدوير المواد الأولية") #
    all_p = sorted(df['partner_id'].unique().tolist())
    
    # خيار اختيار الكل لطباعة شاملة
    select_all = st.sidebar.checkbox("اختيار كل العملاء (Select All)")
    
    if select_all:
        selected = all_p
    else:
        search = st.sidebar.text_input("بحث عن عميل:", "")
        filtered = [p for p in all_p if search.lower() in p.lower()]
        selected = st.sidebar.multiselect("اختر العملاء:", options=filtered)

    # حساب إحصائيات الداشبورد
    view_df = df[df['partner_id'].isin(selected)] if selected else df
    t_deb, t_cre = view_df['debit'].sum(), view_df['credit'].sum()

    st.header("📊 ملخص المديونيات")
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي المدين", f"{t_deb:,.2f} EGP")
    c2.metric("إجمالي الدائن", f"{t_cre:,.2f} EGP")
    c3.metric("صافي الرصيد", f"{(t_deb - t_cre):,.2f} EGP")
    st.markdown("---")

    if selected:
        # زر إعداد الملف المجمع
        if st.sidebar.button(f"📄 تجهيز تقرير لعدد ({len(selected)}) عميل"):
            with st.spinner("جاري إنشاء ملف PDF..."):
                st.session_state['pdf_blob'] = generate_pdf(df, selected)
        
        if 'pdf_blob' in st.session_state:
            st.sidebar.download_button("📥 تحميل كشوفات الحساب", st.session_state['pdf_blob'], "Suhul_Ledger.pdf")

        # معاينة ذكية (أول 3 فقط لمنع الشاشة السوداء)
        st.subheader("معاينة الحسابات")
        for p in selected[:3]:
            with st.expander(f"كشف حساب: {p}"):
                p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].tail(10))
else:
    st.error("خطأ في تحميل البيانات. يرجى التحقق من الملف المصدر.")
