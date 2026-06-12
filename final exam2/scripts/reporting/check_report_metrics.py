"""
check_report_metrics.py
=======================
检查报告文档中的关键指标与命令示例是否保持一致。
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger("check_report_metrics")
TEXT_SUFFIXES = {".html", ".ipynb", ".md", ".py", ".txt"}
SKIP_NAMES = {"check_report_metrics.py"}
SCAN_PATHS = (
    BASE_DIR / "README.md",
    BASE_DIR / "SUBMISSION.md",
    BASE_DIR / "pipeline_demo.ipynb",
    BASE_DIR / "report",
    BASE_DIR / "scripts",
)
FORBIDDEN_PATTERNS = {
    "旧 CLI 脚本入口": re.compile(r"python\s+(?:src/main[.]py|main[.]py)\b"),
    "旧测试数量 82": re.compile(r"82\s*个(?:自动化)?(?:测试|用例)?"),
    "旧语料数量 54": re.compile(r"54\s*个(?:文档|语料|样本|数据块)?"),
    "旧越界准确率": re.compile(r"11[.]" r"1%"),
    "旧越界命中": re.compile(r"\b1" r"/9\b"),
    "Notebook 乱码占位": re.compile(r"[?]{4,}"),
}


# ── 文件扫描 ──────────────────────────────────────────────
def _iter_text_files() -> list[Path]:
    files = []
    for path in SCAN_PATHS:
        if path.is_file():
            candidates = [path]
        else:
            candidates = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        for candidate in candidates:
            if candidate.name in SKIP_NAMES or candidate.suffix.lower() not in TEXT_SUFFIXES:
                continue
            files.append(candidate)
    return sorted(set(files))


def _scan_file(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        LOGGER.warning("跳过非 UTF-8 文本文件 %s: %s", path.relative_to(BASE_DIR), exc)
        return []

    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule_name, pattern in FORBIDDEN_PATTERNS.items():
            match = pattern.search(line)
            if match is None:
                continue
            findings.append(
                {
                    "path": str(path.relative_to(BASE_DIR)),
                    "line": line_no,
                    "rule": rule_name,
                    "match": match.group(0),
                }
            )
    return findings


def _run_checks() -> tuple[list[dict], int]:
    files = _iter_text_files()
    findings = []
    for path in files:
        findings.extend(_scan_file(path))
    return findings, len(files)


# ── 命令入口 ──────────────────────────────────────────────
def main() -> int:
    """运行报告指标与命令示例一致性检查。"""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
    findings, file_count = _run_checks()

    if findings:
        LOGGER.error("报告一致性检查失败，共发现 %s 处问题。", len(findings))
        for finding in findings:
            LOGGER.error(
                "%s:%s: %s -> %s",
                finding["path"],
                finding["line"],
                finding["rule"],
                finding["match"],
            )
        return 1

    LOGGER.info("报告一致性检查通过，共扫描 %s 个文件。", file_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
