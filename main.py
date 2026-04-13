from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import os
import datetime
import requests
from xml.etree import ElementTree as ET
from openai import OpenAI

# ===================== 心流开放平台 配置 =====================
API_BASE_URL = "https://apis.iflow.cn/v1"
DEFAULT_MODEL = "deepseek-r1"
API_KEY = "sk-60420ee6f652fb35e8008ddd9f608dff"
# ============================================================

class Main(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化"""
        logger.info("✅ HLTV 新闻插件 加载成功！指令：/hltv /hltv新闻")

    # ====================== 核心指令 ======================
    @filter.command("hltv")
    @filter.command("hltv新闻")
    async def on_hltv_news(self, event: AstrMessageEvent):
        """获取 HLTV 今日新闻 + AI 总结"""
        try:
            # 1. 抓取新闻
            yield event.plain_result("🔍 正在抓取 HLTV 最新新闻...")
            news_list = self.fetch_hltv_news()
            if not news_list:
                yield event.plain_result("❌ 未抓取到新闻")
                return

            # 2. 生成文本
            news_text = self.build_news_text(news_list)

            # 3. AI 总结
            yield event.plain_result("🤖 正在生成总结...")
            summary = self.summarize_news(news_text)
            if not summary:
                yield event.plain_result("❌ AI 总结失败")
                return

            # 4. 发送结果
            yield event.plain_result(f"📰 HLTV 今日新闻总结\n\n{summary}")

        except Exception as e:
            logger.error(f"新闻插件错误: {e}")
            yield event.plain_result(f"❌ 出错：{str(e)}")

    # ====================== 工具方法 ======================
    def fetch_hltv_news(self):
        RSS_URL = "https://www.hltv.org/rss/news"
        try:
            resp = requests.get(RSS_URL, timeout=15)
            root = ET.fromstring(resp.content)
            news = []
            today = datetime.date.today()

            for item in root.findall(".//item")[:8]:  # 最多8条
                title = item.find("title").text or ""
                link = item.find("link").text or ""
                pub = item.find("pubDate").text or ""
                desc = item.find("description").text or ""
                news.append({
                    "title": title,
                    "link": link,
                    "pubdate": pub,
                    "description": desc.strip()
                })
            return news
        except:
            return []

    def build_news_text(self, news_list):
        text = ""
        for i, n in enumerate(news_list, 1):
            text += f"{i}. {n['title']}\n{n['description']}\n\n"
        return text

    def summarize_news(self, text):
        client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
        prompt = f"""你是专业CSGO电竞编辑，请用简洁、专业、分点的中文总结以下HLTV新闻：

{text}

要求：简洁、重点突出、适合阅读。"""

        try:
            res = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"总结失败: {e}")
            return None

    async def terminate(self):
        """插件卸载时调用"""
        logger.info("🛑 HLTV 新闻插件 已卸载")