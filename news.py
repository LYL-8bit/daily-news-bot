import feedparser
import requests
import os
import sys
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser

# ==================== 配置 ====================

# 北京时区
BJT = timezone(timedelta(hours=8))

# RSS 新闻源
RSS_SOURCES = [
    # AI / 科技
    {"name": "Hacker News",             "url": "https://news.ycombinator.com/rss", "category": "💻 计算机 & 开发"},
    {"name": "TechCrunch",              "url": "https://techcrunch.com/feed/", "category": "🤖 AI & 科技"},
    {"name": "The Verge",               "url": "https://www.theverge.com/rss/index.xml", "category": "🤖 AI & 科技"},
    {"name": "Ars Technica",            "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "🤖 AI & 科技"},
    {"name": "VentureBeat AI",          "url": "https://venturebeat.com/category/ai/feed/", "category": "🤖 AI & 科技"},
    {"name": "MIT Technology Review",   "url": "https://www.technologyreview.com/feed/", "category": "🤖 AI & 科技"},
    # 国际时事
    {"name": "Reuters",                 "url": "https://feeds.reuters.com/reuters/topNews", "category": "🌍 国际时事"},
    {"name": "AP News",                 "url": "https://feeds.apnews.com/rss/apf-topnews", "category": "🌍 国际时事"},
    {"name": "BBC News",                "url": "https://feeds.bbci.co.uk/news/rss.xml", "category": "🌍 国际时事"},
    {"name": "Al Jazeera",              "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "🌍 国际时事"},
    # 中文补充
    {"name": "BBC 中文",                "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "category": "🌍 国际时事"},
    {"name": "RFI 中文",                "url": "https://www.rfi.fr/cn/rss", "category": "🌍 国际时事"},
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
    # 判断是早报还是晚报
    if now.hour < 16:
        period = "早报"
        icon = "🌅"
        cutoff = now - timedelta(hours=12)
    else:
        period = "晚报"
        icon = "🌙"
        cutoff = now - timedelta(hours=12)

    articles = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:20]:  # 每个源最多取20条
                # 解析时间
                pub_time = None
                if hasattr(entry, "published"):
                    try:
                        pub_time = dateparser.parse(entry.published)
                        if pub_time and pub_time.tzinfo is None:
                            pub_time = pub_time.replace(tzinfo=timezone.utc)
                    except:
                        pass

                # 过滤时间窗口
                if pub_time and pub_time < cutoff.astimezone(timezone.utc):
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:300].strip()

                if title and link:
                    articles.append({
                        "source": source["name"],
                        "category": source["category"],
                        "title": title,
                        "link": link,
                        "summary": summary,
                    })
        except Exception as e:
            print(f"抓取 {source['name']} 失败：{e}")

    return articles, period, icon, now

# ==================== 调用 Grok ====================

def call_grok(articles):
    api_key = os.environ.get("GROK_API_KEY")
    if not api_key:
        raise ValueError("未找到 GROK_API_KEY")

    # 构建文章列表文本
    article_text = ""
    for i, a in enumerate(articles[:60], 1):  # 最多送60条给Grok
        article_text += f"{i}. [{a['source']}] {a['title']}\n"
        if a["summary"]:
            article_text += f"   摘要：{a['summary']}\n"
        article_text += f"   链接：{a['link']}\n\n"

    prompt = f"""你是一个新闻编辑助手。以下是从英文媒体抓取的最新新闻，请帮我：
1. 从中筛选出最有价值、最重要的10条（优先选择：AI/科技进展、国际重大事件、科技行业动态）
2. 过滤掉低价值内容（娱乐八卦、体育、重复新闻）
3. 将标题和摘要翻译成中文
4. 按以下三个分类整理输出：🤖 AI & 科技 / 🌍 国际时事 / 💻 计算机 & 开发
5. 每条新闻格式：• 中文标题 — 1-2句中文摘要 [原文链接]

只输出整理好的新闻内容，不要有多余的解释。

新闻列表：
{article_text}"""

    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-3-fast",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
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

    # 清理特殊字符
    text = text.replace("&", "&amp;")

    # 超过4000字符自动分段
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]

    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        print(f"发送内容前200字：{chunk[:200]}")
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=30,
        )
        print(f"Telegram响应：{resp.status_code} {resp.text}")
        resp.raise_for_status()

# ==================== 主程序 ====================

def main():
    # 测试模式
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