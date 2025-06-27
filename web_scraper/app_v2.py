import streamlit as st
import psycopg2
import pandas as pd

# ---------------------
# 数据库连接配置
# ---------------------
DB_CONFIG = {
    "host": "localhost",
    "database": "independent_enrollment",
    "user": "postgres",
    "password": "123456",
    "port": 5432
}

# ---------------------
# 读取数据函数
# ---------------------
@st.cache_data(show_spinner=True)
def load_data():
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql("""
        SELECT
            si.id AS school_id,
            si.name AS 学校名称,
            si.province AS 省份,
            si.type AS 性质,
            si.category AS 院校类型,
            s.exam_type AS 考试类型,
            s.year AS 年份,
            s.values AS 分数详情
        FROM school_info si
        JOIN score s ON si.id = s.school_id
        ORDER BY si.name, s.exam_type
    """, conn)
    conn.close()
    return df

# ---------------------
# 页面配置
# ---------------------
st.set_page_config(page_title="高职单招分数线嵌套展示", layout="wide")
st.title("📊 高职单招院校分数线（嵌套展示）")

df = load_data()

# ---------------------
# 筛选器（侧边栏）
# ---------------------
with st.sidebar:
    st.header("筛选条件")
    provinces = st.multiselect("选择省份", options=sorted(df["省份"].dropna().unique()))
    categories = st.multiselect("选择学校类型", options=sorted(df["院校类型"].dropna().unique()))

# 应用筛选
filtered_df = df.copy()
if provinces:
    filtered_df = filtered_df[filtered_df["省份"].isin(provinces)]
if categories:
    filtered_df = filtered_df[filtered_df["院校类型"].isin(categories)]

# ---------------------
# 按学校分组并嵌套展示
# ---------------------
grouped = filtered_df.groupby(["school_id", "学校名称", "省份", "性质", "院校类型"])

for (sid, name, province, nature, category), group in grouped:
    with st.expander(f"🏫 {name} | {province} | {nature} | {category}", expanded=False):
        score_df = pd.DataFrame([
            {
                "考试类型": row["考试类型"],
                "年份": row["年份"],
                "投档最低分": row["分数详情"][2] if len(row["分数详情"]) > 2 else None,
                "职业技能": row["分数详情"][3] if len(row["分数详情"]) > 3 else None,
                "语文": row["分数详情"][4] if len(row["分数详情"]) > 4 else None,
                "数学": row["分数详情"][5] if len(row["分数详情"]) > 5 else None,
                "专业基础": row["分数详情"][6] if len(row["分数详情"]) > 6 else None,
                "职业适应性测试": row["分数详情"][7] if len(row["分数详情"]) > 7 else None,
            }
            for _, row in group.iterrows()
        ])
        st.table(score_df)
