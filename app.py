import streamlit as st
import pandas as pd
from io import BytesIO

# -----------------------------
# Load CSV from GitHub
# -----------------------------
url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
df = pd.read_csv(url)

# -----------------------------
# Fix date column safely
# -----------------------------
# تحويل التاريخ لنص
df["date"] = df["date"].astype(str).str.strip()

# تحويل datetime مع تجاهل الأخطاء
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# حذف الصفوف اللي فيها تاريخ بايظ
df = df.dropna(subset=["date"])

# تحويل التاريخ إلى تاريخ فقط بدون وقت
df["date"] = df["date"].dt.date

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📦 Raw Material Daily Report")
st.write("")

# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

date_input = st.sidebar.date_input(
    "Date From → To",
    value=[df["date"].min(), df["date"].max()],
    min_value=df["date"].min(),
    max_value=df["date"].max()
)

# -----------------------------
# Normalize Streamlit date input
# -----------------------------
if isinstance(date_input, list) and len(date_input) == 2:
    start_date = date_input[0]
    end_date = date_input[1]
else:
    start_date = date_input
    end_date = date_input

# تحويل start/end إلى تاريخ فقط
start_date = pd.to_datetime(start_date).date()
end_date = pd.to_datetime(end_date).date()

# -----------------------------
# Apply filter
# -----------------------------
df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# -----------------------------
# Display Table
# -----------------------------
st.subheader("📊 Raw Material Usage (Filtered)")
st.dataframe(df, use_container_width=True)

# -----------------------------
# Download as Excel
# -----------------------------
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="RawMaterialDaily")
    writer.close()
    return output.getvalue()

excel_file = to_excel(df)

st.download_button(
    label="⬇️ Download Excel",
    data=excel_file,
    file_name="raw_material_daily.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
