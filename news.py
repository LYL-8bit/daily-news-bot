import feedparser
import requests
import os
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser

# ==================== 配置 ====================

BJT = timezone(timedelta(hours=8))

RSS_SOURCES = [
    {"name": "CNBC Top News",          "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",       "category": "📈 美股 & 商业"},
    {"name": "CNBC Technology",        "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",        "category": "📈 美股 & 商业"},
    {"name": "MarketWatch Top",        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",  "category": "📈 美股 & 商业"},
    {"name": "MarketWatch Pulse",      "url": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "category": "📈 美股 & 商业"},
    {"name": "Yahoo Finance",          "url": "https://finance.yahoo.com/news/rssindex",                    "category": "📈 美股 & 商业"},
    {"name": "Hacker News",           "url": "https://news.ycombinator.com/rss",                 "category": "💻 计算机 & 开发"},
    {"name": "TechCrunch",            "url": "https://techcrunch.com/feed/",                      "category": "🤖 AI & 科技"},
    {"name": "The Verge",             "url": "https://www.theverge.com/rss/index.xml",            "category": "🤖 AI & 科技"},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/index",   "category": "🤖 AI & 科技"},
    {"name": "VentureBeat AI",        "url": "https://venturebeat.com/category/ai/feed/",         "category": "🤖 AI & 科技"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/",            "category": "🤖 AI & 科技"},
    {"name": "Wired",                 "url": "https://www.wired.com/feed/rss",                    "category": "🤖 AI & 科技"},
    {"name": "NYTimes Technology",     "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "category": "🤖 AI & 科技"},
    {"name": "IEEE Spectrum",         "url": "https://spectrum.ieee.org/feeds/feed.rss",          "category": "💻 计算机 & 开发"},
    {"name": "Reuters",               "url": "https://feeds.reuters.com/reuters/topNews",         "category": "🌍 国际时事"},
    {"name": "AP News",               "url": "https://feeds.apnews.com/rss/apf-topnews",          "category": "🌍 国际时事"},
    {"name": "BBC News",              "url": "https://feeds.bbci.co.uk/news/rss.xml",             "category": "🌍 国际时事"},
    {"name": "Al Jazeera",            "url": "https://www.aljazeera.com/xml/rss/all.xml",         "category": "🌍 国际时事"},
    {"name": "The Guardian World",    "url": "https://www.theguardian.com/world/rss",             "category": "🌍 国际时事"},
    {"name": "DW News",               "url": "https://rss.dw.com/rdf/rss-en-all",                "category": "🌍 国际时事"},
    {"name": "France 24",             "url": "https://www.france24.com/en/rss",                  "category": "🌍 国际时事"},
    {"name": "NPR World",             "url": "https://feeds.npr.org/1004/rss.xml",               "category": "🌍 国际时事"},
    {"name": "New Scientist",         "url": "https://www.newscientist.com/feed/home/",           "category": "🔬 科学"},
    {"name": "Science Daily",         "url": "https://www.sciencedaily.com/rss/top/science.xml", "category": "🔬 科学"},
    {"name": "BBC 中文",              "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",    "category": "🌍 国际时事"},
    {"name": "RFI 中文",              "url": "https://www.rfi.fr/cn/rss",                        "category": "🌍 国际时事"},
]

IMPORTANT_KEYWORDS = {
    # 用户最关注：美国科技、美股、AI、宏观影响资产价格的事件
    "ai": 8, "artificial intelligence": 8, "openai": 8, "anthropic": 8, "nvidia": 9,
    "microsoft": 7, "google": 7, "alphabet": 7, "meta": 7, "apple": 7, "amazon": 7,
    "tesla": 7, "semiconductor": 7, "chip": 7, "data center": 7, "cloud": 6,
    "earnings": 8, "stock": 6, "stocks": 6, "nasdaq": 8, "s&p": 8, "dow": 5,
    "fed": 8, "federal reserve": 8, "rate": 6, "inflation": 7, "jobs report": 7,
    "treasury": 5, "oil": 5, "crypto": 5, "bitcoin": 5,
    "war": 6, "tariff": 6, "sanction": 6, "china": 5, "taiwan": 6, "ukraine": 5,
    "major": 4, "breakthrough": 5, "launch": 4, "acquisition": 5, "lawsuit": 4,
}

CATEGORY_WEIGHTS = {
    "📈 美股 & 商业": 12,
    "🤖 AI & 科技": 10,
    "💻 计算机 & 开发": 5,
    "🌍 国际时事": 3,
    "🔬 科学": 2,
}

MAX_ARTICLES_FOR_GROK = 90

# ==================== 测试模式 ====================

def test_sources():
    print("=" * 50)
    print("RSS 新闻源测试")
    print("=" * 50)
    ok = []
    fail = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            count = len(feed.entries)
            if count > 0:
                print(f"✅ {source['name']:<30} 获取到 {count} 条")
                ok.append(source["name"])
            else:
                print(f"⚠️  {source['name']:<30} 连接成功但没有内容")
                fail.append(source["name"])
        except Exception as e:
            print(f"❌ {source['name']:<30} 失败：{e}")
            fail.append(source["name"])
    print("=" * 50)
    print(f"可用：{len(ok)} 个　失败：{len(fail)} 个")
    if fail:
        print(f"失败的源：{', '.join(fail)}")

# ==================== 抓取新闻 ====================

def fetch_news():
    now = datetime.now(BJT)
    period = "晚报"
    icon = "🌙"
    cutoff = now - timedelta(hours=12)

    articles = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:20]:
                pub_time = None
                if hasattr(entry, "published"):
                    try:
                        pub_time = dateparser.parse(entry.published)
                        if pub_time and pub_time.tzinfo is None:
                            pub_time = pub_time.replace(tzinfo=timezone.utc)
                    except:
                        pass

                if pub_time and pub_time < cutoff.astimezone(timezone.utc):
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:300].strip()

                if title and link:
                    if pub_time:
                        pub_bjt = pub_time.astimezone(BJT)
                        pub_str = pub_bjt.strftime("%m-%d %H:%M")
                    else:
                        pub_str = "时间未知"
                    articles.append({
                        "source": source["name"],
                        "category": source["category"],
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "pub_time": pub_str,
                    })
        except Exception as e:
            print(f"抓取 {source['name']} 失败：{e}")

    return articles, period, icon, now


def score_article(article):
    """给新闻打分：优先保留美国科技、美股、AI、宏观市场和重大国际事件。"""
    text = f"{article['title']} {article['summary']} {article['source']}".lower()
    score = CATEGORY_WEIGHTS.get(article["category"], 0)

    for keyword, weight in IMPORTANT_KEYWORDS.items():
        if keyword in text:
            score += weight

    # 同样重要的新闻，更新的排前面；时间未知不额外加分。
    if article["pub_time"] != "时间未知":
        score += 1

    return score


def prepare_articles_for_grok(articles):
    """去重、排序并限制输入规模，避免模型被低价值新闻淹没。"""
    deduped = []
    seen_titles = set()
    for article in articles:
        key = article["title"].lower().strip()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(article)

    deduped.sort(key=score_article, reverse=True)
    return deduped[:MAX_ARTICLES_FOR_GROK]

# ==================== 调用 Grok ====================

def call_grok(articles):
    api_key = os.environ.get("GROK_API_KEY")
    if not api_key:
        raise ValueError("未找到 GROK_API_KEY")

    article_text = ""
    for i, a in enumerate(articles, 1):
        article_text += f"{i}. [{a['source']}] [{a['pub_time']}] {a['title']}\n"
        if a["summary"]:
            article_text += f"   摘要：{a['summary']}\n"
        article_text += f"   链接：{a['link']}\n\n"

    prompt = f"""你是一个中文新闻编辑和美股/科技观察员。用户偏好：信息要全，但不要啰嗦；重点关注美国科技、美股、AI、半导体、大厂、宏观数据，同时也想知道当天全球重大事件。

请从下面新闻中去重、合并同类项，输出一份【精简但信息密度高】的中文晚报。

硬性要求：
1. 全文控制在 1200-1800 个中文字左右，宁可少写废话，也不要遗漏真正的大事。
2. 优先级：美国科技/AI/美股/半导体/大厂财报与监管 > 影响市场的宏观与地缘事件 > 全球重大时事 > 开发者/科学新闻。
3. 不要逐条贴 URL；每条只保留来源名和时间。只有特别值得回看原文的，才在最后放“🔗 值得点开的原文”最多 3 个 URL。
4. 每条新闻最多 1-2 句话，必须写清楚“发生了什么 + 为什么重要/可能影响什么”。
5. 去掉娱乐、体育、低价值产品软文、小更新；重复新闻合并。
6. 不要使用 Markdown 链接，不要输出多余解释。

固定输出格式：

📌 今日主线
- 3 条以内，每条一句话，总结今天最重要的方向。

📈 美国科技 / 美股重点
- 5-7 条。每条格式：标题：一句话说明事实；影响：对美股、公司、AI、半导体或市场情绪的意义。（来源 时间）

🌍 全球大事速览
- 4-6 条。只放真正重要的国际/宏观/地缘事件。

💻 AI / 开发者 / 科学
- 3-5 条。偏向技术趋势、工具、模型、科研突破，不要堆小新闻。

💡 今日可行动关注
- 最多 3 条。每条格式：
  - 方向：具体关注什么
    理由：为什么值得看
    风险：可能错在哪里

🔗 值得点开的原文
- 最多 3 个 URL；如果没有特别值得点开的，就写“无”。

新闻列表：
{article_text}"""

    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-4-1-fast-non-reasoning",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2400,
            "temperature": 0.2,
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ==================== 发送 Telegram ====================

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("未找到 Telegram 配置")

    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]

    for chunk in chunks:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not resp.ok:
            print(f"Telegram发送失败：{resp.status_code}")
        resp.raise_for_status()

# ==================== 发送邮件 ====================

def send_email(subject, text):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "")
    if not sender or not password or not recipients_raw:
        raise ValueError("未找到邮件配置")

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())

# ==================== 主程序 ====================

def main():
    if "--test" in sys.argv:
        test_sources()
        return

    print("开始抓取新闻...")
    articles, period, icon, now = fetch_news()
    print(f"共抓取到 {len(articles)} 条新闻")

    if not articles:
        print("没有抓取到新闻，退出")
        return

    print("调用 Grok API 处理中...")
    selected_articles = prepare_articles_for_grok(articles)
    print(f"筛选后提交 {len(selected_articles)} 条高价值新闻给 Grok")
    summary = call_grok(selected_articles)

    date_str = now.strftime("%m月%d日")
    header = f"{icon} {date_str} {period}｜精简版\n\n"
    footer = f"\n\n⏱ 抓取 {len(articles)} 条，筛选 {len(selected_articles)} 条 | Powered by Grok"
    full_message = header + summary + footer

    subject = f"{icon} {date_str} {period}｜精简版"
    errors = []

    try:
        print("发送到 Telegram...")
        send_telegram(full_message)
        print("Telegram 发送成功")
    except Exception as e:
        print(f"Telegram 发送失败：{e}")
        errors.append(f"Telegram: {e}")

    try:
        print("发送邮件...")
        send_email(subject, full_message)
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败：{e}")
        errors.append(f"Email: {e}")

    if errors:
        raise RuntimeError("部分渠道发送失败：" + " | ".join(errors))
    print("推送完成！")

if __name__ == "__main__":
    main()