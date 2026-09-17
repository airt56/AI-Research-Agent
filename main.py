import os
import smtplib
from email.mime.text import MIMEText

from pyzotero import zotero
from openai import OpenAI


# ==========================
# 环境变量
# ==========================

ZOTERO_ID = os.environ["ZOTERO_ID"]
ZOTERO_KEY = os.environ["ZOTERO_KEY"]

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_API_BASE = os.environ["DEEPSEEK_API_BASE"]

SENDER = os.environ["SENDER"]
RECEIVER = os.environ["RECEIVER"]
RECEIVER_2 = os.environ["RECEIVER_2"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]



# ==========================
# 连接 Zotero
# ==========================

print("Connecting Zotero...")


zot = zotero.Zotero(
    ZOTERO_ID,
    "user",
    ZOTERO_KEY
)


papers = zot.top(
    limit=5
)


print(
    f"Found {len(papers)} papers"
)



paper_content = ""


for i, paper in enumerate(papers):

    title = paper["data"].get(
        "title",
        ""
    )

    abstract = paper["data"].get(
        "abstractNote",
        ""
    )


    paper_content += f"""

======================

Paper {i+1}

Title:

{title}


Abstract:

{abstract}


"""



# ==========================
# DeepSeek
# ==========================


print("Calling DeepSeek...")


client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_BASE
)



prompt = f"""

你是一名设计学、建筑环境与人工智能方向科研助手。


我的研究方向：

AI + TouchDesigner + Interactive Art + Spatial Design + Human Computer Interaction + Computational Design


请分析以下5篇论文。


每篇论文严格按照：

# 今日论文分析


## 1. 标题（英文 + 中文）


## 2. 摘要中文翻译


## 3. 研究问题


## 4. 研究方法

包括：

- 数据来源
- 实验设计
- 技术方法
- 评价方式


## 5. 创新点


包括：

- 理论创新
- 方法创新
- 技术创新
- 应用创新


## 6. 与我的研究关系


分析：

- TouchDesigner相关性
- AI相关性
- 交互设计相关性
- 空间设计应用可能


## 7. 潜在SCI选题启发


提出：

- 可以借鉴的方法
- 可以形成的新研究问题
- 可能实验设计


论文：

{paper_content}

请使用中文输出。


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



result = response.choices[0].message.content



print("AI analysis finished")



# ==========================
# 邮件发送
# ==========================


subject = "今日论文分析"


msg = MIMEText(
    result,
    "plain",
    "utf-8"
)


msg["Subject"] = subject
msg["From"] = SENDER
msg["To"] = RECEIVER



receivers = [

    RECEIVER,
    RECEIVER_2

]



server = smtplib.SMTP_SSL(

    "smtp.126.com",

    465

)


server.login(

    SENDER,

    SENDER_PASSWORD

)



server.sendmail(

    SENDER,

    receivers,

    msg.as_string()

)



server.quit()



print("Email sent successfully")
