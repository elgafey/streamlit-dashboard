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

vendor_list = df["vendor_name"].dropna().unique()
selected_vendors = st.multiselect("اختر الموردين", vendor_list)

filtered_df = df.copy()
if selected_vendors:
    filtered_df = filtered_df[filtered_df["vendor_name"].isin(selected_vendors)]

st.write("### جدول البيانات")
st.dataframe(filtered_df)

fig = px.histogram(filtered_df, x="month", title="عدد الطلبات لكل شهر")
st.plotly_chart(fig)
