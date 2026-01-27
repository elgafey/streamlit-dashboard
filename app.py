import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard ", layout="wide")
st.title("📊 Dashboard ")

# تحميل البيانات من GitHub
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/main/net_received_po.csv"
    response = requests.get(url)
    response.encoding = "utf-8"
    return pd.read_csv(StringIO(response.text))

df = load_data()

# تحويل التاريخ
df["date_order"] = pd.to_datetime(df["date_order"], errors="coerce")
df = df.dropna(subset=["date_order"])  # حذف الصفوف اللي فيها تاريخ غير صالح

# فلتر التاريخ
min_date = df["date_order"].min().date()
max_date = df["date_order"].max().date()

col1, col2 = st.columns(2)
with col1:
    from_date = st.date_input("📅 من تاريخ", min_date)
with col2:
    to_date = st.date_input("📅 إلى تاريخ", max_date)

# فلترة حسب التاريخ
filtered_df = df[
    (df["date_order"] >= pd.to_datetime(from_date)) &
    (df["date_order"] <= pd.to_datetime(to_date))
]

# فلتر الموردين
vendor_list = filtered_df["vendor_name"].dropna().unique()
selected_vendors = st.multiselect("اختر الموردين", vendor_list)

if selected_vendors:
    filtered_df = filtered_df[filtered_df["vendor_name"].isin(selected_vendors)]

# جدول البيانات
st.write("### 📋 جدول البيانات")
st.dataframe(filtered_df, use_container_width=True)

# زرار تحميل البيانات
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ تحميل البيانات الظاهرة كـ CSV",
    data=csv,
    file_name="filtered_data.csv",
    mime="text/csv"
)

# رسم بياني حسب شهر الطلب
filtered_df["order_month"] = filtered_df["date_order"].dt.to_period("M").astype(str)
fig = px.histogram(
    filtered_df,
    x="order_month",
    title="📦 عدد الطلبات لكل شهر",
    color="order_month",
    text_auto=True
)
fig.update_layout(
    xaxis_title="الشهر",
    yaxis_title="عدد الطلبات",
    title_x=0.5,
    plot_bgcolor="white",
    paper_bgcolor="white"
)
st.plotly_chart(fig, use_container_width=True)


