import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.title("Dashboard من GitHub CSV")

url = "https://raw.githubusercontent.com/elgafey/sql-data/main/net_received_po.csv"
response = requests.get(url)
response.encoding = "utf-8"
df = pd.read_csv(StringIO(response.text))

# تحويل التاريخ
df["month"] = pd.to_datetime(df["month"])

# فلتر التاريخ
min_date = df["month"].min()
max_date = df["month"].max()

from_date = st.date_input("📅 من تاريخ", min_date)
to_date = st.date_input("📅 إلى تاريخ", max_date)

# فلترة حسب التاريخ
filtered_df = df[
    (df["month"] >= pd.to_datetime(from_date)) &
    (df["month"] <= pd.to_datetime(to_date))
]

# فلتر الموردين
vendor_list = filtered_df["vendor_name"].dropna().unique()
selected_vendors = st.multiselect("اختر الموردين", vendor_list)

if selected_vendors:
    filtered_df = filtered_df[filtered_df["vendor_name"].isin(selected_vendors)]

st.write("### جدول البيانات")
st.dataframe(filtered_df)

# زرار تحميل البيانات
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ تحميل البيانات الظاهرة كـ CSV",
    data=csv,
    file_name="filtered_data.csv",
    mime="text/csv"
)

# رسم
fig = px.histogram(filtered_df, x="month", title="عدد الطلبات لكل شهر")
st.plotly_chart(fig)
