import feedparser
import requests
import os
import sys
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser

# ==================== 配置 ====================

BJT = timezone(timedelta(hours=8))

RSS_SOURCES = [
    {"name": "Hacker News",           "url": "https://news.ycombinator.com/rss",                 "category": "💻 计算机 & 开发"},
    {"name": "TechCrunch",            "url": "https://techcrunch.com/feed/",                      "category": "🤖 AI & 科技"},
    {"name": "The Verge",             "url": "https://www.theverge.com/rss/index.xml",            "category": "🤖 AI & 科技"},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/index",   "category": "🤖 AI & 科技"},
    {"name": "VentureBeat AI",        "url": "https://venturebeat.com/category/ai/feed/",         "category": "🤖 AI & 科技"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/",            "category": "🤖 AI & 科技"},
    {"name": "Wired",                 "url": "https://www.wired.com/feed/rss",                    "category": "🤖 AI & 科技"},
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
    if now.hour < 16:
        period = "早报"
        icon = "🌅"
    else:
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

    prompt = f"""你是一个新闻编辑助手，同时也是一个擅长发现商业机会的分析师。以下是从英文媒体抓取的最新新闻，请帮我完成两个任务：

【任务一：新闻简报】
1. 从中筛选出最有价值、最重要的15条（优先选择：AI/科技进展、国际重大事件、科技行业动态、科学发现）
2. 过滤掉低价值内容（娱乐八卦、体育赛事、重复新闻只保留一条）
3. 将标题和摘要翻译成中文
4. 按以下四个分类整理输出：🤖 AI & 科技 / 🌍 国际时事 / 💻 计算机 & 开发 / 🔬 科学
5. 每条新闻格式：
- 中文标题
  摘要：2-3句中文摘要，包含关键数据或影响
  时间：发布时间
  链接：原文URL

【任务二：机会分析】
在新闻简报结束后，另起一段，标题写"💡 今日机会分析"，然后：
1. 从今日新闻中挖掘2-3个普通人可以利用的机会，包括但不限于：
   - 信息差套利（某个产品/技术在国内外存在价格差或信息差）
   - 趋势红利（某个领域正在爆发，可以提前布局）
   - 倒卖/代购机会（某个产品因新闻热度可能涨价或断货）
   - 副业机会（某个技能或工具需求正在上升）
   - 投资方向（某个赛道值得关注）
2. 每个机会格式：
🔥 机会名称
背景：用1句话说明相关新闻背景
机会：具体说明怎么操作或利用
风险：简要提示潜在风险
3. 语气要务实接地气，面向普通人，不要空泛

注意：所有链接直接输出原始URL，不要用Markdown格式包裹。
只输出以上两个任务的内容，不要有多余的解释。

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
            "max_tokens": 4000,
            "temperature": 0.3,
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
    summary = call_grok(articles)

    date_str = now.strftime("%m月%d日")
    header = f"{icon} {date_str} {period}\n\n"
    footer = f"\n\n⏱ 本期处理 {len(articles)} 条新闻 | Powered by Grok"
    full_message = header + summary + footer

    print("发送到 Telegram...")
    send_telegram(full_message)
    print("推送完成！")

if __name__ == "__main__":
    main()