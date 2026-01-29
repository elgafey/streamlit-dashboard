import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from weasyprint import HTML
import io

# 1. Page Configuration
st.set_page_config(page_title="Suhul Albeeah | Audit Pro", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # Filter for consistency with Odoo
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

def generate_pdf_multi_page(df_filtered, selected_partners):
    """PDF Engine for professional printing"""
    html_content = """<html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
    @page { size: A4; margin: 1cm; }
    body { font-family: 'Arial', sans-serif; direction: rtl; color: #333; }
    .page-container { page-break-after: always; }
    .header { border-bottom: 3px solid #1a237e; margin-bottom: 20px; padding-bottom: 10px; }
    .company-name { color: #1a237e; font-size: 22px; font-weight: bold; }
    .report-title { text-align: center; font-size: 20px; margin: 20px 0; background: #f5f5f5; padding: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }
    th { background-color: #1a237e; color: white; padding: 10px; border: 1px solid #ddd; }
    td { padding: 8px; border: 1px solid #ddd; text-align: center; }
    .summary-box { margin-top: 20px; border: 2px solid #1a237e; width: 280px; float: left; padding: 15px; }
    .clearfix { clear: both; }</style></head><body>"""
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].sort_values('date')
        if cust_df.empty: continue
        rb = 0
        html_content += f"""<div class="page-container"><div class="header"><div class="company-name">شركة سهول البيئة لتدوير المواد الأولية</div></div>
        <div class="report-title">Partner Ledger</div><p>Partner: {partner}</p><table><thead><tr>
        <th>Date</th><th>Description</th><th>Debit</th><th>Credit</th><th>Balance</th></tr></thead><tbody>"""
        for _, row in cust_df.iterrows():
            rb += row['net']
            html_content += f"<tr><td>{row['date'].strftime('%Y-%m-%d')}</td><td>{row['move_name']}</td><td>{row['debit']:,.2f}</td><td>{row['credit']:,.2f}</td><td>{rb:,.2f}</td></tr>"
        html_content += f"</tbody></table><div class='summary-box'>Final Balance: <strong>{rb:,.2f}</strong></div><div class='clearfix'></div></div>"
    
    html_content += "</body></html>"
    return HTML(string=html_content).write_pdf()

# --- Main Logic ---
df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 Interactive Audit", "⚖️ Trial Balance"])
    
    with tab1:
        st.title("Interactive Financial Audit")
        st.info("💡 Select a row using the checkbox to see full Journal Entry details.")

        c1, c2 = st.columns([1, 2])
        with c1:
            date_range = st.date_input("Period:", [df['date'].min(), df['date'].max()], key="audit_date")
        with c2:
            partners = sorted(df['partner_id'].unique().tolist())
            selected_partner = st.selectbox("Select Partner:", ["-- Select --"] + partners)

        if selected_partner != "-- Select --":
            mask = (df['date'] >= pd.Timestamp(date_range[0])) & \
                   (df['date'] <= pd.Timestamp(date_range[1])) & \
                   (df['partner_id'] == selected_partner)
            p_data = df[mask].copy().sort_values('date')
            
            if not p_data.empty:
                p_data['Running Balance'] = p_data['net'].cumsum()
                
                # AgGrid Configuration
                gb = GridOptionsBuilder.from_dataframe(p_data[['date', 'move_name', 'debit', 'credit', 'Running Balance']])
                gb.configure_selection('single', use_checkbox=True)
                gb.configure_pagination(paginationAutoPageSize=True)
                grid_options = gb.build()

                grid_response = AgGrid(
                    p_data,
                    gridOptions=grid_options,
                    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    theme='alpine'
                )

                # --- Fixed Drill-down Logic ---
                selected_rows = grid_response['selected_rows']
                
                # Check if selection exists and is not empty (Handles DataFrame return type)
                if selected_rows is not None and not selected_rows.empty:
                    # Using .iloc[0] to avoid KeyError in newer AgGrid/Pandas versions
                    move_id = selected_rows.iloc[0]['move_name']
                    st.markdown(f"### 🔍 Journal Entry Details: `{move_id}`")
                    
                    full_entry = df[df['move_name'] == move_id]
                    st.table(full_entry[['date', 'account_code', 'debit', 'credit']])
                
                st.divider()
                if st.button("🚀 Export Current View to PDF"):
                    with st.spinner("Generating PDF..."):
                        pdf_bytes = generate_pdf_multi_page(p_data, [selected_partner])
                        st.download_button("📥 Download PDF", pdf_bytes, f"{selected_partner}_Statement.pdf")
            else:
                st.warning("No transactions found for this period.")

    with tab2:
        st.title("Annual Trial Balance")
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        sel_year = st.selectbox("Select Year:", years)
        
        movement = df[df['date'].dt.year == sel_year].groupby('partner_id')['net'].sum().reset_index(name='Net Movement')
        st.dataframe(movement.sort_values('Net Movement', ascending=False), use_container_width=True)
