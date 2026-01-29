import streamlit as st
import pandas as pd
from weasyprint import HTML
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Suhul Albeeah | Financial Reports", layout="wide")

@st.cache_data 
def load_data():
    try:
        # تحميل البيانات من الرابط الخاص بك
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        # تنظيف التاريخ
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # فلترة الحسابات لمطابقة أرقام أودو (الأكواد المطلوبة)
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        # تحويل الأرقام لضمان الدقة
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        return pd.DataFrame()

def generate_pdf_multi_page(df_filtered, selected_partners):
    """توليد PDF احترافي: كل عميل في صفحة مستقلة مع دعم كامل للعربية"""
    
    html_content = """
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <style>
            @page { size: A4; margin: 1cm; }
            body { font-family: 'Arial', sans-serif; direction: rtl; color: #333; line-height: 1.4; }
            .page-container { page-break-after: always; border-bottom: 1px dashed #ccc; padding-bottom: 20px; }
            .header { border-bottom: 3px solid #1a237e; margin-bottom: 20px; padding-bottom: 10px; display: flex; justify-content: space-between; }
            .company-info { text-align: right; }
            .company-name { color: #1a237e; font-size: 22px; font-weight: bold; }
            .report-title { text-align: center; font-size: 20px; margin: 20px 0; background: #f5f5f5; padding: 10px; border-radius: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }
            th { background-color: #1a237e; color: white; padding: 10px; border: 1px solid #ddd; }
            td { padding: 8px; border: 1px solid #ddd; text-align: center; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .summary-box { margin-top: 20px; border: 2px solid #1a237e; width: 280px; float: left; padding: 15px; border-radius: 5px; background: #fff; }
            .summary-item { display: flex; justify-content: space-between; margin-bottom: 5px; }
            .final-balance { font-size: 16px; font-weight: bold; border-top: 1px solid #1a237e; padding-top: 5px; margin-top: 5px; }
            .clearfix { clear: both; }
            .footer { text-align: center; font-size: 9px; color: #888; margin-top: 30px; }
        </style>
    </head>
    <body>
    """

    for partner in selected_partners:
        # فلترة بيانات العميل الحالي فقط
        cust_df = df_filtered[df_filtered['partner_id'] == partner].sort_values('date')
        if cust_df.empty: continue
        
        running_balance = 0
        html_content += f"""
        <div class="page-container">
            <div class="header">
                <div class="company-info">
                    <div class="company-name">شركة سهول البيئة لتدوير المواد الأولية</div>
                    <div>الرقم الضريبي: 300451393600003</div>
                </div>
            </div>

            <div class="report-title">كشف حساب عميل (Partner Ledger)</div>
            
            <div style="font-size: 14px; margin-bottom: 20px;">
                <strong>اسم العميل:</strong> {partner}<br>
                <strong>تاريخ الاستخراج:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d')}
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width: 15%;">التاريخ</th>
                        <th style="width: 45%;">البيان / مرجع القيد</th>
                        <th style="width: 12%;">مدين</th>
                        <th style="width: 12%;">دائن</th>
                        <th style="width: 16%;">الرصيد الجاري</th>
                    </tr>
                </thead>
                <tbody>
        """

        for _, row in cust_df.iterrows():
            running_balance += row['net']
            html_content += f"""
                    <tr>
                        <td>{row['date'].strftime('%Y-%m-%d')}</td>
                        <td style="text-align: right;">{row['move_name']}</td>
                        <td>{row['debit']:,.2f}</td>
                        <td>{row['credit']:,.2f}</td>
                        <td style="font-weight: bold;">{running_balance:,.2f}</td>
                    </tr>
            """
        
        html_content += f"""
                </tbody>
            </table>

            <div class="summary-box">
                <div class="summary-item">
                    <span>إجمالي المدين:</span> <strong>{cust_df['debit'].sum():,.2f}</strong>
                </div>
                <div class="summary-item">
                    <span>إجمالي الدائن:</span> <strong>{cust_df['credit'].sum():,.2f}</strong>
                </div>
                <div class="summary-item final-balance">
                    <span>صافي الرصيد الحالي:</span> <strong>{cust_df['net'].sum():,.2f}</strong>
                </div>
            </div>
            <div class="clearfix"></div>
            <div class="footer">تعتبر هذه الصفحة كشف حساب رسمي لشركة سهول البيئة - صفحة مستقلة للعميل: {partner}</div>
        </div>
        """

    html_content += "</body></html>"
    return HTML(string=html_content).write_pdf()

# --- واجهة التطبيق ---
df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 كشوف الحسابات التفصيلية", "⚖️ ميزان المراجعة"])
    
    with tab1:
        st.markdown("### 📊 استخراج تقارير العملاء (Odoo Style)")
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            # فلتر تاريخ مستقل للتابة الأولى
            d_range = st.date_input("حدد الفترة الزمنية:", [df['date'].min(), df['date'].max()], key="date_range_p")
        with col_b:
            partners_list = sorted(df['partner_id'].unique().tolist())
            selected_customers = st.multiselect("اختر العملاء المطلوب طباعتهم:", options=partners_list)
            if st.checkbox("اختيار جميع العملاء المتاحين"):
                selected_customers = partners_list

        if selected_customers:
            # فلترة البيانات بناءً على الاختيارات
            final_mask = (df['date'] >= pd.Timestamp(d_range[0])) & \
                         (df['date'] <= pd.Timestamp(d_range[1])) & \
                         (df['partner_id'].isin(selected_customers))
            
            working_df = df[final_mask].copy()
            
            st.info(f"تم العثور على {len(working_df)} حركات مالية للعملاء المختارين.")

            if st.button("🚀 إصدار ملف PDF مجمع (كل عميل في صفحة)"):
                with st.spinner("جاري معالجة الصفحات وتنسيق اللغة العربية..."):
                    try:
                        pdf_file = generate_pdf_multi_page(working_df, selected_customers)
                        st.download_button(
                            label="📥 تحميل ملف PDF الجاهز",
                            data=pdf_file,
                            file_name=f"Suhul_Albeeah_Reports.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"خطأ في محرك الطباعة: {e}")
                        st.warning("تأكد من إعداد ملف packages.txt في مستودع GitHub.")

    with tab2:
        st.markdown("### ⚖️ ميزان المراجعة السنوي")
        available_years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        selected_year = st.selectbox("اختر السنة المالية:", available_years, key="year_selector")
        
        # حساب الميزان (افتتاحي، حركة، ختامي)
        opening = df[df['date'].dt.year < selected_year].groupby('partner_id')['net'].sum().reset_index(name='الرصيد الافتتاحي')
        movement = df[df['date'].dt.year == selected_year].groupby('partner_id')['net'].sum().reset_index(name='حركة السنة')
        
        trial_balance = pd.merge(df[['partner_id']].drop_duplicates(), opening, on='partner_id', how='left')
        trial_balance = pd.merge(trial_balance, movement, on='partner_id', how='left').fillna(0)
        trial_balance['الرصيد الختامي'] = trial_balance['الرصيد الافتتاحي'] + trial_balance['حركة السنة']
        
        # عرض الجدول بتنسيق مالي
        st.dataframe(
            trial_balance.sort_values('الرصيد الختامي', ascending=False)
            .style.format("{:,.2f}", subset=['الرصيد الافتتاحي', 'حركة السنة', 'الرصيد الختامي']),
            use_container_width=True
        )
else:
    st.warning("برجاء التأكد من توفر البيانات في الرابط المصدر.")
