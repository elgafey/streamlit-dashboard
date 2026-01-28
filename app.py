import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Raw Material Report", layout="wide")

# -----------------------------
# Load CSV from GitHub
# -----------------------------
@st.cache_data 
def load_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # تحويل التاريخ مع معالجة الأخطاء
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # حذف الصفوف التي تحتوي على NaT (تاريخ غير صحيح أو فارغ) فورا
    df = df.dropna(subset=["date"])
    
    # تحويله إلى نوع date الخاص بـ python ليتوافق مع Streamlit
    df["date"] = df["date"].dt.date
    return df

try:
    df_raw = load_data()
    df = df_raw.copy()

    # تأكد أن البيانات ليست فارغة بعد التنظيف
    if df.empty:
        st.error("البيانات فارغة أو تحتوي على تواريخ غير صحيحة فقط.")
        st.stop()

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    # تحديد أقل وأكبر تاريخ (مع التأكد أنها قيم date صحيحة وليست NaT)
    min_date = df["date"].min()
    max_date = df["date"].max()

    # إضافة فلتر التاريخ مع تأمين القيم
    date_input = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # فلتر المنتجات
    available_products = sorted(df["product_name"].unique().tolist())
    selected_products = st.sidebar.multiselect(
        "Select Products",
        options=available_products,
        default=available_products
    )

    # -----------------------------
    # معالجة اختيار التاريخ بعناية
    # -----------------------------
    if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
        start_date, end_date = date_input
    else:
        # في حالة اختيار يوم واحد أو أثناء التحميل
        start_date = end_date = date_input[0] if isinstance(date_input, (list, tuple)) else date_input

    # -----------------------------
    # تطبيق الفلترة
    # -----------------------------
    mask = (
        (df["date"] >= start_date) & 
        (df["date"] <= end_date) & 
        (df["product_name"].isin(selected_products))
    )
    df_filtered = df.loc[mask]

    # -----------------------------
    # Streamlit UI
    # -----------------------------
    st.title("📦 Raw Material Daily Report")
    
    # عرض الـ Metrics فقط لو فيه بيانات
    if not df_filtered.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(df_filtered))
        with col2:
            if "raw_qty_used" in df_filtered.columns:
                st.metric("Total Qty Used", f"{df_filtered['raw_qty_used'].sum():,.2f}")
        with col3:
            if "raw_value_used" in df_filtered.columns:
                st.metric("Total Value", f"{df_filtered['raw_value_used'].sum():,.2f}")

        st.divider()
        st.subheader("📊 Data Details")
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.warning("لا توجد بيانات تطابق الفلاتر المختارة.")

except Exception as e:
    st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
