import streamlit as st
import pandas as pd
from io import BytesIO

# إعدادات الصفحة
st.set_page_config(page_title="Raw Material Report", layout="wide")

# -----------------------------
# Load CSV from GitHub
# -----------------------------
@st.cache_data 
def load_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
    df = pd.read_csv(url, encoding='utf-8')
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    return df

try:
    df_raw = load_data()
    df = df_raw.copy()

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    # 1. فلتر التاريخ
    min_date = df["date"].min()
    max_date = df["date"].max()
    date_input = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 2. فلتر المنتجات (الجديد)
    # استخراج قائمة المنتجات الفريدة
    available_products = sorted(df["product_name"].unique())
    selected_products = st.sidebar.multiselect(
        "Select Products",
        options=available_products,
        default=available_products # افتراضياً يختار الكل
    )

    # -----------------------------
    # معالجة اختيار التاريخ
    # -----------------------------
    if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
        start_date, end_date = date_input
    elif isinstance(date_input, (list, tuple)) and len(date_input) == 1:
        start_date = end_date = date_input[0]
    else:
        start_date = end_date = date_input

    # -----------------------------
    # تطبيق الفلترة (تاريخ + منتجات)
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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", len(df_filtered))
    with col2:
        if "raw_qty_used" in df_filtered.columns:
            total_qty = df_filtered["raw_qty_used"].sum()
            st.metric("Total Qty Used", f"{total_qty:,.2f}")
    with col3:
        if "raw_value_used" in df_filtered.columns:
            total_val = df_filtered["raw_value_used"].sum()
            st.metric("Total Value", f"{total_val:,.2f}")

    st.divider()

    st.subheader("📊 Data Details")
    st.dataframe(df_filtered, use_container_width=True)

    # -----------------------------
    # Download as Excel
    # -----------------------------
    def to_excel(df_to_download):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_to_download.to_excel(writer, index=False, sheet_name="Sheet1")
        return output.getvalue()

    st.sidebar.divider()
    if not df_filtered.empty:
        excel_file = to_excel(df_filtered)
        st.sidebar.download_button(
            label="⬇️ Download Filtered Data (Excel)",
            data=excel_file,
            file_name=f"raw_material_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.sidebar.warning("No data found for selected filters.")

except Exception as e:
    st.error(f"Error loading data: {e}")
