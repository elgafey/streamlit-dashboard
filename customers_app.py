import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Suhul Albeeah - Financial System", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = df['date'].str.split(' GMT').str[0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        return df
    except:
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- Sidebar Controls ---
    st.sidebar.title("Global Filters")
    # فلتر السنين
    available_years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Fiscal Year:", available_years)
    
    # --- Tabs System ---
    tab1, tab2 = st.tabs(["📑 Customer Ledger", "⚖️ Trial Balance"])

    # --- Tab 1: Customer Ledger (القديم بتاعنا) ---
    with tab1:
        st.subheader("Individual Customer Statements")
        all_p = sorted(df['partner_id'].unique().tolist())
        select_all = st.checkbox("Select All for PDF")
        selected = all_p if select_all else st.multiselect("Pick Customers:", options=all_p)
        
        if selected:
            # Dashboard Metrics
            stats_df = df[df['partner_id'].isin(selected)]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Debit", f"{stats_df['debit'].sum():,.2f}")
            c2.metric("Total Credit", f"{stats_df['credit'].sum():,.2f}")
            c3.metric("Net Exposure", f"{stats_df['net'].sum():,.2f}")
            
            # Preview (First 3)
            for p in selected[:3]:
                with st.expander(f"Ledger: {p}"):
                    p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                    p_df['Running_Balance'] = p_df['net'].cumsum()
                    st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])

    # --- Tab 2: Trial Balance (الجديد) ---
    with tab2:
        st.subheader(f"Customers Trial Balance - Year {selected_year}")
        
        # 1. Initial Balance: كل الحركات قبل السنة المختارة
        initial_mask = df['date'].dt.year < selected_year
        initial_df = df[initial_mask].groupby('partner_id')['net'].sum().reset_index()
        initial_df.columns = ['partner_id', 'Initial Balance']
        
        # 2. Period Balance: كل الحركات داخل السنة المختارة
        period_mask = df['date'].dt.year == selected_year
        period_df = df[period_mask].groupby('partner_id')['net'].sum().reset_index()
        period_df.columns = ['partner_id', 'Period Balance']
        
        # دمج البيانات
        trial_df = pd.merge(df[['partner_id']].drop_duplicates(), initial_df, on='partner_id', how='left')
        trial_df = pd.merge(trial_df, period_df, on='partner_id', how='left')
        
        # ملء القيم الفارغة بالأصفار وحساب الـ Ending Balance
        trial_df = trial_df.fillna(0)
        trial_df['Ending Balance'] = trial_df['Initial Balance'] + trial_df['Period Balance']
        
        # تنسيق الأرقام للعرض
        display_trial = trial_df.sort_values(by='Ending Balance', ascending=False)
        
        # عرض الإجماليات تحت التابة
        t1, t2, t3 = st.columns(3)
        t1.metric("Total Initial", f"{trial_df['Initial Balance'].sum():,.2f}")
        t2.metric("Total Period", f"{trial_df['Period Balance'].sum():,.2f}")
        t3.metric("Total Ending", f"{trial_df['Ending Balance'].sum():,.2f}")
        
        st.dataframe(display_trial.style.format({
            'Initial Balance': '{:,.2f}',
            'Period Balance': '{:,.2f}',
            'Ending Balance': '{:,.2f}'
        }), use_container_width=True)

        # زر تحميل الـ Trial Balance كـ Excel
        csv = trial_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Trial Balance to CSV", csv, f"Trial_Balance_{selected_year}.csv", "text/csv")

else:
    st.error("No data found.")
