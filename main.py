import os
import json
import random
import requests
import smtplib

from email.mime.text import MIMEText
from email.header import Header

from openai import OpenAI


# ==================================================
# Environment Variables
# ==================================================

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_API_BASE = os.environ["DEEPSEEK_API_BASE"]

SENDER = os.environ["SENDER"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]

RECEIVER = os.environ["RECEIVER"]
RECEIVER_2 = os.environ["RECEIVER_2"]


HISTORY_FILE = "papers_history.json"


# ==================================================
# Research Keywords
# ==================================================

KEYWORDS = [

    "AI architecture",

    "generative design",

    "computational design",

    "interactive architecture",

    "spatial computing",

    "human computer interaction",

    "immersive environment",

    "digital twin building",

    "smart building",

    "elderly architecture",

    "senior living design",

    "aging friendly architecture",

    "healthcare architecture",

    "environmental psychology",

    "human centered design",

    "creative AI"

]


# ==================================================
# History
# ==================================================

def load_history():

    if not os.path.exists(HISTORY_FILE):

        return {
            "papers": []
        }


    with open(
        HISTORY_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)



def save_history(history):

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )



# ==================================================
# OpenAlex Search
# ==================================================

def search_papers():


    papers = []


    for keyword in KEYWORDS:


        url = "https://api.openalex.org/works"


        params = {

            "search": keyword,

            "filter":
            "from_publication_date:2023-01-01",

            "sort":
            "cited_by_count:desc",

            "per-page":10
        }


        response = requests.get(

            url,

            params=params,

            timeout=30

        )


        data = response.json()


        for item in data.get(
            "results",
            []
        ):


            title = item.get(
                "title"
            )


            if not title:

                continue


            doi = item.get(
                "doi",
                ""
            )


            source = ""


            if item.get(
                "primary_location"
            ):


                location = item[
                    "primary_location"
                ]


                if location.get(
                    "source"
                ):


                    source = location[
                        "source"
                    ].get(
                        "display_name",
                        ""
                    )



            papers.append({

                "title":
                title,

                "doi":
                doi,

                "journal":
                source,

                "year":
                item.get(
                    "publication_year",
                    ""
                ),

                "citation":
                item.get(
                    "cited_by_count",
                    0
                )

            })


    return papers




# ==================================================
# Remove Duplicate
# ==================================================

def filter_history(
        papers,
        history
):


    old = history.get(
        "papers",
        []
    )


    result = []


    for paper in papers:


        key = (
            paper["doi"]
            if paper["doi"]
            else paper["title"]
        )


        if key not in old:


            result.append(
                paper
            )



    return result[:5]




# ==================================================
# DeepSeek Analysis
# ==================================================

def deepseek_analysis(
        papers
):


    client = OpenAI(

        api_key=
        DEEPSEEK_API_KEY,

        base_url=
        DEEPSEEK_API_BASE

    )



    paper_text = ""


    for i,p in enumerate(papers):


        paper_text += f"""

论文{i+1}

标题:
{p['title']}

期刊:
{p['journal']}

年份:
{p['year']}

DOI:
{p['doi']}

"""


    prompt = f"""

你是一名建筑环境、设计学和人工智能方向科研助手。


我的研究方向：

AI + TouchDesigner + Interactive Art + Spatial Design + Architecture + 老年建筑 + Human-centered Design


请按照以下格式分析论文：

# 🐷超级贝猪每日论文分析


## 英文标题（中文标题）


期刊/会议：
级别：
SCI / SSCI / AHCI / Top Conference

分区：
Q1/Q2（如果无法确认请说明）


DOI：
提供完整链接：

https://doi.org/


第一作者：
姓名（单位）

简介：
一句话介绍研究方向。


通讯作者：
姓名（单位）

简介：
一句话介绍身份和研究领域。


论文内容：

用一段话总结：

- 研究背景
- 研究问题
- 方法
- 主要发现


研究亮点：

- 3点以内


对我研究的启发：

结合：

AI
TouchDesigner
Interactive Art
Spatial Design
Architecture
老年建筑
人因评价


说明：

- 可以借鉴的方法
- 可以迁移的技术
- 潜在SCI研究方向



论文：

{paper_text}


请中文输出。

每篇论文之间使用：

==================================================

进行分隔。

"""


    response = client.chat.completions.create(

        model="deepseek-v4-flash",

        messages=[

            {

                "role":
                "user",

                "content":
                prompt

            }

        ]

    )


    return response.choices[0].message.content




# ==================================================
# Email
# ==================================================

def send_email(
        content
):


    greetings = [

        "🐷超级贝猪，今天也要认真学习哦！每天一点积累，都会成为未来研究的重要力量。",

        "🐷超级贝猪，今天的新论文已经送达啦，希望里面有新的研究灵感！",

        "🐷超级贝猪，坚持阅读优秀论文，未来的创新可能就在今天的积累里。",

        "🐷超级贝猪，科研学习时间到啦，一起探索新的知识吧！"

    ]


    message = random.choice(
        greetings
    )


    body = message + "\n\n" + content



    email = MIMEText(

        body,

        "plain",

        "utf-8"

    )


    email["Subject"] = Header(

        "🐷超级贝猪每日论文分析",

        "utf-8"

    )


    email["From"] = SENDER


    email["To"] = (

        RECEIVER
        +
        ","
        +
        RECEIVER_2

    )



    server = smtplib.SMTP_SSL(

        "smtp.qq.com",

        465

    )


    server.login(

        SENDER,

        SENDER_PASSWORD

    )


    server.sendmail(

        SENDER,

        [
            RECEIVER,
            RECEIVER_2
        ],

        email.as_string()

    )


    server.quit()




# ==================================================
# Main
# ==================================================

print(
    "Searching papers..."
)


history = load_history()


papers = search_papers()



papers = filter_history(

    papers,

    history

)



if not papers:


    raise Exception(
        "No new papers found"
    )



print(
    f"Selected {len(papers)} papers"
)



result = deepseek_analysis(

    papers

)



print(
    "AI analysis finished"
)



send_email(

    result

)



for p in papers:


    history["papers"].append(

        p["doi"]
        if p["doi"]
        else p["title"]

    )



save_history(

    history

)



print(
    "Email sent successfully"
)
