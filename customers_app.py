import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة الأساسية
st.set_page_config(page_title="Ar Suhul - Professional Financial Dashboard", layout="wide")

# تهيئة الحالة لحفظ مدخلات البحث وحالة ملف الـ PDF
if 'search_query' not in st.session_state: st.session_state['search_query'] = ""
if 'pdf_ready' not in st.session_state: st.session_state['pdf_ready'] = False
if 'pdf_data' not in st.session_state: st.session_state['pdf_data'] = None

# دالة تنظيف النصوص لضمان التوافق مع ملفات PDF
def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']: return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# تحميل ومعالجة البيانات من GitHub
@st.cache_data 
def load_and_clean_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    
    # قراءة الملف مع منع تحويل القيم الفارغة إلى منطقية (False)
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # معالجة تنسيق التاريخ الطويل (GMT) لضمان عدم ظهور NaT
    df['date'] = df['date'].str.split(' GMT').str[0] 
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # تنسيق المبالغ المالية
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # حذف التكرار الوهمي الناتج عن قراءة السطور الفارغة
    df = df.drop_duplicates(subset=['move_name', 'partner_id', 'debit', 'credit'], keep='first')
    
    return df

# توليد ملف PDF مجمع لكافة العملاء المختارين
def generate_pdf_report(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Account Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 10, f"Net Balance: {final_bal:,.2f} EGP", ln=True, align='C')
        pdf.ln(5)
        
        # ترويسة الجدول في التقرير
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        cols = [("Date", 30), ("Description", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for title, width in cols:
            pdf.cell(width, 10, title, 1, 0, 'C', True)
        pdf.ln()
        
        # محتوى الجدول
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            d_str = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, d_str, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
            
    return bytes(pdf.output(dest='S'))

# --- منطق تشغيل التطبيق ---
try:
    df_main = load_and_clean_data()
    partners_list = sorted(df_main['partner_id'].unique().tolist())

    # القائمة الجانبية (الأوامر والبحث)
    st.sidebar.title("🛠️ Tools & Filters")
    
    # زر مسح كافة الفلاتر (Reset)
    if st.sidebar.button("🧹 Clear All Filters"):
        st.session_state['search_query'] = ""
        st.session_state['pdf_ready'] = False
        st.rerun()

    # حقل البحث الذكي
    query = st.sidebar.text_input("Quick Customer Search:", value=st.session_state['search_query'])
    filtered_partners = [p for p in partners_list if query.lower() in p.lower()]
    
    selected = st.sidebar.multiselect("Select Target Customers:", options=filtered_partners)
    
    # خيار اختيار الكل للنتائج المفلترة
    if st.sidebar.checkbox("Select All Search Results"):
        selected = filtered_partners

    # --- لوحة البيانات الإجمالية (Dashboard Metrics) ---
    st.title("📂 Customer Ledger Dashboard")
    
    # حساب الإجماليات بناءً على الاختيار أو لكافة العملاء
    display_stats_df = df_main[df_main['partner_id'].isin(selected)] if selected else df_main
    total_debit = display_stats_df['debit'].sum()
    total_credit = display_stats_df['credit'].sum()
    grand_balance = total_debit - total_credit

    # عرض الأرقام في مربعات Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Debit (مدين)", f"{total_debit:,.2f} EGP")
    m2.metric("Total Credit (دائن)", f"{total_credit:,.2f} EGP")
    m3.metric("Net Balance (الإجمالي)", f"{grand_balance:,.2f} EGP", delta_color="normal")
    
    st.markdown("---")

    # معالجة وعرض كشوفات الحساب المختارة
    if selected:
        if st.sidebar.button("🚀 Prepare PDF Reports"):
            st.session_state['pdf_data'] = generate_pdf_report(df_main, selected)
            st.session_state['pdf_ready'] = True

        if st.session_state['pdf_ready']:
            st.sidebar.success("✅ Reports Ready!")
            st.sidebar.download_button(
                label="📥 Download Statements PDF",
                data=st.session_state['pdf_data'],
                file_name="ArSuhul_Statements.pdf",
                mime="application/pdf"
            )

        for p in selected:
            with st.expander(f"Statement Preview: {p}", expanded=True):
                p_df = df_main[df_main['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                
                # إعداد جدول العرض مع تنسيق التاريخ
                p_display = p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].copy()
                p_display['date'] = p_display['date'].dt.strftime('%Y-%m-%d')
                st.table(p_display)
    else:
        st.info("💡 Please use the sidebar to search and select customers. Summary above shows total company exposure.")

except Exception as e:
    st.error(f"Critical System Error: {e}")
