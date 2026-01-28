import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# إعداد الصفحة
st.set_page_config(page_title="كشوف حسابات السهول", layout="wide")

st.title("👥 نظام كشوف الحسابات المجمع")

# -----------------------------
# دالة تحميل البيانات
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# دالة إنشاء الـ PDF (تدعم لغات متعددة)
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    
    # تحميل خط يدعم العربية والانجليزية (لازم ترفع الملف Arial.ttf على جيت هب)
    try:
        # ملاحظة: الخط ده بيحل مشكلة الـ Character Error
        pdf.add_font('UniFont', '', 'Arial.ttf', uni=True) 
        font_name = 'UniFont'
    except:
        # لو الخط مش موجود، هيستخدم الخط العادي وهيطلع Error لو في عربي
        font_name = 'Helvetica'
        st.warning("⚠️ تحذير: ملف الخط Arial.ttf غير موجود، قد يحدث خطأ في الحروف العربية.")

    for partner in selected_partners:
        # تصفية بيانات العميل وحساب الرصيد التراكمي
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # العنوان
        pdf.set_font(font_name, 'B', 16)
        pdf.cell(0, 10, f"Statement of Account: {partner}", ln=True, align='C')
        pdf.ln(10)
        
        # رأس الجدول
        pdf.set_font(font_name, 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(35, 10, "Date", 1, 0, 'C', True)
        pdf.cell(65, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # محتوى الجدول
        pdf.set_font(font_name, '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(35, 8, str(row['date']), 1)
            pdf.cell(65, 8, str(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# تشغيل الواجهة
# -----------------------------
try:
    df_all = load_ar_suhul()
    partners = sorted(df_all['partner_id'].unique().tolist())
    
    st.sidebar.header("إعدادات الطباعة")
    selected_partners = st.sidebar.multiselect("اختر العملاء المطلوبين في ملف واحد", options=partners)

    if selected_partners:
        if st.sidebar.button("🚀 إصدار ملف PDF المجمع"):
            pdf_bytes = generate_pdf(df_all, selected_partners)
            st.sidebar.download_button(
                label="📥 تحميل الملف الآن",
                data=bytes(pdf_bytes),
                file_name="Combined_Statements.pdf",
                mime="application/pdf"
            )
            st.success(f"تم إنشاء {len(selected_partners)} صفحات بنجاح!")
            
        # عرض معاينة
        for p in selected_partners:
            with st.expander(f"معاينة كشف حساب: {p}"):
                p_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("اختر العملاء من القائمة الجانبية.")

except Exception as e:
    st.error(f"Error: {e}")
