import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# 1. إعدادات الصفحة المتقدمة
st.set_page_config(page_title="Suhul Albeeah | Financial Portal", layout="wide")

# تصميم CSS مخصص لتحسين شكل الجداول والتابات
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { border: none !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        # فلترة الحسابات المستهدفة للمطابقة مع أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def generate_pdf(df_filtered, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 8, "SUHUL ALBEEAH", ln=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 5, "VAT: 300451393600003", ln=True); pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 16); pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 11); pdf.cell(0, 10, f"Customer: {partner}", ln=True); pdf.ln(5)
        # الجدول
        pdf.set_font("Helvetica", 'B', 9); pdf.set_fill_color(230, 230, 230)
        for h, w in [("Date", 30), ("Move", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]:
            pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln(); pdf.set_font("Helvetica", '', 9)
        for _, r in cust_df.iterrows():
            pdf.cell(30, 8, r['date'].strftime('%Y-%m-%d'), 1)
            pdf.cell(70, 8, str(r['move_name'])[:35], 1)
            pdf.cell(30, 8, f"{r['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{r['Running_Balance']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output(dest='S'))

df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 Individual Ledger", "⚖️ Trial Balance"])

    # --- TAB 1: LEDGER (With Range Filter) ---
    with tab1:
        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            date_range = st.date_input("Select Statement Period:", 
                                     [df['date'].min(), df['date'].max()])
        with col_f2:
            all_p = sorted(df['partner_id'].unique().tolist())
            selected = st.multiselect("Select Customers:", options=all_p)
            select_all = st.checkbox("Select All Customers")
            if select_all: selected = all_p

        if selected:
            # فلترة البيانات بناءً على التاريخ المختار في التابة
            start_dt, end_dt = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            mask = (df['date'] >= start_dt) & (df['date'] <= end_dt) & (df['partner_id'].isin(selected))
            filtered_df = df[mask].copy()

            # إجماليات التابة
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Debit", f"{filtered_df['debit'].sum():,.2f}")
            m2.metric("Total Credit", f"{filtered_df['credit'].sum():,.2f}")
            m3.metric("Net Balance", f"{filtered_df['net'].sum():,.2f}")
            
            st.divider()
            if st.button("🚀 Prepare PDF Report"):
                st.session_state['pdf'] = generate_pdf(filtered_df, selected)
            if 'pdf' in st.session_state:
                st.download_button("📥 Download PDF", st.session_state['pdf'], "Ledger.pdf")

            for p in selected[:5]: # عرض أول 5 للمعاينة
                with st.expander(f"View Ledger: {p}"):
                    p_df = filtered_df[filtered_df['partner_id'] == p].sort_values('date')
                    p_df['Running_Balance'] = p_df['net'].cumsum()
                    st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)

    # --- TAB 2: TRIAL BALANCE (By Year) ---
    with tab2:
        col_t1, _ = st.columns([1, 3])
        with col_t1:
            years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
            sel_year = st.selectbox("Fiscal Year:", years)

        # حسابات الميزان
        entities = df[['partner_id']].drop_duplicates()
        init = df[df['date'].dt.year < sel_year].groupby('partner_id')['net'].sum().reset_index(name='Initial')
        peri = df[df['date'].dt.year == sel_year].groupby('partner_id')['net'].sum().reset_index(name='Period')
        
        tb = pd.merge(entities, init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['Ending'] = tb['Initial'] + tb['Period']
        
        # عرض الميزان بشكل محسن
        st.subheader(f"Trial Balance - Year {sel_year}")
        st.dataframe(tb.sort_values('Ending', ascending=False).style.format("{:,.2f}", subset=['Initial', 'Period', 'Ending']), 
                     use_container_width=True, height=500)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Opening", f"{tb['Initial'].sum():,.2f}")
        c2.metric("Total Period Change", f"{tb['Period'].sum():,.2f}")
        c3.metric("Global Final Balance", f"{tb['Ending'].sum():,.2f}")

else: st.error("No Data Loaded.")
