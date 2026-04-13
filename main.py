from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import datetime
import requests
from xml.etree import ElementTree as ET
from openai import OpenAI

# ===================== 心流开放平台 配置 =====================
API_BASE_URL = "https://apis.iflow.cn/v1"
DEFAULT_MODEL = "qwen3-coder-plus"
API_KEY = "sk-60420ee6f652fb35e8008ddd9f608dff"
# ============================================================

class Main(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("✅ HLTV 新闻插件 加载成功！指令：/hltv /hltv新闻")

    # ====================== 正确的命令注册方式 ======================
    @filter.command("hltv", "hltv新闻")
    async def on_hltv_news(self, event: AstrMessageEvent):
        try:
            yield event.plain_result("🔍 正在抓取 HLTV 最新新闻...")
            
            news_list = self.fetch_hltv_news()
            if not news_list:
                yield event.plain_result("❌ 未抓取到新闻")
                return

            news_text = self.build_news_text(news_list)
            yield event.plain_result("🤖 正在生成总结...")
            
            summary = self.summarize_news(news_text)
            if not summary:
                yield event.plain_result("❌ AI 总结失败")
                return

            yield event.plain_result(f"📰 HLTV 今日新闻总结\n\n{summary}")

        except Exception as e:
            logger.error(f"插件错误: {str(e)}")
            yield event.plain_result(f"❌ 出错：{str(e)}")

    # ====================== 你原版的核心逻辑（完整保留） ======================
    def fetch_hltv_news(self):
        RSS_URL = "https://www.hltv.org/rss/news"
        try:
            response = requests.get(RSS_URL, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            news_list = []
            today = datetime.date.today()

            for item in root.findall('.//item')[:8]:
                title = item.find('title').text or "无标题"
                link = item.find('link').text or ""
                pubdate_str = item.find('pubDate').text or ""
                description = item.find('description').text or ""

                news_list.append({
                    "title": title,
                    "link": link,
                    "pubdate": pubdate_str,
                    "description": description.strip()
                })

            return news_list
        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return []

    def build_news_text(self, news_list):
        text = f"HLTV 新闻汇总 - {datetime.date.today()}\n\n"
        for i, news in enumerate(news_list, 1):
            text += f"{i}. {news['title']}\n"
            text += f"时间: {news['pubdate']}\n"
            text += f"内容: {news['description']}\n\n"
        return text

    def summarize_news(self, text):
        client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
        prompt = f"""
你是一位专业的 CS:GO / 电子竞技 新闻编辑。
请用中文为以下 HLTV 今日新闻生成一份**精炼且可读性强的每日总结**。

要求：
- 开头写一句整体概览
- 按重要性排序，分点总结
- 每条1-2句话
- 语言专业、流畅
- 最后加一句简短结语

以下是新闻内容：

{text}
"""
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"总结失败: {e}")
            return None

    async def terminate(self):
        logger.info("🛑 HLTV 新闻插件 已卸载")