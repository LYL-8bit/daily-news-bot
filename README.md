# daily-news-bot

每天自动抓取财经/科技 RSS 新闻，用 Grok 总结成中文晚报，推送到 **Telegram + 邮箱**。
另含「关键词实时预警」和「周报 / 月报」功能。全部跑在 GitHub Actions 上，无需服务器。

---

## 功能概览

| 功能 | 脚本 | Workflow | 频率（北京时间） |
|------|------|----------|------------------|
| 每日晚报 | `news.py` | `.github/workflows/news.yml` | 每天 20:07 |
| 关键词预警 | `alert.py` | `.github/workflows/alert.yml` | 每 4 小时（8/12/16/20/0/4 点） |
| 周报 / 月报 | `weekly.py` | `.github/workflows/weekly.yml` | 周报每周日 21:07；月报每月 1 日 21:07 |

> GitHub Actions 的 cron 用 UTC，且高峰期常有数十分钟延迟，实际推送时间会比设定略晚。

---

## 工作流程

```
RSS 源 ──抓取──> 按关键词/分类打分排序 ──取 Top 90──> Grok 总结
                                                        │
                                          ┌─────────────┴─────────────┐
                                       Telegram                     邮箱(HTML)
```

- 晚报抓取近 **24 小时**内的新闻，覆盖美股交易时段（北京时间 21:30~04:00 的隔夜新闻）。
- 每日晚报的 Grok 摘要会存档到 `archive/YYYY-MM-DD.txt`，供周报 / 月报二次总结使用。
- 预警只扫高优先级财经/科技源，命中关键词即邮件通知；已推送文章记录在 `alert_cache.txt`，7 天内不重复推送。

---

## GitHub Secrets 配置

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 用途 | 必需 |
|--------|------|------|
| `GROK_API_KEY` | xAI Grok API 密钥（[console.x.ai](https://console.x.ai)） | ✅ |
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token（找 @BotFather 创建） | ✅ |
| `TELEGRAM_CHAT_ID` | 接收消息的聊天 ID | ✅ |
| `EMAIL_SENDER` | 发件 QQ 邮箱地址 | ✅ |
| `EMAIL_PASSWORD` | QQ 邮箱 **SMTP 授权码**（不是登录密码） | ✅ |
| `EMAIL_RECIPIENTS` | 晚报/周报收件人，多个用英文逗号 `,` 分隔 | ✅ |
| `ALERT_EMAIL` | 关键词预警的收件人；留空则发给 `EMAIL_SENDER` | 可选 |

> QQ 邮箱授权码获取：邮箱设置 → 账号 → 开启 SMTP 服务 → 生成授权码。

---

## 自定义

- **RSS 源**：编辑 `news.py` 的 `RSS_SOURCES`（含分类与权重 `CATEGORY_WEIGHTS`）。
- **选稿打分关键词**：`news.py` 的 `IMPORTANT_KEYWORDS`。
- **预警关键词**：`alert.py` 的 `ALERT_KEYWORDS`（大小写不敏感，词边界匹配）。
- **预警监控的源**：`alert.py` 的 `ALERT_SOURCES`。
- **Grok 模型 / 提示词**：各脚本的 `call_grok()` 函数。

---

## 本地测试

```bash
pip install -r requirements.txt

# 测试所有 RSS 源是否可用（Windows 终端需先 set PYTHONIOENCODING=utf-8）
python news.py --test

# 手动跑一次晚报（需先在环境变量里配置上述 Secrets）
python news.py
```

周报 / 月报可在 **Actions → Weekly & Monthly Summary → Run workflow** 手动触发，
勾选 `force` 可忽略「存档天数不足」的限制用于测试。

---

## 注意事项

- 失效或停更的 RSS 源会在抓取时静默跳过，不影响其他源；可定期用 `python news.py --test` 体检。
- 存档与缓存由 GitHub Actions 自动 commit 回仓库（`if: always()` 保证发送失败也不丢存档）。
- 修改 `.github/workflows/` 下的文件需要 token 具备 `workflow` 权限。
