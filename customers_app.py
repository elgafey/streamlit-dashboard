import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from weasyprint import HTML
import io

# 1. Page Configuration for a Portal look
st.set_page_config(page_title="Suhul Albeeah | Management Portal", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # Standard Audit Accounts
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Portal Sync Error: {e}")
        return pd.DataFrame()

def generate_pdf_report(df_filtered, partner):
    """Clean Professional PDF for Executives"""
    html_content = f"""
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 1cm; }}
            body {{ font-family: 'Arial', sans-serif; direction: rtl; color: #333; }}
            .header {{ border-bottom: 3px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }}
            .company-name {{ color: #1a237e; font-size: 22px; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #1a237e; color: white; padding: 10px; border: 1px solid #ddd; font-size: 12px; }}
            td {{ padding: 8px; border: 1px solid #ddd; text-align: center; font-size: 11px; }}
            .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-name">Suhul Albeeah Co. - Management Portal</div>
            <div style="font-size: 12px;">Partner Statement: {partner}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Date</th><th>Description</th><th>Debit</th><th>Credit</th><th>Balance</th>
                </tr>
            </thead>
            <tbody>
    """
    rb = 0
    for _, row in df_filtered.sort_values('date').iterrows():
        rb += row['net']
        html_content += f"<tr><td>{row['date'].strftime('%Y-%m-%d')}</td><td>{row['move_name']}</td><td>{row['debit']:,.2f}</td><td>{row['credit']:,.2f}</td><td>{rb:,.2f}</td></tr>"
    
    html_content += f"</tbody></table><div style='margin-top:20px; text-align:left;'>Final Balance: <strong>{rb:,.2f}</strong></div></body></html>"
    return HTML(string=html_content).write_pdf()

# --- Portal Core ---
df = load_data()

if not df.empty:
    st.title("🏛️ Management Financial Portal")
    
    # Overview Metrics (Managers love these)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Receivables (All)", f"{df['debit'].sum():,.2f}")
    m2.metric("Total Collections (All)", f"{df['credit'].sum():,.2f}")
    m3.metric("Outstanding Balance", f"{df['net'].sum():,.2f}")

    tab1, tab2 = st.tabs(["🔍 Partner Audit (Interactive)", "📊 Executive Summary"])

    with tab1:
        st.subheader("Interactive Partner Ledger")
        
        # Selection Bars
        col_p, col_d = st.columns([2, 1])
        with col_p:
            selected_p = st.selectbox("Select Partner Account:", ["-- Select Partner --"] + sorted(df['partner_id'].unique().tolist()))
        with col_d:
            d_range = st.date_input("Report Period:", [df['date'].min(), df['date'].max()])

        if selected_p != "-- Select Partner --":
            p_data = df[(df['partner_id'] == selected_p) & (df['date'] >= pd.Timestamp(d_range[0])) & (df['date'] <= pd.Timestamp(d_range[1]))].copy().sort_values('date')
            
            if not p_data.empty:
                p_data['Running Balance'] = p_data['net'].cumsum()
                
                # AgGrid for Drill-down
                gb = GridOptionsBuilder.from_dataframe(p_data[['date', 'move_name', 'debit', 'credit', 'Running Balance']])
                gb.configure_selection('single', use_checkbox=True)
                gb.configure_pagination(paginationPageSize=10)
                grid_response = AgGrid(p_data, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, theme='alpine', fit_columns_on_grid_load=True)

                # Drill-down Action
                selected_rows = grid_response['selected_rows']
                if selected_rows is not None and not selected_rows.empty:
                    move_id = selected_rows.iloc[0]['move_name']
                    st.success(f"Audit View: Entry details for `{move_id}`")
                    st.table(df[df['move_name'] == move_id][['date', 'account_code', 'debit', 'credit']])

                # Quick Actions for Managers
                if st.button("🖨️ Export Executive PDF"):
                    pdf = generate_pdf_report(p_data, selected_p)
                    st.download_button("📥 Download Report", pdf, f"Report_{selected_p}.pdf")
            else:
                st.warning("No data found for this period.")

    with tab2:
        st.subheader("Partner Aging / Balances")
        summary = df.groupby('partner_id')['net'].sum().reset_index().rename(columns={'net': 'Current Balance'})
        st.dataframe(summary.sort_values('Current Balance', ascending=False), use_container_width=True)

else:
    st.error("Connection lost or no data available.")
