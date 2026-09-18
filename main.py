import os
import json
import random
import smtplib

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
# Load Profile
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
# arXiv Search
# ==================================================

def search_arxiv():


    papers=[]



    categories = profile[

        "preferred_arxiv_categories"

    ]



    for category in categories:



        url=(

            "https://export.arxiv.org/api/query?"

            f"search_query=cat:{category}"

            "&sortBy=submittedDate"

            "&sortOrder=descending"

            "&max_results=20"

        )



        feed = feedparser.parse(url)



        for item in feed.entries:



            title = item.title.replace(

                "\n",

                " "

            )


            abstract = item.summary.replace(

                "\n",

                " "

            )



            link = item.link



            papers.append({

                "title":title,

                "abstract":abstract,

                "source":"arXiv",

                "link":link,

                "date":str(datetime.now())

            })



    return papers





# ==================================================
# Remove History
# ==================================================

def remove_duplicate(

        papers,

        history

):


    old_titles=set()



    for item in history.get(

        "papers",

        []

    ):


        old_titles.add(

            item["title"]

        )



    result=[]



    for paper in papers:



        if paper["title"] not in old_titles:


            result.append(

                paper

            )



    return result





# ==================================================
# Embedding Ranking
# ==================================================

def rank_papers(

        papers

):


    print(

        "Loading embedding model..."

    )



    model = SentenceTransformer(

        "all-MiniLM-L6-v2"

    )




    research_text = " ".join(

        profile["research_direction"]

        +

        profile["future_technology_interest"]

    )



    research_vector = model.encode(

        [

            research_text

        ]

    )



    paper_texts=[]



    for paper in papers:


        paper_texts.append(

            paper["title"]

            +

            " "

            +

            paper["abstract"]

        )



    paper_vectors=model.encode(

        paper_texts

    )



    scores=cosine_similarity(

        research_vector,

        paper_vectors

    )[0]




    for i,paper in enumerate(papers):


        paper["score"]=float(

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

def analyze_papers(

        papers

):


    client=OpenAI(

        api_key=DEEPSEEK_API_KEY,

        base_url=DEEPSEEK_API_BASE

    )



    content=""



    for i,paper in enumerate(papers):


        content += f"""
论文{i+1}
标题：{paper['title']}
链接：{paper['link']}
摘要：{paper['abstract']}
==============================
"""



    prompt=f"""
你是一名博士研究助手。
请用简洁的中文分析下面的论文。
不要使用任何 Markdown 符号，不要使用井号、星号、加粗或列表符号。
文字尽量精炼，少用标点。
每篇论文之间用一行等号分隔。
每篇论文只输出以下内容：
论文编号
英文标题
中文标题
中文摘要
研究亮点
为什么值得建筑设计领域关注
==============================

我的研究方向：
AI + TouchDesigner + Interactive Art + Spatial Design + Architecture + Elderly Architecture + Human Computer Interaction

论文：
{content}
"""



    response=client.chat.completions.create(


        model="deepseek-v4-flash",


        messages=[

            {

                "role":"user",

                "content":prompt

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


    greetings=[


        "🐷超级贝猪，今天也要认真学习哦！",

        "🐷超级贝猪，新的AI前沿论文已经送达啦！",

        "🐷超级贝猪，坚持每天阅读，未来创新来自今天的积累。"


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

        "🐷超级贝猪每日AI前沿论文",

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

    "Collecting arXiv papers..."

)



history=load_history()



papers=search_arxiv()



print(

    "Collected:",

    len(papers)

)



papers=remove_duplicate(

    papers,

    history

)



print(

    "New papers:",

    len(papers)

)



if not papers:


    raise Exception(

        "No new papers"

    )



papers=rank_papers(

    papers

)



print(

    "Selected:",

    len(papers)

)



result=analyze_papers(

    papers

)



send_email(

    result

)



for paper in papers:


    history["papers"].append({

        "title":

        paper["title"],


        "date":

        str(datetime.now())

    })



save_history(

    history

)



print(

    "Finished successfully"

)
