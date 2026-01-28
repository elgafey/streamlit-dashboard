import streamlit as st
import pandas as pd
from io import BytesIO

# إعدادات الصفحة
st.set_page_config(page_title="Raw Material Report", layout="wide")

# -----------------------------
# دالة تحميل البيانات من GitHub
# -----------------------------
@st.cache_data 
def load_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # تنظيف عمود التاريخ بناءً على صور البيانات التي أرسلتها سابقاً
    df['date_cleaned'] = df['date'].astype(str).str[:15]
    df["date_final"] = pd.to_datetime(df['date_cleaned'], errors="coerce")
    df = df.dropna(subset=["date_final"])
    df["date"] = df["date_final"].dt.date
    return df

try:
    df_raw = load_data()
    df = df_raw.copy()

    # -----------------------------
    # Sidebar Filters (الفلاتر الجانبية)
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    # 1. فلتر نطاق التاريخ
    min_date = df["date"].min()
    max_date = df["date"].max()
    date_input = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 2. فلتر المنتجات (التعديل هنا)
    available_products = sorted(df["product_name"].unique().tolist())
    selected_products = st.sidebar.multiselect(
        "Select Products (Leave empty for ALL)",
        options=available_products,
        default=[]  # التعديل: يبدأ فارغاً كما طلبت
    )

    # معالجة التاريخ
    if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
        start_date, end_date = date_input
    else:
        start_date = end_date = date_input[0] if isinstance(date_input, (list, tuple)) else date_input

    # -----------------------------
    # منطق الفلترة (التعديل هنا ليدعم العرض الشامل عند الفراغ)
    # -----------------------------
    # لو المستخدم لم يختار شيء (قائمة فارغة)، نعتبره اختار الكل
    if not selected_products:
        final_selected = available_products
    else:
        final_selected = selected_products

    mask = (
        (df["date"] >= start_date) & 
        (df["date"] <= end_date) & 
        (df["product_name"].isin(final_selected))
    )
    df_filtered = df.loc[mask]

    # -----------------------------
    # الواجهة الرئيسية (Streamlit UI)
    # -----------------------------
    st.title("📦 Raw Material Daily Report")
    
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
        display_cols = [c for c in df_filtered.columns if c not in ['date_cleaned', 'date_final']]
        st.dataframe(df_filtered[display_cols], use_container_width=True)

        # زر التحميل
        def to_excel(df_to_download):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_to_download.to_excel(writer, index=False, sheet_name="Report")
            return output.getvalue()

        st.sidebar.divider()
        excel_file = to_excel(df_filtered[display_cols])
        st.sidebar.download_button(
            label="⬇️ Download Excel",
            data=excel_file,
            file_name="raw_material_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ لا توجد بيانات.")

except Exception as e:
    st.error(f"❌ حدث خطأ: {e}")
