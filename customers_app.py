import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# إعدادات الصفحة
st.set_page_config(page_title="كشوف حسابات العملاء", layout="wide")

st.title("👥 نظام إصدار كشوف الحسابات المجمعة")
st.markdown("---")

# -----------------------------
# دالة تحميل البيانات
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    # تحويل التاريخ وترتيبه لضمان صحة الرصيد التراكمي
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# منطق إنشاء PDF متعدد الصفحات
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # تصفية البيانات وحساب الرصيد التراكمي لكل عميل على حدة
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        # إضافة صفحة جديدة لكل عميل
        pdf.add_page()
        
        # عنوان الصفحة (بما أن FPDF الافتراضية لا تدعم العربي بمرونة، سنستخدم الإنجليزية هنا للعناوين لضمان العمل)
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Statement: {partner}", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Final Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f}", ln=True, align='C')
        pdf.ln(10)
        
        # رأس الجدول
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(35, 10, "Date", 1, 0, 'C', True)
        pdf.cell(65, 10, "Movement", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # بيانات الجدول
        pdf.set_font("Arial", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(35, 8, str(row['date']), 1)
            pdf.cell(65, 8, str(row['move_name'])[:30], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# الواجهة الرئيسية
# -----------------------------
try:
    df_all = load_ar_suhul()
    
    # اختيار العملاء من القائمة الجانبية
    st.sidebar.header("إعدادات الطباعة المجمعة")
    partners = sorted(df_all['partner_id'].unique().tolist())
    selected_partners = st.sidebar.multiselect("اختر العملاء المطلوبين", options=partners)

    if selected_partners:
        # زر إنشاء الملف
        if st.sidebar.button("إنشاء ملف PDF مجمع"):
            with st.spinner('جاري تحضير الملف...'):
                pdf_bytes = generate_pdf(df_all, selected_partners)
                st.sidebar.download_button(
                    label="📥 تحميل ملف الـ PDF المجمع",
                    data=bytes(pdf_bytes),
                    file_name="Customer_Statements_Combined.pdf",
                    mime="application/pdf"
                )
            st.success(f"تم تجهيز كشوف الحساب لـ {len(selected_partners)} عميل بنجاح!")

        # عرض معاينة سريعة على الشاشة
        for p in selected_partners:
            with st.expander(f"معاينة كشف حساب: {p}"):
                p_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("قم باختيار العملاء من القائمة الجانبية لبدء إصدار كشوف الحساب المجمعة.")

except Exception as e:
    st.error(f"حدث خطأ: {e}")
