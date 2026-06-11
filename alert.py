import feedparser
import os
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
CACHE_FILE = "alert_cache.txt"
CACHE_TTL_DAYS = 7

# ==================== 关键词配置（大小写不敏感）====================

ALERT_KEYWORDS = [
    # 重点人物
    "elon musk", "trump", "jerome powell", "sam altman", "justin sun",

    # AI & 大模型（具体产品/公司，不放泛称 llm/chip）
    "openai", "anthropic", "claude", "gemini", "grok", "chatgpt",

    # 芯片 & 半导体（具体公司）
    "nvidia", "tsmc", "intel", "amd",

    # 重点公司（马斯克系）
    "tesla", "spacex",

    # 美股指数
    "nasdaq", "s&p 500", "s&p500", "dow jones",

    # 美联储 & 宏观（高信号事件）
    "federal reserve", "fomc", "rate cut", "rate hike", "treasury yield",

    # 重大市场事件
    "ipo", "acquisition", "merger", "bankruptcy", "layoffs", "market crash",

    # 地缘 & 政策
    "tariff", "sanctions", "trade war",

    # 加密
    "bitcoin", "justin sun",

    # 宏观衰退
    "recession",
]

# ==================== 监控的 RSS 源（仅高优先级）====================

ALERT_SOURCES = [
    {"name": "CNBC Top News",   "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "CNBC Technology", "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html"},
    {"name": "MarketWatch Top", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "Yahoo Finance",   "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "TechCrunch",      "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge",       "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "VentureBeat AI",  "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Reuters",         "url": "https://feeds.reuters.com/reuters/topNews"},
]

# ==================== 缓存（防重复推送）====================

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return set()
    now = datetime.now(timezone.utc)
    valid = set()
    with open(CACHE_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                h, ts = parts
                try:
                    t = datetime.fromisoformat(ts)
                    if t.tzinfo is None:
                        t = t.replace(tzinfo=timezone.utc)
                    if (now - t).days < CACHE_TTL_DAYS:
                        valid.add(h)
                except Exception:
                    pass
    return valid

def save_cache(all_hashes, existing_cache):
    now_str = datetime.now(timezone.utc).isoformat()
    # 读取现有文件保留时间戳
    timestamps = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2:
                    timestamps[parts[0]] = parts[1]
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        for h in all_hashes:
            ts = timestamps.get(h, now_str)
            f.write(f"{h}\t{ts}\n")

# ==================== 关键词匹配 ====================

def match_keywords(title, summary=""):
    text = f"{title} {summary}".lower()
    return [kw for kw in ALERT_KEYWORDS if kw in text]

# ==================== 发送预警邮件 ====================

def send_alert_email(articles):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    alert_to = os.environ.get("ALERT_EMAIL") or sender
    if not sender or not password or not alert_to:
        raise ValueError("未找到邮件配置")

    now = datetime.now(BJT)
    subject = f"🚨 新闻预警 {now.strftime('%m月%d日 %H:%M')} · {len(articles)} 条"

    lines = [f"触发 {len(articles)} 条关键词预警：\n"]
    for a in articles:
        kw_str = "、".join(a["keywords"])
        lines.append(f"[{a['source']}] {a['title']}")
        lines.append(f"关键词：{kw_str}")
        lines.append(f"链接：{a['link']}")
        lines.append("")

    msg = MIMEText("\n".join(lines), "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = alert_to

    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [alert_to], msg.as_string())
    print(f"预警邮件已发送：{len(articles)} 条")

# ==================== 主程序 ====================

def main():
    print("开始关键词扫描...")
    cache = load_cache()
    triggered = []
    all_seen_hashes = set(cache)

    for source in ALERT_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:15]:
                url = entry.get("link", "")
                if not url:
                    continue
                url_hash = hashlib.md5(url.encode()).hexdigest()
                all_seen_hashes.add(url_hash)
                if url_hash in cache:
                    continue
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:200].strip()
                matched = match_keywords(title, summary)
                if matched:
                    triggered.append({
                        "source": source["name"],
                        "title": title,
                        "link": url,
                        "keywords": matched,
                    })
        except Exception as e:
            print(f"扫描 {source['name']} 失败：{e}")

    print(f"扫描完成，触发预警 {len(triggered)} 条")

    if triggered:
        send_alert_email(triggered)

    save_cache(all_seen_hashes, cache)
    print("缓存已更新")

if __name__ == "__main__":
    main()
