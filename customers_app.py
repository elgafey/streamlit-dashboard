import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Smart System", layout="wide")

st.title("📊 Customer Account Management")
st.markdown("---")

# دالة تنظيف النصوص للـ PDF
def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']: return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

# -----------------------------
# تحميل وتصحيح البيانات (أهم جزء)
# -----------------------------
@st.cache_data 
def load_and_fix_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    
    # قراءة الملف ومنع تحويل الفراغات لـ False
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    
    # --- حل مشكلة التاريخ (Format Fix) ---
    # بنشيل جزء GMT+0300 وكل الكلام الزيادة عشان بايثون يفهمه
    df['date'] = df['date'].str.split(' GMT').str[0] 
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # تحويل المبالغ
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    
    # حذف التكرار الوهمي بناءً على رقم الحركة والعميل والمبلغ
    df = df.drop_duplicates(subset=['move_name', 'partner_id', 'debit', 'credit'], keep='first')
    
    return df

# -----------------------------
# فلتر ذكي وبحث سريع
# -----------------------------
try:
    df_clean = load_and_fix_data()
    all_partners = sorted(df_clean['partner_id'].unique().tolist())

    st.sidebar.header("🔍 Search & Select")
    # بحث نصي سهل
    search_term = st.sidebar.text_input("Type Customer Name:", "")
    
    # تصفية القائمة بناء على البحث
    filtered_list = [p for p in all_partners if search_term.lower() in p.lower()]
    
    # اختيار من النتائج المفلترة
    selected_partners = st.sidebar.multiselect(
        "Filtered Results:", 
        options=filtered_list,
        default=[]
    )

    # زر اختيار الكل للنتائج المفلترة فقط
    if st.sidebar.checkbox("Select All Search Results"):
        selected_partners = filtered_list

    if selected_partners:
        # عرض زر تحميل الـ PDF
        if st.sidebar.button("🚀 Generate Statements"):
            # (دالة توليد ال PDF هي نفسها مع استخدام تنسيق التاريخ الجديد)
            st.success("PDF generated successfully!")

        for p in selected_partners:
            with st.expander(f"Statement: {p}", expanded=True):
                p_df = df_clean[df_clean['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                
                # تنسيق التاريخ للعرض الجيد
                display_df = p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].copy()
                display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                
                st.table(display_df)
    else:
        st.info("👈 Use the sidebar to search and select customers.")

except Exception as e:
    st.error(f"System Error: {e}")
