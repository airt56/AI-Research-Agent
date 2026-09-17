import os
import json
import random
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from openai import OpenAI

HISTORY_FILE = "papers_history.json"

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_API_BASE = os.environ["DEEPSEEK_API_BASE"]

SENDER = os.environ["SENDER"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
RECEIVER = os.environ["RECEIVER"]
RECEIVER_2 = os.environ["RECEIVER_2"]

KEYWORDS = [
    "interactive art",
    "human computer interaction",
    "human AI interaction",
    "spatial computing",
    "computational design",
    "generative design",
    "AI architecture",
    "immersive environment",
    "creative AI",
    "digital twin"
]


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {"papers": []}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_papers():
    papers = []
    for keyword in KEYWORDS:
        response = requests.get(
            "https://api.openalex.org/works",
            params={
                "search": keyword,
                "filter": "from_publication_date:2024-01-01",
                "sort": "cited_by_count:desc",
                "per-page": 10
            },
            timeout=30
        )

        for item in response.json().get("results", []):
            papers.append({
                "title": item.get("title", ""),
                "doi": item.get("doi", ""),
                "year": item.get("publication_year", ""),
                "citation": item.get("cited_by_count", 0)
            })

    return papers


def remove_duplicate(papers, history):
    old = history.get("papers", [])
    result = []

    for paper in papers:
        key = paper["doi"] or paper["title"]
        if key not in old:
            result.append(paper)

    return result[:5]


def analyze_with_deepseek(papers):
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_BASE
    )

    paper_text = "\n\n".join(
        [
            f"Title: {p['title']}\nDOI: {p['doi']}"
            for p in papers
        ]
    )

    prompt = f"""
你是一名AI、交互艺术、空间设计方向科研助手。

我的研究方向：
AI + TouchDesigner + Interactive Art + Spatial Design + HCI + Computational Design

请分析以下论文。

每篇输出：

1. 英文标题 + 中文标题
2. 期刊/会议名称、SCI/SSCI/AHCI/顶会信息
3. 第一作者、单位、研究简介
4. 通讯作者、单位、身份简介
5. 摘要中文
6. 研究方法
7. 研究亮点
8. 与我的研究关系
9. 潜在SCI选题启发

论文：

{paper_text}

请使用中文。
"""

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def send_email(content):
    messages = [
        "🐷 超级贝猪，今天也要认真学习哦！每天一点积累，都会成为未来研究的力量。",
        "🐷 超级贝猪，新的论文已经准备好啦，坚持阅读，坚持成长！",
        "🐷 超级贝猪，今天也一起探索新的知识吧，说不定会发现新的研究灵感。"
    ]

    body = random.choice(messages) + "\n\n" + content

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header("今日论文分析", "utf-8")
    msg["From"] = SENDER
    msg["To"] = RECEIVER + "," + RECEIVER_2

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(SENDER, SENDER_PASSWORD)
    server.sendmail(
        SENDER,
        [RECEIVER, RECEIVER_2],
        msg.as_string()
    )
    server.quit()


if __name__ == "__main__":

    history = load_history()

    papers = remove_duplicate(
        get_papers(),
        history
    )

    if not papers:
        raise Exception("No new papers found")

    result = analyze_with_deepseek(papers)

    send_email(result)

    for paper in papers:
        history["papers"].append(
            paper["doi"] or paper["title"]
        )

    save_history(history)

    print("Email sent successfully")
