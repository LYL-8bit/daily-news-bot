import os
import sys
import re
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
ARCHIVE_DIR = "archive"

# ==================== 加载存档 ====================

def load_archives(days):
    now = datetime.now(BJT)
    archives = []
    for i in range(days, 0, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(ARCHIVE_DIR, f"{date}.txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                archives.append((date, f.read().strip()))
    return archives

# ==================== 调用 Grok ====================

def call_grok(archives, is_monthly):
    api_key = os.environ.get("GROK_API_KEY")
    if not api_key:
        raise ValueError("未找到 GROK_API_KEY")

    period = "月报" if is_monthly else "周报"
    span = f"过去 {len(archives)} 天"
    content = "\n\n---\n\n".join([f"【{date}】\n{text}" for date, text in archives])

    prompt = f"""你是一个财经与科技新闻编辑。以下是{span}的每日新闻摘要，请总结成一份{period}。

要求：
1. 全文 2000-3000 字，信息密度高，不废话
2. 识别本期 3-5 条主线（跨多天持续发酵的事件及其演变）
3. 分析美股/科技/AI 的整体趋势
4. 指出后续值得持续关注的议题
5. 用中文

固定格式：

📅 本期主线
- （跨天延续的重要事件）

📈 美股 & 市场
-

🤖 AI & 科技
-

🌍 宏观 & 地缘
-

🔭 后续关注
-

每日摘要：
{content}"""

    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "grok-4.3",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.3,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ==================== HTML 邮件 ====================

SECTION_ICONS = ("📅", "📈", "🤖", "🌍", "🔭")

def text_to_html(text, subject):
    def linkify(s):
        return re.sub(
            r'(https?://[^\s\]）】）]+)',
            r'<a href="\1" style="color:#2563eb;word-break:break-all;">\1</a>',
            s,
        )

    body_parts = []
    for line in text.split("\n"):
        s = line.rstrip()
        if not s:
            body_parts.append('<div style="height:8px"></div>')
        elif any(s.startswith(icon) for icon in SECTION_ICONS):
            body_parts.append(
                f'<h2 style="margin:28px 0 12px;padding:10px 14px;'
                f'border-left:4px solid #2563eb;background:#f0f7ff;'
                f'border-radius:0 6px 6px 0;font-size:15px;color:#1e3a5f;font-weight:700;">'
                f'{s}</h2>'
            )
        elif s.startswith("    ") or s.startswith("\t"):
            body_parts.append(
                f'<p style="margin:3px 0 3px 24px;color:#6b7280;font-size:13px;">'
                f'{linkify(s.strip())}</p>'
            )
        elif s.startswith("- ") or s.startswith("• "):
            body_parts.append(
                f'<p style="margin:8px 0;color:#1f2937;">🔹 {linkify(s[2:])}</p>'
            )
        else:
            body_parts.append(f'<p style="margin:6px 0;color:#374151;">{linkify(s)}</p>')

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:16px 0;background:#f0f4f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
  <div style="max-width:660px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.10);">
    <div style="background:#1e3a5f;padding:24px 28px;">
      <div style="font-size:11px;color:#93c5fd;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">Daily News Bot</div>
      <div style="font-size:22px;font-weight:700;color:#f0f9ff;line-height:1.3;">{subject}</div>
    </div>
    <div style="padding:20px 28px 16px;line-height:1.8;font-size:15px;">
      {chr(10).join(body_parts)}
    </div>
    <div style="padding:12px 28px 16px;border-top:1px solid #e5e7eb;text-align:center;">
      <p style="margin:0;color:#d1d5db;font-size:11px;">Powered by Grok 4.3 · daily-news-bot</p>
    </div>
  </div>
</body>
</html>"""


def send_email(subject, summary):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "")
    if not sender or not password or not recipients_raw:
        raise ValueError("未找到邮件配置")

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(summary, "plain", "utf-8"))
    msg.attach(MIMEText(text_to_html(summary, subject), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())

# ==================== 主程序 ====================

def main():
    is_monthly = "--monthly" in sys.argv
    days = 30 if is_monthly else 7
    label = "月报" if is_monthly else "周报"
    min_days = 10 if is_monthly else 3

    print(f"加载过去 {days} 天存档...")
    archives = load_archives(days)
    print(f"找到 {len(archives)} 天存档")

    if len(archives) < min_days:
        print(f"存档不足（{len(archives)} 天，需至少 {min_days} 天），跳过{label}")
        return

    now = datetime.now(BJT)
    print(f"调用 Grok 生成{label}...")
    summary = call_grok(archives, is_monthly)

    if is_monthly:
        subject = f"📅 {now.strftime('%Y年%m月')} 月报"
    else:
        subject = f"📅 周报 · {now.strftime('%m月%d日')}"

    print(f"发送{label}邮件...")
    send_email(subject, summary)
    print(f"{label}推送完成！")


if __name__ == "__main__":
    main()
