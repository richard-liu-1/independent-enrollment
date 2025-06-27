import requests
from bs4 import BeautifulSoup
import psycopg2
from urllib.parse import urljoin
from tqdm import tqdm
import time
import chardet

# PostgreSQL 连接配置
conn = psycopg2.connect(
    host="localhost",
    database="independent_enrollment",
    user="postgres",
    password="123456"
)
cursor = conn.cursor()

BASE_URL = "https://www.hbdzxx.com/news/2015/1.html"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 工具函数
def int_or_none(val):
    try:
        return int(val.strip())
    except:
        return None

# Step 1：解析主页面学校数据
def parse_main_table():
    res = requests.get(BASE_URL, headers=HEADERS)
    res.encoding = res.apparent_encoding  # 自动识别编码
    soup = BeautifulSoup(res.text, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')[1:]

    schools = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 9:
            continue
        school = {
            'name': cols[0].get_text(strip=True),
            'province': cols[1].get_text(strip=True),
            'type': cols[2].get_text(strip=True),
            'category': cols[3].get_text(strip=True),
            'phone': cols[4].get_text(strip=True),
            'address': cols[5].get_text(strip=True),
            'remarks': cols[6].get_text(strip=True),
            'dorm_link': urljoin(BASE_URL, cols[7].find('a')['href']) if cols[7].find('a') else None,
            'score_link': urljoin(BASE_URL, cols[8].find('a')['href']) if cols[8].find('a') else None
        }
        schools.append(school)
    return schools

# Step 2：插入主表数据
def insert_school(school):
    cursor.execute("""
        INSERT INTO school_info (name, province, type, category, phone, address, remarks, dorm_link, score_link)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        school['name'], school['province'], school['type'], school['category'],
        school['phone'], school['address'], school['remarks'],
        school['dorm_link'], school['score_link']
    ))
    return cursor.fetchone()[0]

# Step 3：解析子页面分数线表格
def parse_score_table(score_url, school_id, school_name):
    print(f"🔍 正在抓取分数线页面: {score_url}")
    try:
        res = requests.get(score_url, headers=HEADERS, timeout=10)

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        # res.encoding = res.apparent_encoding
        # soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table')
        if not table:
            print(f"⚠️  表格不存在: {score_url}")
            return

        rows = table.find_all('tr')
        if len(rows) < 2:
            print(f"⚠️  行数不足: {score_url}")
            return

        num_header_rows = 2 if len(rows[0].find_all(['td', 'th'])) < len(rows[1].find_all(['td', 'th'])) else 1
        headers = [td.get_text(strip=True) for td in rows[num_header_rows - 1].find_all(['td', 'th'])]
        score_type = 2 if '位次' in headers or '控制线' in headers else 1

        for row in rows[num_header_rows:]:
            cells = row.find_all('td')
            if len(cells) != len(headers):
                continue
            values = [c.get_text(strip=True).replace('\xa0', '') for c in cells]
            exam_type = values[0] if len(values) > 0 else None
            cursor.execute("""
                INSERT INTO score (
                    school_id, school_name, exam_type, year, type, headers, values, source_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                school_id, school_name, exam_type, 2025, score_type,
                headers, values, score_url
            ))

        print(f"✅ 插入完成：{school_name} 分数线 {len(rows) - num_header_rows} 条")
    except Exception as e:
        print(f"❌ 异常：{score_url} | {e}")

# Step 4：主逻辑
def main():
    schools = parse_main_table()
    print(f"📋 共解析出 {len(schools)} 所院校")
    for i, school in enumerate(tqdm(schools), 1):
        school_id = insert_school(school)
        print(f"\n🏫 插入第 {i} 所学校: {school['name']}")
        if school['score_link']:
            parse_score_table(school['score_link'], school_id, school['name'])
        time.sleep(1)
        conn.commit()

    cursor.close()
    conn.close()
    print("\n🎉 所有数据抓取完成！")

if __name__ == "__main__":
    main()
