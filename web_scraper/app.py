import streamlit as st
import psycopg2
import pandas as pd

# ---------------------
# 配置 PostgreSQL 连接
# ---------------------
# local
# DB_CONFIG = {
#     "host": "localhost",
#     "database": "independent_enrollment",
#     "user": "postgres",
#     "password": "123456",
#     "port": 5432
# }

# db_config = st.secrets["database"]

# ---------------------
# 从数据库中加载数据
# ---------------------
@st.cache_data(show_spinner=True)
def load_data():
    st.success("✅ start to load data")
    try:
        db = st.secrets["database"]
        conn = psycopg2.connect(
            host=db["host"],
            port=db["port"],
            user=db["user"],
            password=db["password"],
            database=db["database"]
        )
        st.success("✅ 成功连接 Supabase（通过 IPv4）")
        query = """
            SELECT
                si.name AS 学校名称,
                si.province AS 省份,
                si.type AS 性质,
                si.category AS 院校类型,
                s.exam_type AS 考试类型,
                s.year AS 年份,
                s.values[3] AS 投档最低分,
                s.values[4] AS 职业技能,
                s.values[5] AS 语文,
                s.values[6] AS 数学,
                s.values[7] AS 专业基础,
                s.values[8] AS 职业适应性测试
            FROM school_info si
            JOIN score s ON si.id = s.school_id
            ORDER BY si.name, s.exam_type;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ 数据库连接失败，请检查 Secrets 配置或 Supabase 网络：{e}")
        return pd.DataFrame()  # 空表，避免后续崩溃

# ---------------------
# Streamlit 页面布局
# ---------------------
st.set_page_config(page_title="高职单招分数线展示", layout="wide")
st.title("📊 高职单招院校分数线表格")

df = load_data()

if df.empty:
    st.warning("⚠️ 暂无数据，请检查连接或数据是否存在。")
    st.stop()

# ---------------------
# 筛选器（可选）
# ---------------------
with st.sidebar:
    st.header("筛选条件")
    provinces = st.multiselect("选择省份", options=sorted(df["省份"].dropna().unique()))
    exam_types = st.multiselect("选择考试类型", options=sorted(df["考试类型"].dropna().unique()))

# 应用筛选
filtered_df = df.copy()
if provinces:
    filtered_df = filtered_df[filtered_df["省份"].isin(provinces)]
if exam_types:
    filtered_df = filtered_df[filtered_df["考试类型"].isin(exam_types)]

st.dataframe(filtered_df, use_container_width=True)

# ---------------------
# 导出为 CSV
# ---------------------
st.download_button(
    label="📥 下载当前数据为 CSV",
    data=filtered_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="高职单招分数线.csv",
    mime="text/csv"
)
