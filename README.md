AI-Research-Agent

每天自动抓取 arXiv 论文，筛选与建筑设计、AI、HCI 相关的文章，用 DeepSeek 生成中文分析，再通过 QQ 邮箱发送。

----

每天发送时间

北京时间 12:20

GitHub Actions 定时运行，实际发送可能晚几分钟。

----

主要流程

读取研究配置 research_profile.json

抓取 arXiv 最新论文

按标题去重，使用 papers_history.json

用 SentenceTransformer 计算相似度，保留前 5 篇

调用 DeepSeek 生成中文分析

通过 QQ 邮箱发送

保存本次论文到 papers_history.json

----

主要文件

main.py 主程序

daily.yml GitHub Actions 工作流

research_profile.json 研究方向与筛选配置

papers_history.json 已处理论文记录，自动更新

requirements.txt 依赖

----

需要的 secrets

DEEPSEEK_API_KEY

DEEPSEEK_API_BASE

SENDER

SENDER_PASSWORD

RECEIVER

RECEIVER_2

----

本地运行

pip install -r requirements.txt

设置环境变量

python main.py

----

修改研究方向

编辑 research_profile.json

可改 research_direction

future_technology_interest

preferred_arxiv_categories

keywords

----

注意事项

papers_history.json 由 workflow 自动提交

不要手动修改，否则可能重复处理
