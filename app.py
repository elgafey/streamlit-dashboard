import streamlit as st
import pandas as pd
from io import BytesIO

# إعدادات الصفحة
st.set_page_config(page_title="Raw Material Report", layout="wide")

# -----------------------------
# دالة تحميل البيانات من GitHub
# -----------------------------
@st.cache_data 
def load_data():
    # الرابط الخاص بملفك على GitHub
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
    
    # قراءة الملف مع دعم اللغة العربية
    df = pd.read_csv(url, encoding='utf-8')
    
    # تنظيف عمود التاريخ: 
    # التنسيق القادم هو (Sun Jun 29 2025 00:00:00 GMT+0300)
    # سنقوم بقص أول 15 حرفاً فقط (مثل: Sun Jun 29 2025) ليكون قابلاً للتحويل
    df['date_cleaned'] = df['date'].astype(str).str[:15]
    
    # تحويل النص المنظف إلى تاريخ حقيقي
    df["date_final"] = pd.to_datetime(df['date_cleaned'], errors="coerce")
    
    # حذف أي صفوف فشل تحويل تاريخها (تجنب خطأ NaTType)
    df = df.dropna(subset=["date_final"])
    
    # تحويل العمود لنوع date البسيط المتوافق مع فلاتر Streamlit
    df["date"] = df["date_final"].dt.date
    return df

try:
    # تحميل البيانات
    df_raw = load_data()
    df = df_raw.copy()

    # -----------------------------
    # Sidebar Filters (الفلاتر الجانبية)
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    # 1. فلتر نطاق التاريخ
    min_date = df["date"].min()
    max_date = df["date"].max()

    date_input = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 2. فلتر المنتجات (Multiselect)
    available_products = sorted(df["product_name"].unique().tolist())
    selected_products = st.sidebar.multiselect(
        "Select Products",
        options=available_products,
        default=available_products # افتراضياً اختيار الكل
    )

    # معالجة اختيار التاريخ لضمان عدم حدوث خطأ أثناء الاختيار
    if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
        start_date, end_date = date_input
    else:
        # في حالة اختيار يوم واحد فقط
        start_date = end_date = date_input[0] if isinstance(date_input, (list, tuple)) else date_input

    # -----------------------------
    # تطبيق الفلترة النهائية
    # -----------------------------
    mask = (
        (df["date"] >= start_date) & 
        (df["date"] <= end_date) & 
        (df["product_name"].isin(selected_products))
    )
    df_filtered = df.loc[mask]

    # -----------------------------
    # الواجهة الرئيسية (Streamlit UI)
    # -----------------------------
    st.title("📦 Raw Material Daily Report")
    
    # عرض الإحصائيات (Metrics)
    if not df_filtered.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(df_filtered))
        with col2:
            # حساب إجمالي الكمية المستخدمة
            if "raw_qty_used" in df_filtered.columns:
                total_qty = df_filtered["raw_qty_used"].sum()
                st.metric("Total Qty Used", f"{total_qty:,.2f}")
        with col3:
            # حساب إجمالي القيمة المادية
            if "raw_value_used" in df_filtered.columns:
                total_val = df_filtered["raw_value_used"].sum()
                st.metric("Total Value", f"{total_val:,.2f}")

        st.divider()

        # عرض جدول البيانات
        st.subheader("📊 Data Details")
        # إخفاء أعمدة التنظيف التقنية عند العرض
        display_cols = [c for c in df_filtered.columns if c not in ['date_cleaned', 'date_final']]
        st.dataframe(df_filtered[display_cols], use_container_width=True)

        # -----------------------------
        # تصدير البيانات إلى Excel
        # -----------------------------
        def to_excel(df_to_download):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_to_download.to_excel(writer, index=False, sheet_name="Report")
            return output.getvalue()

        st.sidebar.divider()
        excel_file = to_excel(df_filtered[display_cols])

        st.sidebar.download_button(
            label="⬇️ Download Filtered Data (Excel)",
            data=excel_file,
            file_name=f"raw_material_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ لا توجد بيانات تطابق الفلاتر المختارة.")

except Exception as e:
    st.error(f"❌ حدث خطأ غير متوقع: {e}")
    st.info("تأكد من أن الملف على GitHub متاح وأن أسماء الأعمدة صحيحة.")
