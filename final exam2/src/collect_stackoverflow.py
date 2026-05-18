"""
collect_stackoverflow.py
========================
Stack Overflow 问答语料采集模块。

使用 Stack Exchange API 采集大数据/机器学习相关高质量问答，
输出为带 Front-Matter 的 Markdown 文件。
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.utils import get_logger, get_model_name, get_openai_client

logger = get_logger("collect_stackoverflow")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "external"

USER_AGENT = "final-exam-rag-corpus-bot/1.0 (edu project)"

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 1  # SO API 限速较宽松
MIN_SCORE = 3       # 最低分数阈值
PAGE_SIZE = 25      # 每页条数

# ── 搜索标签 ──────────────────────────────────────────────────────────────────

TAGS = [
    "apache-spark",
    "hadoop",
    "apache-kafka",
    "apache-flink",
    "apache-hive",
    "pandas",
    "numpy",
    "machine-learning",
    "deep-learning",
    "nlp",
    "etl",
    "data-warehouse",
    "bigdata",
    "mongodb",
    "elasticsearch",
]


# ── API 调用 ──────────────────────────────────────────────────────────────────

def _api_get(params: dict) -> dict | None:
    """调用 Stack Exchange API，带重试机制。"""
    base = "https://api.stackexchange.com/2.3"
    url = f"{base}/search/advanced?{urlencode(params)}"
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "identity",
    })

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("backoff"):
                logger.info("API backoff: %ds", data["backoff"])
                time.sleep(data["backoff"])

            return data

        except HTTPError as exc:
            if exc.code == 400:
                logger.warning("API 参数错误 [%d]", attempt)
                return None
            elif exc.code == 502:
                logger.warning("API 502 [%d]，%ds 后重试…", attempt, RETRY_DELAY * attempt)
                time.sleep(RETRY_DELAY * attempt)
            else:
                logger.warning("HTTP %d [%d]", exc.code, attempt)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        except (URLError, TimeoutError, OSError) as exc:
            logger.warning("请求失败 [%d]: %s", attempt, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    return None


def _strip_html(text: str) -> str:
    """移除 HTML 标签并解码实体。"""
    text = html.unescape(text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<pre>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _safe_name(text: str) -> str:
    """将文本转为安全的文件名。"""
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]", "", text)
    return text[:60] or "question"


# ── LLM 翻译 ──────────────────────────────────────────────────────────────────

_TRANSLATE_SYSTEM = (
    "你是专业翻译。将用户提供的英文技术文本翻译为中文。"
    "要求：保留代码块和变量名不翻译；术语可中英并列（如 Spark）；"
    "直接输出翻译结果，不要解释。"
)


def _translate_to_chinese(text: str, client=None) -> str:
    """使用 LLM 将英文技术文本翻译为中文。失败时返回原文。"""
    if not text or len(text.strip()) < 20:
        return text

    try:
        if client is None:
            client = get_openai_client()
        model = get_model_name()

        # 截断过长文本，避免 token 超限
        snippet = text[:3000]
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _TRANSLATE_SYSTEM},
                {"role": "user", "content": snippet},
            ],
            temperature=0,
            max_tokens=2048,
        )
        translated = resp.choices[0].message.content or text
        return translated.strip()

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.warning("翻译失败，使用原文: %s", exc)
        return text


# ── 采集逻辑 ──────────────────────────────────────────────────────────────────

def fetch_questions(tag: str, max_pages: int = 2) -> list[dict]:
    """
    按标签搜索高质量问答。

    参数：
      tag       : Stack Overflow 标签名
      max_pages : 最大翻页数

    返回：
      问答字典列表，每项包含 question_id / title / body / tags / score / answers
    """
    questions: list[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "site": "stackoverflow",
            "tagged": tag,
            "sort": "votes",
            "order": "desc",
            "pagesize": PAGE_SIZE,
            "page": page,
            "min": MIN_SCORE,
            "filter": "withbody",
        }

        data = _api_get(params)
        if not data:
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            answers = item.get("answer_count", 0)
            if answers < 1:
                continue

            questions.append({
                "question_id": item["question_id"],
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "tags": item.get("tags", []),
                "score": item.get("score", 0),
                "answer_count": answers,
                "link": item.get("link", ""),
            })

        quota = data.get("quota_remaining", "?")
        logger.info("  [%s] 第 %d 页: %d 条 (配额剩余: %s)", tag, page, len(items), quota)

        if not data.get("has_more", False):
            break

        time.sleep(REQUEST_DELAY)

    return questions


def fetch_top_answer(question_id: int) -> str | None:
    """获取问题的最高分回答正文。"""
    params = {
        "site": "stackoverflow",
        "sort": "votes",
        "order": "desc",
        "pagesize": 1,
        "filter": "withbody",
    }
    base = "https://api.stackexchange.com/2.3"
    url = f"{base}/questions/{question_id}/answers?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            items = data.get("items", [])
            if items:
                return items[0].get("body", "")

            if data.get("backoff"):
                time.sleep(data["backoff"])

            return None

        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    return None


def write_markdown(tag: str, question: dict, answer_body: str | None, client=None) -> Path:
    """将问答写入 Markdown 文件（翻译为中文）。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"so_{_safe_name(tag)}_{question['question_id']}.md"
    out_path = OUTPUT_DIR / file_name
    fetched_at = datetime.now(timezone.utc).isoformat()

    # 翻译标题和正文
    title_zh = _translate_to_chinese(question["title"], client=client)
    q_body = _strip_html(question["body"])
    q_body_zh = _translate_to_chinese(q_body, client=client)

    a_section = ""
    if answer_body:
        a_text = _strip_html(answer_body)
        a_text_zh = _translate_to_chinese(a_text, client=client)
        a_section = f"\n## 最佳回答\n\n{a_text_zh}\n"

    content = (
        f"# {title_zh}\n\n"
        f"- 来源: Stack Overflow\n"
        f"- 原始标题: {question['title']}\n"
        f"- 问题ID: {question['question_id']}\n"
        f"- 标签: {', '.join(question['tags'])}\n"
        f"- 得分: {question['score']}\n"
        f"- 回答数: {question['answer_count']}\n"
        f"- 抓取时间(UTC): {fetched_at}\n"
        f"- 原始链接: {question['link']}\n\n"
        f"## 问题\n\n{q_body_zh}\n"
        f"{a_section}"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── 主采集流程 ────────────────────────────────────────────────────────────────

def collect(max_per_tag: int = 10) -> tuple[list[str], list[str]]:
    """
    遍历所有标签采集高质量问答（翻译为中文）。

    参数：
      max_per_tag : 每个标签最多采集的问题数

    返回：
      (成功路径列表, 失败标签列表)
    """
    success: list[str] = []
    failed: list[str] = []

    # 复用同一个 OpenAI 客户端用于翻译
    client = get_openai_client()

    for tag in TAGS:
        logger.info("采集标签: %s", tag)
        questions = fetch_questions(tag, max_pages=2)

        if not questions:
            logger.warning("  [%s] 无结果", tag)
            failed.append(tag)
            continue

        count = 0
        for q in questions:
            if count >= max_per_tag:
                break

            answer_body = fetch_top_answer(q["question_id"])
            time.sleep(REQUEST_DELAY)

            out_path = write_markdown(tag, q, answer_body, client=client)
            success.append(str(out_path))
            logger.info("  已写入: %s (score=%d)", out_path.name, q["score"])
            count += 1

        logger.info("  [%s] 完成: %d 篇", tag, count)

    return success, failed


def main() -> None:
    success, failed = collect()
    logger.info("Stack Overflow 采集完成: 成功 %d，失败 %d", len(success), len(failed))
    for p in success[:5]:
        logger.info("  - %s", p)
    if len(success) > 5:
        logger.info("  ... 共 %d 篇", len(success))


if __name__ == "__main__":
    main()
