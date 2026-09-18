import os
import json
import random
import smtplib
import requests
import feedparser

from datetime import datetime

from email.mime.text import MIMEText
from email.header import Header

from openai import OpenAI

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity



# ==================================================
# Environment
# ==================================================

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_API_BASE = os.environ["DEEPSEEK_API_BASE"]

SENDER = os.environ["SENDER"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]

RECEIVER = os.environ["RECEIVER"]
RECEIVER_2 = os.environ["RECEIVER_2"]


HISTORY_FILE = "papers_history.json"
PROFILE_FILE = "research_profile.json"



# ==================================================
# Load Research Profile
# ==================================================

def load_profile():

    with open(
        PROFILE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)



profile = load_profile()



# ==================================================
# History
# ==================================================

def load_history():

    if not os.path.exists(HISTORY_FILE):

        return {
            "papers":[]
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
# arXiv
# ==================================================

def search_arxiv():

    papers=[]


    categories=[

        "cs.AI",
        "cs.HC",
        "cs.GR",
        "cs.CV"

    ]


    for cat in categories:


        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query=cat:{cat}"
            "&sortBy=submittedDate"
            "&sortOrder=descending"
            "&max_results=15"
        )


        feed = feedparser.parse(url)



        for item in feed.entries:


            papers.append({

                "title":
                item.title.replace("\n"," "),

                "abstract":
                item.summary,

                "source":
                "arXiv",

                "journal":
                "arXiv preprint",

                "doi":
                "",

                "year":
                datetime.now().year

            })


    return papers




# ==================================================
# OpenAlex
# ==================================================

def search_openalex():


    papers=[]


    keywords = profile["keywords"]



    for keyword in keywords:


        url="https://api.openalex.org/works"


        params={

            "search":
            keyword,

            "filter":
            "from_publication_date:2020-01-01",

            "sort":
            "cited_by_count:desc",

            "per-page":
            15

        }



        r=requests.get(

            url,

            params=params,

            timeout=30

        )



        data=r.json()



        for item in data.get(
            "results",
            []
        ):


            title=item.get(
                "title",
                ""
            )


            if not title:

                continue



            journal=""


            if item.get(
                "primary_location"
            ):

                source=item[
                    "primary_location"
                ].get(
                    "source"
                )


                if source:

                    journal=source.get(
                        "display_name",
                        ""
                    )



            papers.append({

                "title":
                title,

                "abstract":
                "",

                "source":
                "OpenAlex",

                "journal":
                journal,

                "doi":
                item.get(
                    "doi",
                    ""
                ),

                "year":
                item.get(
                    "publication_year",
                    ""
                )

            })


    return papers




# ==================================================
# Remove History
# ==================================================

def remove_duplicate(
        papers,
        history
):


    old=set()


    for p in history["papers"]:

        old.add(
            p.get(
                "title",
                ""
            )
        )


        if p.get("doi"):

            old.add(
                p["doi"]
            )



    result=[]


    for p in papers:


        key=p["doi"] if p["doi"] else p["title"]


        if key not in old:

            result.append(p)



    return result



# ==================================================
# Embedding Ranking
# ==================================================

def ranking(papers):


    if len(papers)<=5:

        return papers



    model=SentenceTransformer(
        "all-MiniLM-L6-v2"
    )



    interest=" ".join(

        profile["research_topics"]

    )



    interest_vector=model.encode(

        [interest]

    )



    texts=[]


    for p in papers:

        texts.append(

            p["title"]
            +
            " "
            +
            p.get(
                "abstract",
                ""
            )

        )



    vectors=model.encode(
        texts
    )



    scores=cosine_similarity(

        interest_vector,

        vectors

    )[0]



    for i,p in enumerate(papers):

        p["score"]=float(
            scores[i]
        )



    papers.sort(

        key=lambda x:x["score"],

        reverse=True

    )


    return papers[:5]



# ==================================================
# DeepSeek
# ==================================================

def analyze(papers):


    client=OpenAI(

        api_key=DEEPSEEK_API_KEY,

        base_url=DEEPSEEK_API_BASE

    )



    text=""


    for i,p in enumerate(papers):


        text+=f"""

论文{i+1}

标题:
{p['title']}

来源:
{p['source']}

期刊:
{p['journal']}

DOI:
{p['doi']}

摘要:
{p.get('abstract','')}


----------------------

"""



    prompt=f"""

你是我的博士研究助手。

我的研究方向：

AI + TouchDesigner + Interactive Art + Spatial Design + Computational Design + Architecture + Elderly Architecture + HCI


请分析以下论文。


输出格式：


🐷超级贝猪每日论文分析


英文标题（中文标题）


期刊/会议：
如果无法确认SCI分区，不要编造。


第一作者：
姓名 + 单位（如果数据库没有，请说明）


通讯作者：
姓名 + 单位（如果数据库没有，请说明）


摘要中文：


研究方法：


研究亮点：


对我的研究启发：

重点分析：

1. AI应用

2. 交互设计

3. 空间设计

4. 老年建筑

5. 可形成SCI研究方向



论文之间使用：

==================================================


论文：

{text}


"""



    response=client.chat.completions.create(

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

def send_email(content):


    greetings=[

        "🐷超级贝猪，今天也要认真学习哦！",

        "🐷超级贝猪，新的论文灵感已经送达啦！",

        "🐷超级贝猪，坚持阅读，未来的创新来自每天积累。"

    ]


    body=(

        random.choice(greetings)

        +

        "\n\n"

        +

        content

    )



    msg=MIMEText(

        body,

        "plain",

        "utf-8"

    )


    msg["Subject"]=Header(

        "🐷超级贝猪每日论文分析",

        "utf-8"

    )


    msg["From"]=SENDER

    msg["To"]=RECEIVER



    server=smtplib.SMTP_SSL(

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

        msg.as_string()

    )


    server.quit()



# ==================================================
# Main
# ==================================================

print(
    "Collecting papers..."
)



history=load_history()



papers=[]


papers.extend(
    search_arxiv()
)


papers.extend(
    search_openalex()
)



print(
    len(papers),
    "candidate papers"
)



papers=remove_duplicate(

    papers,

    history

)



papers=ranking(

    papers

)



print(
    "Selected",
    len(papers)
)



result=analyze(

    papers

)



send_email(

    result

)



for p in papers:

    history["papers"].append({

        "title":
        p["title"],

        "doi":
        p["doi"],

        "date":
        str(datetime.now())

    })



save_history(

    history

)



print(
    "Finished"
)
