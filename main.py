import os
import json
import random
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

import feedparser
import requests
from openai import OpenAI

# Try loading .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==================================================
# Configuration & Environment Variables
# ==================================================

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()

SENDER = os.environ.get("SENDER", "").strip()
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "").strip()
RECEIVER = os.environ.get("RECEIVER", "").strip()
RECEIVER_2 = os.environ.get("RECEIVER_2", "").strip()

HISTORY_FILE = "papers_history.json"
PROFILE_FILE = "research_profile.json"


# ==================================================
# Profile & History Helpers
# ==================================================

def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return {
            "preferred_arxiv_categories": ["cs.AI", "cs.HC", "cs.CV", "cs.GR"],
            "keywords": ["AI design", "generative AI", "computational design", "spatial computing"],
            "news_rss_feeds": [
                "https://news.google.com/rss/search?q=(Artificial+Intelligence+OR+AI)+AND+(Design+OR+Creative)+when:2d&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=(OpenAI+OR+Anthropic+OR+DeepSeek+OR+\"Generative+AI\")+when:2d&hl=en-US&gl=US&ceid=US:en",
                "https://techcrunch.com/category/artificial-intelligence/feed/"
            ]
        }
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {"papers": [], "news": []}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"papers": [], "news": []}
            if "papers" not in data:
                data["papers"] = []
            if "news" not in data:
                data["news"] = []
            return data
    except Exception as e:
        print(f"Warning loading history: {e}")
        return {"papers": [], "news": []}


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ==================================================
# News Retrieval
# ==================================================

def clean_text(text):
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split())


def fetch_daily_news(profile, history):
    """
    Fetch trending news items from RSS feeds related to AI and Design.
    """
    print("Fetching today's AI & Design news...")
    feeds = profile.get("news_rss_feeds", [])
    seen_titles = {item["title"].strip().lower() for item in history.get("news", []) if "title" in item}

    candidates = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url, request_headers=headers)
            for entry in feed.entries:
                title = clean_text(entry.get("title", ""))
                if not title or len(title) < 8:
                    continue

                title_norm = title.lower()
                if title_norm in seen_titles:
                    continue

                link = entry.get("link", "")
                summary = clean_text(entry.get("summary", entry.get("description", "")))[:300]
                pub_date = entry.get("published", str(datetime.now().date()))

                candidates.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "date": pub_date
                })
                seen_titles.add(title_norm)
        except Exception as e:
            print(f"Notice: Failed to fetch feed {feed_url}: {e}")

    # Fallback to HuggingFace Daily Papers if candidate list is small
    if len(candidates) < 5:
        try:
            resp = requests.get("https://huggingface.co/api/daily_papers", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data[:8]:
                    paper_info = item.get("paper", {})
                    p_title = clean_text(paper_info.get("title", ""))
                    if p_title and p_title.lower() not in seen_titles:
                        candidates.append({
                            "title": f"[HuggingFace Trending] {p_title}",
                            "summary": clean_text(paper_info.get("summary", ""))[:300],
                            "link": f"https://huggingface.co/papers/{paper_info.get('id', '')}",
                            "date": str(datetime.now().date())
                        })
                        seen_titles.add(p_title.lower())
        except Exception as e:
            print(f"Notice: Hugging Face papers fetch skipped: {e}")

    print(f"Collected {len(candidates)} new news candidates.")
    return candidates


# ==================================================
# ArXiv Research Paper Search
# ==================================================

def search_arxiv(profile, history):
    """
    Search arXiv for latest relevant research papers.
    """
    print("Collecting latest research papers from arXiv...")
    categories = profile.get("preferred_arxiv_categories", ["cs.AI", "cs.HC", "cs.CV"])
    old_titles = {item["title"].strip().lower() for item in history.get("papers", []) if "title" in item}

    papers = []
    seen_in_batch = set()

    for category in categories:
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query=cat:{category}"
            "&sortBy=submittedDate"
            "&sortOrder=descending"
            "&max_results=12"
        )
        try:
            feed = feedparser.parse(url)
            for item in feed.entries:
                title = clean_text(item.get("title", ""))
                title_norm = title.lower()

                if not title or title_norm in old_titles or title_norm in seen_in_batch:
                    continue

                abstract = clean_text(item.get("summary", ""))
                link = item.get("link", "")

                authors = []
                if hasattr(item, "authors"):
                    authors = [a.get("name", "") for a in item.authors if a.get("name")]
                elif "author" in item:
                    authors = [item["author"]]

                author_str = ", ".join(authors[:4])
                if len(authors) > 4:
                    author_str += " et al."

                published = item.get("published", "")
                if published:
                    try:
                        published = published.split("T")[0]
                    except Exception:
                        pass
                else:
                    published = str(datetime.now().date())

                papers.append({
                    "title": title,
                    "abstract": abstract,
                    "authors": author_str or "Unknown",
                    "published": published,
                    "link": link
                })
                seen_in_batch.add(title_norm)
        except Exception as e:
            print(f"Notice: Failed to fetch arXiv category {category}: {e}")

    print(f"Collected {len(papers)} new paper candidates.")
    return papers


# ==================================================
# Candidate Pre-selection
# ==================================================

def preselect_papers(papers, profile, limit=12):
    """
    Quickly rank paper candidates using keyword matching to narrow down for LLM.
    """
    if len(papers) <= limit:
        return papers

    keywords = [kw.lower() for kw in profile.get("keywords", []) + profile.get("focus_areas", [])]

    def score(p):
        text = (p["title"] + " " + p["abstract"]).lower()
        return sum(2 if kw in p["title"].lower() else 1 for kw in keywords if kw in text)

    papers.sort(key=score, reverse=True)
    return papers[:limit]


# ==================================================
# DeepSeek AI Analysis
# ==================================================

def analyze_with_deepseek(news_candidates, paper_candidates, profile):
    """
    Ask DeepSeek to pick TOP 3 News and TOP 3 Papers, providing in-depth forward-looking insights.
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not set. Please provide a valid API key.")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_BASE
    )

    # Format News for prompt
    news_text = ""
    for i, item in enumerate(news_candidates[:15], 1):
        news_text += f"[{i}] 标题: {item['title']}\n    摘要: {item['summary']}\n    链接: {item['link']}\n    时间: {item['date']}\n\n"

    # Format Papers for prompt
    paper_text = ""
    for i, p in enumerate(paper_candidates, 1):
        paper_text += f"[{i}] 标题: {p['title']}\n    作者: {p['authors']}\n    日期: {p['published']}\n    链接: {p['link']}\n    摘要: {p['abstract'][:400]}...\n\n"

    prompt = f"""你是一名顶级科技前沿智库专家与设计计算领域学者。
请分析以下提供的候选新闻和候选论文，精选出【3 条最重大的 AI 与设计前瞻新闻】以及【3 篇最具前瞻性的学术研究论文】。

选拔标准：
1. 具备前瞻性、突破性与行业变革价值；
2. 围绕人工智能（Generative AI / 多模态 / 大模型）、设计行业（空间计算、计算设计、建筑、人机交互 HCI、创意生产力）交叉前沿；
3. 务必严格遵循如下输出格式规范，语言精练专业，见解深刻。

请严格按以下 JSON 格式返回（只返回纯 JSON，不加任何额外说明或代码块标记之外的文本）：

```json
{{
  "news_items": [
    {{
      "title_zh": "新闻中文标题（精炼有力）",
      "summary": "发生事件核心概括（2-3句话阐明发生了什么、核心关键点）",
      "future_impact": "对未来设计行业或人工智能行业的前瞻影响与深远价值",
      "source_link": "原文链接"
    }}
  ],
  "paper_items": [
    {{
      "title_zh": "中文标题",
      "title_en": "原英文标题",
      "authors": "作者列表",
      "published_date": "发表时间",
      "link": "论文链接",
      "core_topic": "核心主题（如：生成式3D/空间交互/智能架构）",
      "one_sentence_summary": "一句话概括研究内容",
      "future_impact": "对未来设计行业或人工智能行业的影响与前瞻价值"
    }}
  ]
}}
```

候选新闻池：
{news_text}

候选论文池：
{paper_text}
"""

    print(f"Calling DeepSeek ({DEEPSEEK_MODEL}) for deep analysis...")
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional AI and design intelligence analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON from response
    try:
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            data = json.loads(content)
        return data
    except Exception as e:
        print(f"Notice: Failed to parse pure JSON ({e}), returning raw content wrapper.")
        return {"raw_content": content}


# ==================================================
# Email Construction & Rendering
# ==================================================

def render_email_content(data):
    """
    Renders structured content into both plain text and modern responsive HTML.
    """
    date_str = datetime.now().strftime("%Y年%m月%d日")

    # If raw fallback
    if "raw_content" in data:
        plain = f"【AI & 设计前瞻日报 | {date_str}】\n\n" + data["raw_content"]
        html = f"""<div style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
            <h2>AI & 设计前瞻日报 ({date_str})</h2>
            <pre style="white-space: pre-wrap; background: #f4f4f4; padding: 15px; border-radius: 8px;">{data['raw_content']}</pre>
        </div>"""
        return plain, html

    news_list = data.get("news_items", [])[:3]
    paper_list = data.get("paper_items", [])[:3]

    # 1. Plain Text Version
    plain_lines = [
        f"══════════════════════════════════════════",
        f"  AI & 设计前瞻日报 | {date_str}",
        f"══════════════════════════════════════════",
        f"",
        f"【🔥 今日重大 AI & 设计新闻 TOP 3】",
        f"──────────────────────────────────────────"
    ]

    for i, item in enumerate(news_list, 1):
        plain_lines.append(f"\n{i}. {item.get('title_zh', '')}")
        plain_lines.append(f"   ▶ 事件概括: {item.get('summary', '')}")
        plain_lines.append(f"   ▶ 前瞻影响: {item.get('future_impact', '')}")
        plain_lines.append(f"   ▶ 参考链接: {item.get('source_link', '')}")

    plain_lines.append(f"\n\n【📚 精选前瞻学术论文 TOP 3】")
    plain_lines.append(f"──────────────────────────────────────────")

    for i, p in enumerate(paper_list, 1):
        plain_lines.append(f"\n{i}. {p.get('title_zh', '')}")
        plain_lines.append(f"   原名: {p.get('title_en', '')}")
        plain_lines.append(f"   作者: {p.get('authors', '')} | 发表: {p.get('published_date', '')}")
        plain_lines.append(f"   主题: {p.get('core_topic', '')}")
        plain_lines.append(f"   ▶ 一句话总结: {p.get('one_sentence_summary', '')}")
        plain_lines.append(f"   ▶ 行业前瞻价值: {p.get('future_impact', '')}")
        plain_lines.append(f"   ▶ 论文链接: {p.get('link', '')}")

    plain_lines.append(f"\n══════════════════════════════════════════")
    plain_lines.append(f"坚持每日阅读，探索智能与设计的美好未来。")
    plain_text = "\n".join(plain_lines)

    # 2. Modern Card HTML Version (for QQ Mail & mobile)
    news_cards_html = ""
    for i, item in enumerate(news_list, 1):
        news_cards_html += f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: baseline; margin-bottom: 8px;">
                <span style="background: #ef4444; color: #ffffff; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-right: 8px;">新闻 0{i}</span>
                <span style="font-size: 16px; font-weight: 700; color: #0f172a;">{item.get('title_zh', '')}</span>
            </div>
            <p style="color: #334155; font-size: 14px; line-height: 1.6; margin: 8px 0;"><strong>事件核心：</strong>{item.get('summary', '')}</p>
            <div style="background: #f8fafc; border-left: 3px solid #3b82f6; padding: 10px 12px; margin: 10px 0; border-radius: 0 6px 6px 0;">
                <p style="color: #1e293b; font-size: 13px; line-height: 1.5; margin: 0;"><strong>💡 前瞻影响：</strong>{item.get('future_impact', '')}</p>
            </div>
            <div style="margin-top: 10px;">
                <a href="{item.get('source_link', '#')}" target="_blank" style="color: #2563eb; font-size: 12px; text-decoration: none; word-break: break-all;">🔗 查看原文报道 &rarr;</a>
            </div>
        </div>
        """

    paper_cards_html = ""
    for i, p in enumerate(paper_list, 1):
        paper_cards_html += f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="margin-bottom: 6px;">
                <span style="background: #3b82f6; color: #ffffff; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-right: 6px;">论文 0{i}</span>
                <span style="background: #e0e7ff; color: #3730a3; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{p.get('core_topic', 'AI Research')}</span>
            </div>
            <h4 style="font-size: 16px; font-weight: 700; color: #0f172a; margin: 6px 0 2px 0;">{p.get('title_zh', '')}</h4>
            <div style="color: #64748b; font-size: 12px; font-style: italic; margin-bottom: 8px;">{p.get('title_en', '')}</div>
            <div style="color: #64748b; font-size: 12px; margin-bottom: 10px;">
                👥 {p.get('authors', '')} &nbsp;|&nbsp; 📅 {p.get('published_date', '')}
            </div>
            <p style="color: #334155; font-size: 14px; line-height: 1.6; margin: 8px 0;"><strong>📌 一句话概括：</strong>{p.get('one_sentence_summary', '')}</p>
            <div style="background: #f0fdf4; border-left: 3px solid #10b981; padding: 10px 12px; margin: 10px 0; border-radius: 0 6px 6px 0;">
                <p style="color: #064e3b; font-size: 13px; line-height: 1.5; margin: 0;"><strong>🚀 行业前瞻价值：</strong>{p.get('future_impact', '')}</p>
            </div>
            <div style="margin-top: 10px;">
                <a href="{p.get('link', '#')}" target="_blank" style="color: #2563eb; font-size: 12px; text-decoration: none; word-break: break-all;">📄 阅读全文 (arXiv) &rarr;</a>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width: 680px; margin: 20px auto; background-color: #f8fafc; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #ffffff; padding: 28px 24px; text-align: left;">
                <div style="font-size: 12px; letter-spacing: 1.5px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">DAILY INTELLIGENCE AGENT</div>
                <h1 style="font-size: 22px; margin: 0; font-weight: 800; color: #ffffff;">每日 AI & 设计前瞻日报</h1>
                <p style="color: #cbd5e1; font-size: 13px; margin: 8px 0 0 0;">📅 {date_str} · 3 条全球重大资讯 + 3 篇前沿学术论文</p>
            </div>

            <!-- Body Container -->
            <div style="padding: 24px;">
                <!-- Section 1: News -->
                <div style="margin-bottom: 28px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin: 0 0 14px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                        🔥 今日重大 AI & 设计新闻 TOP 3
                    </h3>
                    {news_cards_html}
                </div>

                <!-- Section 2: Papers -->
                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin: 0 0 14px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                        📚 精选前瞻学术论文 TOP 3
                    </h3>
                    {paper_cards_html}
                </div>

                <!-- Footer -->
                <div style="text-align: center; color: #94a3b8; font-size: 12px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
                    坚持每日精读，用前瞻思考探索未来创意与科技边界。<br>
                    Generated by AI-Research-Agent · Powered by DeepSeek
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return plain_text, html


# ==================================================
# Send Email via QQ SMTP
# ==================================================

def send_daily_email(plain_content, html_content):
    """
    Send email through QQ Mail SMTP (SSL 465).
    """
    if not SENDER or not SENDER_PASSWORD or not RECEIVER:
        print("\n[Notice] Email credentials (SENDER / SENDER_PASSWORD / RECEIVER) not configured.")
        print("Skipping actual email delivery. Below is the generated plain-text content:\n")
        print(plain_content)
        return False

    recipients = [RECEIVER]
    if RECEIVER_2:
        recipients.append(RECEIVER_2)

    msg = MIMEMultipart("alternative")
    subject_str = f"🚀 每日AI与设计前瞻简报 ({datetime.now().strftime('%m-%d')}) - 3大事 & 3论文"
    msg["Subject"] = Header(subject_str, "utf-8")
    msg["From"] = Header(f"AI 前瞻助手 <{SENDER}>", "utf-8")
    msg["To"] = Header(", ".join(recipients), "utf-8")

    part_text = MIMEText(plain_content, "plain", "utf-8")
    part_html = MIMEText(html_content, "html", "utf-8")

    msg.attach(part_text)
    msg.attach(part_html)

    print(f"Connecting to SMTP server (smtp.qq.com:465)...")
    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    try:
        server.login(SENDER, SENDER_PASSWORD)
        server.sendmail(SENDER, recipients, msg.as_string())
        print(f"Email successfully sent to: {', '.join(recipients)}")
        return True
    finally:
        server.quit()


# ==================================================
# Main Execution Flow
# ==================================================

def main():
    print("==================================================")
    print(" AI-Research-Agent: Daily News & Research Digest ")
    print("==================================================")

    profile = load_profile()
    history = load_history()

    # 1. Fetch news
    news_candidates = fetch_daily_news(profile, history)

    # 2. Fetch papers
    paper_candidates = search_arxiv(profile, history)
    selected_paper_candidates = preselect_papers(paper_candidates, profile, limit=12)

    if not news_candidates and not selected_paper_candidates:
        print("No new news or papers found today. Exiting.")
        return

    # 3. Analyze with DeepSeek
    analysis_data = analyze_with_deepseek(news_candidates, selected_paper_candidates, profile)

    # 4. Render Email
    plain_text, html_text = render_email_content(analysis_data)

    # 5. Send Email
    send_daily_email(plain_text, html_text)

    # 6. Update History
    now_str = str(datetime.now())

    # Record news
    for item in analysis_data.get("news_items", []):
        history["news"].append({
            "title": item.get("title_zh", ""),
            "link": item.get("source_link", ""),
            "date": now_str
        })

    # Record papers
    for p in analysis_data.get("paper_items", []):
        history["papers"].append({
            "title": p.get("title_en", p.get("title_zh", "")),
            "link": p.get("link", ""),
            "date": now_str
        })

    # Keep history bounded (last 1000 items)
    history["news"] = history["news"][-1000:]
    history["papers"] = history["papers"][-1000:]

    save_history(history)
    print("History updated successfully.")
    print("Daily digest finished successfully!")


if __name__ == "__main__":
    main()
