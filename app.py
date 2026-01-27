import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.title("Dashboard من GitHub CSV")

# رابط GitHub RAW
url = "https://raw.githubusercontent.com/elgafey/sql-data/main/net_received_po.csv"

# تحميل الملف من GitHub بطريقة آمنة
response = requests.get(url)
response.encoding = "utf-8"   # مهم جداً
df = pd.read_csv(StringIO(response.text))

# فلتر الموردين
vendor_list = df["vendor_name"].dropna().unique()
selected_vendors = st.multiselect("اختر الموردين", vendor_list)

# فلترة
filtered_df = df.copy()
if selected_vendors:
    filtered_df = filtered_df[filtered_df["vendor_name"].isin(selected_vendors)]

# جدول
st.write("### جدول البيانات")
st.dataframe(filtered_df)

# رسم
fig = px.histogram(filtered_df, x="month", title="عدد الطلبات لكل شهر")
st.plotly_chart(fig)
