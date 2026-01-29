import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from weasyprint import HTML
import io

# 1. Page Configuration
st.set_page_config(page_title="Suhul Albeeah | Interactive Audit", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # Filter for consistency
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

df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 Interactive Ledger", "⚖️ Trial Balance"])
    
    with tab1:
        st.title("Interactive Financial Audit")
        st.info("💡 Click on any row to see full Journal Entry details below.")

        col1, col2 = st.columns([1, 2])
        with col1:
            date_range = st.date_input("Period:", [df['date'].min(), df['date'].max()])
        with col2:
            partner_options = sorted(df['partner_id'].unique().tolist())
            selected_partner = st.selectbox("Select Partner to Audit:", ["-- Select --"] + partner_options)

        if selected_partner != "-- Select --":
            # Filter Data
            mask = (df['date'] >= pd.Timestamp(date_range[0])) & \
                   (df['date'] <= pd.Timestamp(date_range[1])) & \
                   (df['partner_id'] == selected_partner)
            p_data = df[mask].copy().sort_values('date')
            
            if not p_data.empty:
                # Calculate Running Balance
                p_data['Running Balance'] = p_data['net'].cumsum()
                
                # --- AgGrid Configuration ---
                gb = GridOptionsBuilder.from_dataframe(p_data[['date', 'move_name', 'debit', 'credit', 'Running Balance']])
                gb.configure_selection('single', use_checkbox=True) # تمكين الاختيار بالضغط
                gb.configure_pagination(paginationAutoPageSize=True) # تقسيم الصفحات آلياً
                gb.configure_column("Running Balance", type=["numericColumn","numberColumnFilter","customNumericFormat"], valueFormatter='x.toLocaleString()')
                grid_options = gb.build()

                # عرض الجدول التفاعلي
                grid_response = AgGrid(
                    p_data,
                    gridOptions=grid_options,
                    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=True,
                    theme='alpine' # شكل احترافي داكن أو فاتح
                )

                # --- Drill-down Logic ---
                selected_row = grid_response['selected_rows']
                
                if selected_row is not None and len(selected_row) > 0:
                    # استخراج رقم القيد من الصف المختار
                    move_id = selected_row[0]['move_name']
                    st.markdown(f"### 🔍 Journal Entry Details: `{move_id}`")
                    
                    # البحث عن القيد بالكامل في الداتا الأصلية
                    entry_details = df[df['move_name'] == move_id]
                    st.table(entry_details[['date', 'account_code', 'debit', 'credit']])
                else:
                    st.write("👆 Click a row to audit the entry.")
            else:
                st.warning("No data found for the selected period.")

    with tab2:
        st.title("Trial Balance")
        # ... (نفس كود الميزان السابق)
