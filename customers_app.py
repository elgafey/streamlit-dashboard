import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# 1. إعدادات الصفحة الأساسية
st.set_page_config(page_title="Suhul Albeeah Financial System", layout="wide")

def clean_text(text):
    """تنظيف النصوص لتجنب مشاكل الـ Unicode في الـ PDF"""
    t = str(text).strip()
    if not t or t.lower() in ['none', 'nan', 'false']: return "Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_data():
    """تحميل وتنظيف البيانات من المصدر"""
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        
        # معالجة التواريخ لضمان دقة التقارير
        df['date'] = df['date'].str.split(' GMT').str[0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # تحويل القيم المالية
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        
        # تنظيف أسماء العملاء لضمان المطابقة
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

def generate_pdf(df_all, selected_partners):
    """توليد ملف PDF احترافي بهيدر ثابت"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # الهيدر الإنجليزي لتجنب الـ Encoding Error
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 8, "SUHUL ALBEEAH", ln=True, align='L')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 5, "Environmental Plains for Raw Material Recycling", ln=True, align='L')
        pdf.cell(0, 5, "VAT Number: 300451393600003", ln=True, align='L')
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 10, f"Customer: {clean_text(partner)}", ln=True)
        
        # أعمدة الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        cols = [("Date", 30), ("Move Name", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in cols: pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            d = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, d, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
            
    return bytes(pdf.output(dest='S'))

# --- Main Logic ---
df = load_data()

if not df.empty:
    # Sidebar: Global Year Filter
    st.sidebar.title("Fiscal Filters")
    available_years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year for Trial Balance:", available_years)
    
    tab1, tab2 = st.tabs(["📑 Customer Ledger", "⚖️ Trial Balance"])

    # --- Tab 1: Customer Ledger ---
    with tab1:
        st.subheader("Individual Statements")
        all_partners = sorted(df['partner_id'].unique().tolist())
        
        col_s1, col_s2 = st.columns([1, 3])
        with col_s1:
            select_all = st.checkbox("Select All (For PDF)")
        
        if select_all:
            selected = all_partners
        else:
            selected = st.multiselect("Pick Target Customers:", options=all_partners)

        if selected:
            # Metrics Dashboard
            stats_df = df[df['partner_id'].isin(selected)]
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Debit", f"{stats_df['debit'].sum():,.2f}")
            m2.metric("Total Credit", f"{stats_df['credit'].sum():,.2f}")
            m3.metric("Net Balance", f"{stats_df['net'].sum():,.2f}")
            
            # PDF Generation in Sidebar
            if st.sidebar.button(f"Generate PDF ({len(selected)} Customers)"):
                with st.spinner("Processing PDF..."):
                    st.session_state['pdf_blob'] = generate_pdf(df, selected)
            
            if 'pdf_blob' in st.session_state:
                st.sidebar.download_button("📥 Download Report", st.session_state['pdf_blob'], "Suhul_Ledger.pdf")

            # Preview (Limited to 3 to prevent black screen)
            for p in selected[:3]:
                with st.expander(f"Statement: {p}"):
                    p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                    p_df['Running_Balance'] = p_df['net'].cumsum()
                    st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].tail(15))

    # --- Tab 2: Trial Balance ( ensures ALL customers appear) ---
    with tab2:
        st.subheader(f"Trial Balance - Fiscal Year {selected_year}")
        
        # ضمان شمولية جميع العملاء بالـ Left Merge
        all_entities = df[['partner_id']].drop_duplicates()
        
        # 1. Initial Balance (Before selected year)
        init_df = df[df['date'].dt.year < selected_year].groupby('partner_id')['net'].sum().reset_index()
        init_df.columns = ['partner_id', 'Initial Balance']
        
        # 2. Period Balance (Within selected year)
        peri_df = df[df['date'].dt.year == selected_year].groupby('partner_id')['net'].sum().reset_index()
        peri_df.columns = ['partner_id', 'Period Balance']
        
        # Merge all together
        tb_df = pd.merge(all_entities, init_df, on='partner_id', how='left')
        tb_df = pd.merge(tb_df, peri_df, on='partner_id', how='left')
        
        tb_df[['Initial Balance', 'Period Balance']] = tb_df[['Initial Balance', 'Period Balance']].fillna(0)
        tb_df['Ending Balance'] = tb_df['Initial Balance'] + tb_df['Period Balance']
        
        # Format and Display
        st.dataframe(tb_df.sort_values(by='Ending Balance', ascending=False).style.format({
            'Initial Balance': '{:,.2f}',
            'Period Balance': '{:,.2f}',
            'Ending Balance': '{:,.2f}'
        }), use_container_width=True)
        
        # Total Summary for TB
        st.divider()
        t1, t2, t3 = st.columns(3)
        t1.metric("Total Opening", f"{tb_df['Initial Balance'].sum():,.2f}")
        t2.metric("Total Period Change", f"{tb_df['Period Balance'].sum():,.2f}")
        t3.metric("Total Final Value", f"{tb_df['Ending Balance'].sum():,.2f}")

else:
    st.warning("No data found in source file.")
