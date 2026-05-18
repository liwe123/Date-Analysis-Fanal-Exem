"""
collect_csdn.py
===============
CSDN 博客技术文章采集模块。

通过 CSDN 搜索 API 采集大数据/机器学习相关技术博客，
输出为带 Front-Matter 的 Markdown 文件。
"""

from __future__ import annotations

import html as html_lib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.utils import get_logger

logger = get_logger("collect_csdn")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "external"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

MAX_RETRIES = 3
RETRY_DELAY = 3
REQUEST_DELAY = 3  # CSDN 限速较严，每次请求间隔 3 秒
MAX_PER_KEYWORD = 8

# ── 搜索关键词 ────────────────────────────────────────────────────────────────

KEYWORDS = [
    "Spark 大数据教程",
    "Hadoop 入门实战",
    "Flink 流处理",
    "Kafka 消息队列",
    "数据仓库 Hive",
    "大数据面试题",
    "机器学习算法",
    "深度学习入门",
    "ETL 数据清洗",
    "数据湖架构",
]


# ── 网络请求 ──────────────────────────────────────────────────────────────────

def _fetch_url(url: str) -> str | None:
    """获取 URL 内容，带重试机制。"""
    req = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except HTTPError as exc:
            if exc.code == 429:
                wait = RETRY_DELAY * attempt * 2
                logger.warning("429 限流 [%d]，%ds 后重试…", attempt, wait)
                time.sleep(wait)
            elif exc.code == 403:
                logger.warning("403 禁止访问，可能被反爬: %s", url[:80])
                return None
            else:
                logger.warning("HTTP %d [%d]", exc.code, attempt)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
        except (URLError, TimeoutError, OSError) as exc:
            logger.warning("请求失败 [%d]: %s", attempt, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    return None


# ── 搜索接口 ──────────────────────────────────────────────────────────────────

def _search_articles(keyword: str, page: int = 1) -> list[dict]:
    """
    调用 CSDN 搜索 API 获取文章列表。

    返回：
      [{"title": str, "url": str, "description": str, "article_id": str}, ...]
    """
    params = urlencode({
        "q": keyword,
        "t": "all",
        "p": page,
        "s": "new",
        "tm": 0,
    })
    url = f"https://so.csdn.net/api/v3/search?{params}"
    raw = _fetch_url(url)
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("CSDN 搜索 JSON 解析失败: %s", keyword)
        return []

    items = data.get("result_vos", [])
    if isinstance(items, dict):
        items = items.get("result_vos", [])

    results: list[dict] = []
    for item in items:
        article_url = item.get("url", "")
        if not article_url or "blog.csdn.net" not in article_url:
            continue

        # 提取文章 ID
        aid_match = re.search(r"/article/details/(\d+)", article_url)
        article_id = aid_match.group(1) if aid_match else ""

        results.append({
            "title": _strip_html(item.get("title", "")),
            "url": article_url.split("?")[0],  # 去掉追踪参数
            "description": _strip_html(item.get("description", "")),
            "article_id": article_id,
            "author": item.get("nickname", ""),
            "view_num": item.get("view_num", 0),
        })

    return results


# ── 文章正文提取 ──────────────────────────────────────────────────────────────

def _extract_article(html_content: str) -> str:
    """从 CSDN 文章页面提取正文。"""
    # 尝试 <article> 标签
    match = re.search(r"<article[^>]*>(.*?)</article>", html_content, re.DOTALL)
    if match:
        return _clean_html(match.group(1))

    # 尝试 article_content div
    match = re.search(
        r'<div[^>]*id=["\']?article_content["\']?[^>]*>(.*?)</div>\s*<(?:div|section)',
        html_content, re.DOTALL,
    )
    if match:
        return _clean_html(match.group(1))

    # 尝试 content_views
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*content_views[^"\']*["\'][^>]*>(.*?)</div>',
        html_content, re.DOTALL,
    )
    if match:
        return _clean_html(match.group(1))

    return ""


def _clean_html(text: str) -> str:
    """清理 HTML 为纯文本。"""
    text = html_lib.unescape(text)
    # 保留代码块标记
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    # 标题转为 Markdown
    for level in range(1, 7):
        text = re.sub(
            rf"<h{level}[^>]*>(.*?)</h{level}>",
            rf"\n{'#' * level} \1\n",
            text, flags=re.DOTALL,
        )
    # 段落换行
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    # 移除剩余标签
    text = re.sub(r"<[^>]+>", " ", text)
    # 规范化空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_html(text: str) -> str:
    """简单移除 HTML 标签。"""
    text = html_lib.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _safe_name(text: str) -> str:
    """将文本转为安全的文件名。"""
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]", "", text)
    return text[:50] or "article"


# ── 写入文件 ──────────────────────────────────────────────────────────────────

def write_markdown(keyword: str, article: dict, body: str) -> Path:
    """将文章写入 Markdown 文件。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"csdn_{_safe_name(keyword)}_{article['article_id']}.md"
    out_path = OUTPUT_DIR / file_name
    fetched_at = datetime.now(timezone.utc).isoformat()

    # 如果正文太短，用描述补充
    if len(body) < 100 and article.get("description"):
        body = article["description"]

    content = (
        f"# {article['title']}\n\n"
        f"- 来源: CSDN 博客\n"
        f"- 作者: {article.get('author', '未知')}\n"
        f"- 搜索关键词: {keyword}\n"
        f"- 抓取时间(UTC): {fetched_at}\n"
        f"- 原始链接: {article['url']}\n\n"
        f"## 正文\n\n{body}\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── 主采集流程 ────────────────────────────────────────────────────────────────

def collect(max_per_keyword: int = MAX_PER_KEYWORD) -> tuple[list[str], list[str]]:
    """
    遍历关键词采集 CSDN 技术博客。

    返回：
      (成功路径列表, 失败关键词列表)
    """
    success: list[str] = []
    failed: list[str] = []

    for keyword in KEYWORDS:
        logger.info("搜索关键词: %s", keyword)
        articles = _search_articles(keyword, page=1)
        time.sleep(REQUEST_DELAY)

        if not articles:
            logger.warning("  [%s] 无结果", keyword)
            failed.append(keyword)
            continue

        count = 0
        for article in articles:
            if count >= max_per_keyword:
                break

            # 获取文章正文
            html_content = _fetch_url(article["url"])
            if not html_content:
                continue

            body = _extract_article(html_content)
            if len(body) < 50:
                logger.debug("  正文过短，跳过: %s", article["title"][:30])
                continue

            out_path = write_markdown(keyword, article, body)
            success.append(str(out_path))
            logger.info("  已写入: %s", out_path.name)
            count += 1
            time.sleep(REQUEST_DELAY)

        logger.info("  [%s] 完成: %d 篇", keyword, count)

    return success, failed


def main() -> None:
    success, failed = collect()
    logger.info("CSDN 采集完成: 成功 %d，失败 %d", len(success), len(failed))
    for p in success[:5]:
        logger.info("  - %s", p)
    if len(success) > 5:
        logger.info("  ... 共 %d 篇", len(success))


if __name__ == "__main__":
    main()
