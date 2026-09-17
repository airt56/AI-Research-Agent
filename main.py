import os
import smtplib

from email.mime.text import MIMEText
from email.header import Header

from pyzotero import zotero
from openai import OpenAI



# ==================================================
# Environment Variables
# ==================================================

ZOTERO_ID = os.environ["ZOTERO_ID"]
ZOTERO_KEY = os.environ["ZOTERO_KEY"]


DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_API_BASE = os.environ["DEEPSEEK_API_BASE"]


SENDER = os.environ["SENDER"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]

RECEIVER = os.environ["RECEIVER"]
RECEIVER_2 = os.environ["RECEIVER_2"]



# ==================================================
# 1. Connect Zotero
# ==================================================

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



# ==================================================
# 2. Extract papers
# ==================================================

paper_content = ""


for i, paper in enumerate(papers):


    data = paper["data"]


    title = data.get(
        "title",
        "No title"
    )


    abstract = data.get(
        "abstractNote",
        "No abstract"
    )


    year = data.get(
        "date",
        ""
    )


    paper_content += f"""

==============================

Paper {i+1}

Title:
{title}


Year:
{year}


Abstract:
{abstract}


"""



# ==================================================
# 3. DeepSeek Analysis
# ==================================================

print("Calling DeepSeek...")


client = OpenAI(

    api_key=DEEPSEEK_API_KEY,

    base_url=DEEPSEEK_API_BASE

)



prompt = f"""

你是一名高级科研助手。


我的研究方向：

- Interactive Art 交互艺术
- Art and Technology 艺术与科技
- Spatial Design 空间设计
- Human Computer Interaction 人机交互
- Computational Design 计算设计
- Generative Design 生成式设计
- AI + TouchDesigner


请分析以下5篇论文。


每篇论文严格按照以下结构输出：


# 今日论文分析


## 1. 标题

英文标题：

中文标题：


## 2. 摘要中文翻译


完整翻译摘要。


## 3. 研究问题

说明：

- 作者解决什么问题？
- 为什么这个问题重要？


## 4. 研究方法


包括：

- 数据来源
- 实验设计
- 技术方法
- 分析方法
- 评价指标


## 5. 创新点


分析：

- 理论创新
- 方法创新
- 技术创新
- 应用创新


## 6. 与我的研究关系


重点分析：

- AI相关性
- 交互艺术相关性
- 空间设计相关性
- TouchDesigner可实现性
- 可借鉴实验方法


## 7. 潜在SCI研究启发


提出：

- 可以形成的新研究问题
- 可以复刻的方法
- 可能的实验设计


论文如下：

{paper_content}


请使用中文回答。



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



analysis_result = response.choices[0].message.content



print("AI analysis finished")



# ==================================================
# 4. Send Email QQ SMTP
# ==================================================

print("Connecting QQ Mail SMTP...")


subject = "今日论文分析"



message = MIMEText(

    analysis_result,

    "plain",

    "utf-8"

)


message["Subject"] = Header(
    subject,
    "utf-8"
)


message["From"] = SENDER


receivers = [

    RECEIVER,

    RECEIVER_2

]


message["To"] = ",".join(receivers)



try:


    server = smtplib.SMTP_SSL(

        "smtp.qq.com",

        465

    )


    server.login(

        SENDER,

        SENDER_PASSWORD

    )


    print(
        "SMTP login successful"
    )


    server.sendmail(

        SENDER,

        receivers,

        message.as_string()

    )


    server.quit()


    print(
        "Email sent successfully"
    )



except Exception as e:


    print(
        "Email sending failed:"
    )


    print(e)


    raise e
