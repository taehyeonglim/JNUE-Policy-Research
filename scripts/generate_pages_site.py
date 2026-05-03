"""Generate the GitHub Pages static dashboard for the JNUE policy project."""

from __future__ import annotations

import html
import hashlib
import shutil
import sys
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analyzer import (
    get_competition_rates,
    get_major_comparison,
    get_major_heatmap_data,
    get_overview_metrics,
    get_student_summary,
    get_timeline_data,
)
from src.charts import create_major_heatmap, create_status_table_chart, create_timeline_chart
from src.data_loader import GRADUATE_SCHOOL_STATUS


DOCS_DIR = ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
REPORT_PATH = ROOT / "reports" / "전주교대_교육전문대학원_설치_정책연구_초안.hwpx"
REPORT_ASSET = ASSETS_DIR / REPORT_PATH.name
POLICY_AMENDMENT_PATH = ROOT / "reports" / "audit" / "전주교대_교육전문대학원_교원신분보장_학칙개정안_2026-05-03.md"
COMPARISON_TABLE_PATH = ROOT / "reports" / "audit" / "전주교대_교육전문대학원_학칙개정_신구조문대비표_2026-05-03.md"
CHAPTER_DIR = ROOT / "reports" / "chapters"
DEBATE_DIR = ROOT / "reports" / "debates"


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _metric(label: str, value: str, note: str = "") -> str:
    note_html = f"<span>{_escape(note)}</span>" if note else ""
    return f"""
    <article class="metric-card">
      <div class="metric-label">{_escape(label)}</div>
      <strong>{_escape(value)}</strong>
      {note_html}
    </article>
    """


def _table(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    if df.empty:
        return '<p class="muted">표시할 데이터가 없습니다.</p>'
    view = df[columns].copy() if columns else df.copy()
    header = "".join(f"<th>{_escape(col)}</th>" for col in view.columns)
    rows = []
    for _, row in view.iterrows():
        rows.append("<tr>" + "".join(f"<td>{_escape(row[col])}</td>" for col in view.columns) + "</tr>")
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _markdown_table(lines: list[str]) -> str:
    headers = [cell.strip() for cell in lines[0].strip().strip("|").split("|")]
    body_lines = lines[2:]
    head = "".join(f"<th>{_escape(header)}</th>" for header in headers)
    rows = []
    for line in body_lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append("<tr>" + "".join(f"<td>{_inline_markdown(cell)}</td>" for cell in cells) + "</tr>")
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _inline_markdown(text: str) -> str:
    escaped = _escape(text)
    escaped = escaped.replace("&lt;신설&gt;", "<strong>&lt;신설&gt;</strong>")
    while "**" in escaped:
        start = escaped.find("**")
        end = escaped.find("**", start + 2)
        if end < 0:
            break
        escaped = escaped[:start] + "<strong>" + escaped[start + 2 : end] + "</strong>" + escaped[end + 2 :]
    while "`" in escaped:
        start = escaped.find("`")
        end = escaped.find("`", start + 1)
        if end < 0:
            break
        escaped = escaped[:start] + "<code>" + escaped[start + 1 : end] + "</code>" + escaped[end + 1 :]
    return escaped


def _markdown_to_html(markdown_text: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    quote_lines: list[str] = []
    lines = markdown_text.splitlines()
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append("<p>" + _inline_markdown(" ".join(paragraph)) + "</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            blocks.append("<blockquote>" + "".join(f"<p>{line}</p>" for line in quote_lines) + "</blockquote>")
            quote_lines = []

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_quote()
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip().replace("|", "").replace(":", "").replace(" ", "")) <= {"-"}:
            flush_paragraph()
            flush_list()
            flush_quote()
            table_lines = [stripped, lines[i + 1].strip()]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            blocks.append(_markdown_table(table_lines))
            continue
        if stripped.startswith("#"):
            flush_paragraph()
            flush_list()
            flush_quote()
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped[level:].strip()
            level = max(level + 1, 3)
            blocks.append(f"<h{level}>{_inline_markdown(text)}</h{level}>")
            i += 1
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            flush_quote()
            list_items.append(_inline_markdown(stripped[2:].strip()))
            i += 1
            continue
        if len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:5]:
            flush_paragraph()
            flush_quote()
            list_items.append(_inline_markdown(stripped.split(". ", 1)[1].strip()))
            i += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            quote_lines.append(_inline_markdown(stripped.lstrip(">").strip()))
            i += 1
            continue
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    flush_list()
    flush_quote()
    return "\n".join(blocks)


def _read_markdown(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _document_panel(path: Path, fallback_title: str) -> str:
    content = _read_markdown(path)
    if not content:
        return f'<p class="muted">{_escape(path.name)} 파일을 찾을 수 없습니다.</p>'
    return f'<article class="prose">{_markdown_to_html(content)}</article>'


def _redline(text: str) -> str:
    return f'<span class="revision">{_escape(text)}</span>'


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{item}</p>" for item in items)


def _split_comparison_view() -> str:
    rows = [
        {
            "article": "제2조",
            "original": [
                "<strong>제2조(교육목적 및 교육목표)</strong>",
                "① 우리 대학교의 교육목적은 도덕성과 전문성을 갖춘 유능하고 창의적인 초등교원을 양성하는 데 있다.",
            ],
            "revised": [
                "<strong>제2조(교육목적 및 교육목표)</strong>",
                f"① 우리 대학교의 교육목적은 도덕성과 전문성을 갖춘 유능하고 창의적인 초등교원을 양성하고, {_redline('초등교육의 발전에 기여하는 교육전문가 및 연구인력을 양성')}하는 데 있다.",
            ],
        },
        {
            "article": "제3조",
            "original": [
                "<strong>제3조(편제 및 학생정원)</strong>",
                "① 우리 대학교에 초등교육전공과정과 교육대학원을 둔다.",
                "② 우리 대학교의 입학정원은 「고등교육법시행령」 제28조제3항에 따라 매년 조정되는 인원으로 한다.",
                "③ 「고등교육법시행령」 제29조제2항에 해당하는 자를 선발하는 경우에는 그 정원이 따로 있는 것으로 본다.",
            ],
            "revised": [
                "<strong>제3조(편제 및 학생정원)</strong>",
                f"① 우리 대학교에 초등교육전공과정, 교육대학원 {_redline('및 교육전문대학원')}을 둔다.",
                f"② 우리 대학교의 입학정원은 「고등교육법 시행령」 제28조제3항 {_redline('및 관계 법령')}에 따라 매년 조정되는 인원으로 한다.",
                "③ 「고등교육법 시행령」 제29조제2항에 해당하는 자를 선발하는 경우에는 그 정원이 따로 있는 것으로 본다.",
                f"{_redline('④ 교육전문대학원의 학위과정, 전공, 학생정원 및 운영에 관한 사항은 관계 법령과 이 학칙 및 교육전문대학원 학칙으로 정한다.')}",
            ],
        },
        {
            "article": "제4조",
            "original": [
                "<strong>제4조(교육대학원)</strong>",
                "교육대학원의 학사운영에 필요한 사항은 교육대학원학칙으로 정한다.",
            ],
            "revised": [
                f"<strong>{_redline('제4조(대학원)')}</strong>",
                "① 교육대학원의 학사운영에 필요한 사항은 교육대학원 학칙으로 정한다.",
                f"{_redline('② 교육전문대학원의 조직, 학위과정, 전공, 교육과정, 수업, 학위수여, 학생정원 및 학사운영에 필요한 사항은 교육전문대학원 학칙으로 정한다.')}",
                f"{_redline('③ 교육대학원과 교육전문대학원은 교육과정, 교원, 시설, 행정지원 등을 상호 연계하여 운영할 수 있으며, 이에 필요한 사항은 총장이 따로 정한다.')}",
            ],
        },
        {
            "article": "제4조의2",
            "original": [
                "<strong>&lt;신설&gt;</strong>",
                "현행 학칙에는 교육전문대학원 설치에 따른 전임교원의 소속 변경, 겸무·겸보, 교수시간 통합 산정, 신분보장 및 실적 인정 조항이 없다.",
            ],
            "revised": [
                f"<strong>{_redline('제4조의2(전임교원의 소속·겸무·교수시간 및 신분보장)')}</strong>",
                f"{_redline('① 전임교원은 초등교육전공과정의 심화과정, 교육대학원 또는 교육전문대학원의 학과·전공에 소속될 수 있다.')}",
                f"{_redline('② 총장은 교육·연구 및 학사운영상 필요하다고 인정하는 경우 관계 법령과 이 학칙 및 관련 규정에 따라 전임교원의 소속 변경, 겸무 또는 겸보를 명할 수 있다.')}",
                f"{_redline('③ 소속 변경 또는 겸무·겸보는 전공 적합성, 연구실적, 교육전문대학원 전공 운영 필요성, 초등교육전공과정의 교육과정 운영에 미치는 영향, 해당 교원의 의견 및 관련 위원회의 심의를 고려하여 정한다.')}",
                f"{_redline('④ 교육전문대학원 소속 전임교원이 초등교육전공과정의 심화과정 또는 교육대학원을 겸무·겸보하는 경우에는 그 겸무·겸보 범위에서 해당 심화과정 또는 교육대학원 소속 전임교원으로 본다.')}",
                f"{_redline('⑤ 교육전문대학원 소속 전임교원은 초등교육전공과정, 교육대학원 및 교육전문대학원의 강의, 교육실습, 논문지도, 학위논문 심사, 학생지도, 전공운영 및 관련 보직을 담당할 수 있다.')}",
                f"{_redline('⑥ 교육전문대학원 소속 전임교원이 담당하는 초등교육전공과정, 교육대학원 및 교육전문대학원의 강의시간은 제47조에 따른 교수시간 및 관련 규정에 따른 책임시간에 포함한다.')}",
                f"{_redline('⑦ 총장은 교육전문대학원 설치·운영으로 초등교육전공과정의 수업권이 침해되지 아니하도록 매 학년도 교원 배치 및 수업분담 계획을 수립하여야 한다.')}",
                f"{_redline('⑧ 전임교원은 교육전문대학원 소속 변경 또는 겸무·겸보를 이유로 임용, 승진, 재임용, 보수, 교육·연구 및 학생지도 비용, 교원업적평가, 성과평가, 연구년, 복무, 후생복지 및 그 밖의 근무조건에서 불리하게 처우받지 아니한다.')}",
                f"{_redline('⑨ 교육전문대학원 소속 또는 겸무·겸보 교원의 교육전문대학원 강의, 논문지도, 학위논문 심사, 전공운영, 학생지도, 현장연계 연구 및 초등교육전공과정 겸무 업무는 교육·연구 및 학생지도 비용, 교원업적평가 및 성과평가에서 실적으로 인정한다.')}",
                f"{_redline('⑩ 시행에 필요한 사항은 학사운영규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준, 직제 및 사무분장 규정, 보수·수당 관련 규정으로 정한다.')}",
            ],
        },
        {
            "article": "제5조",
            "original": [
                "<strong>제5조(하부조직)</strong>",
                "② 교무처는 학칙관리, 교육공무원인사, 비전임 교원인사, 교육과정관리, 학적관리, 수업 및 성적관리, 교육실습, 학술연구지원, 그 밖의 총장이 정하는 사항을 분장한다.",
            ],
            "revised": [
                "<strong>제5조(하부조직)</strong>",
                f"② 교무처는 학칙관리, 교육공무원인사, 비전임 교원인사, 교육과정관리, 학적관리, 수업 및 성적관리, 교육실습, 학술연구지원, {_redline('교육전문대학원 설치에 따른 교원 소속·겸무·겸보 및 수업분담 조정')}, 그 밖의 총장이 정하는 사항을 분장한다.",
            ],
        },
        {
            "article": "제5조의4",
            "original": [
                "<strong>&lt;신설&gt;</strong>",
                "현행 학칙에는 교육전문대학원장, 전공주임교수, 교육전문대학원 보직의 설치 근거가 없다.",
            ],
            "revised": [
                f"<strong>{_redline('제5조의4(교육전문대학원장 등)')}</strong>",
                f"{_redline('① 교육전문대학원에 교육전문대학원장을 두며, 교육전문대학원장은 부교수 이상의 전임교원으로 보한다.')}",
                f"{_redline('② 교육전문대학원장은 총장의 명을 받아 교육전문대학원의 교무를 총괄하고, 소속 교직원을 감독하며, 학생을 지도한다.')}",
                f"{_redline('③ 교육전문대학원에 전공주임교수 등 필요한 보직을 둘 수 있으며, 전공주임교수는 전임교원으로 보한다.')}",
                f"{_redline('④ 교육전문대학원 전공주임교수는 초등교육전공과정의 교과과장 또는 교육대학원 전공주임교수를 겸보할 수 있다.')}",
                f"{_redline('⑤ 교육전문대학원장, 전공주임교수 및 그 밖의 보직에 관한 세부사항은 교육전문대학원 학칙 및 직제 관련 규정으로 정한다.')}",
            ],
        },
        {
            "article": "제29조의2",
            "original": [
                "<strong>제29조의2(수업방법)</strong>",
                "수업은 주간에 실시함을 원칙으로 한다. 다만, 특별한 경우 총장의 허가를 얻어 야간수업, 방송·통신에 의한 수업 및 현장실습수업 등을 할 수 있고, 이에 필요한 세부사항은 총장이 따로 정한다.",
            ],
            "revised": [
                "<strong>제29조의2(수업방법)</strong>",
                "① 초등교육전공과정의 수업은 주간에 실시함을 원칙으로 한다. 다만, 특별한 경우 총장의 허가를 얻어 야간수업, 방송·통신에 의한 수업 및 현장실습수업 등을 할 수 있고, 이에 필요한 세부사항은 총장이 따로 정한다.",
                f"{_redline('② 교육대학원 및 교육전문대학원의 수업은 각 대학원 학칙에 따라 야간, 주말, 계절제, 집중수업, 원격수업, 현장실습수업 등으로 운영할 수 있다.')}",
                f"{_redline('③ 총장은 제2항에 따른 수업 운영이 초등교육전공과정의 필수수업, 교육실습 및 학생지도에 지장을 주지 아니하도록 수업시간표와 교원 수업분담을 조정하여야 한다.')}",
            ],
        },
        {
            "article": "제47조",
            "original": [
                "<strong>제47조(교수시간)</strong>",
                "① 우리 대학교 교원(강사 제외)의 교수시간은 매 학년도 30주를 기준으로 주당 9시간을 원칙으로 한다. 다만, 학사운영상 특별히 필요하다고 인정하는 경우에는 총장이 다르게 정할 수 있다.",
                "③ 보직교원에 대한 책임시간의 일부면제와 교원에 대한 초과강의시간의 제한에 대하여는 총장이 따로 정한다.",
            ],
            "revised": [
                "<strong>제47조(교수시간)</strong>",
                f"① 우리 대학교 교원(강사 제외)의 교수시간은 매 학년도 30주를 기준으로 주당 9시간을 원칙으로 하며, {_redline('초등교육전공과정, 교육대학원 및 교육전문대학원에서 담당한 강의시간을 통합하여 산정한다.')}",
                f"③ {_redline('보직교원, 교육전문대학원장, 교육전문대학원 전공주임교수, 교육전문대학원 소속 전임교원 및 겸무·겸보 교원')}에 대한 책임시간의 일부면제, 수업분담 기준과 교원에 대한 초과강의시간의 제한에 대하여는 총장이 따로 정한다.",
                f"{_redline('④ 교육전문대학원 소속 전임교원의 초등교육전공과정 및 교육대학원 강의시간은 교수시간 및 책임시간에 포함하며, 소속 변경만을 이유로 교수시간 산정에서 불리하게 취급하지 아니한다.')}",
            ],
        },
        {
            "article": "제66조",
            "original": [
                "<strong>제66조(위원회)</strong>",
                "① 우리 대학교에 교무위원회, 대학인사위원회, 대학원위원회, 대학입학전형관리위원회, 학생지도위원회, 장애학생특별지원위원회를 둔다.",
                "③ 위원회의 설치와 운영에 관한 사항은 총장이 따로 정한다.",
            ],
            "revised": [
                "<strong>제66조(위원회)</strong>",
                f"① 우리 대학교에 교무위원회, 대학인사위원회, 대학원위원회, {_redline('교육전문대학원위원회')}, 대학입학전형관리위원회, 학생지도위원회, 장애학생특별지원위원회를 둔다.",
                f"③ 위원회의 설치와 운영에 관한 사항은 총장이 따로 정한다. {_redline('다만, 교육전문대학원위원회는 교육전문대학원의 학사운영, 전공 설치·폐지, 교육과정, 학위수여, 교원 배치 및 그 밖에 교육전문대학원 운영에 관한 중요 사항을 심의한다.')}",
            ],
        },
        {
            "article": "부칙",
            "original": [
                "<strong>&lt;신설&gt;</strong>",
                "현행 학칙에는 교육전문대학원 최초 설치와 최초 전임교원 7명 소속 변경, 학부 수업권 보호, 하위규정 정비에 관한 경과조치가 없다.",
            ],
            "revised": [
                f"<strong>{_redline('부칙')}</strong>",
                f"{_redline('제1조(시행일) 이 학칙은 공포한 날부터 시행한다. 다만, 교육전문대학원의 학위과정, 전공, 학생정원 및 교원 배치에 관한 사항은 교육부 승인 및 관계 법령에 따른 절차가 완료된 날부터 시행한다.')}",
                f"{_redline('제2조(교육전문대학원 설치 준비행위) 총장은 이 학칙 시행 전이라도 교육전문대학원 설치를 위하여 학칙 제정, 전공 편성, 교원 배치계획, 의견수렴, 교육과정 편성, 하위규정 정비 등 필요한 준비행위를 할 수 있다.')}",
                f"{_redline('제3조(최초 전임교원 소속 변경에 관한 경과조치) 최초 설치에 따라 교육전문대학원 소속으로 변경되는 전임교원은 관련 분야 전임교원 7명을 기준으로 하되, 전공 적합성, 연구실적, 전공 운영 필요성, 학부 수업 운영 영향, 해당 교원의 의견을 종합하여 정한다.')}",
                f"{_redline('제4조(학부 수업권 보호에 관한 경과조치) 총장은 개원 최초 3년간 매 학년도 학부 필수수업, 심화과정 수업, 교육실습 및 학생지도 운영 현황을 점검하고 수업분담 계획을 교수회에 보고하여야 한다.')}",
                f"{_redline('제5조(다른 규정의 정비) 총장은 시행일부터 6개월 이내에 학사운영규정, 직제 및 사무분장 규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준, 보수·수당 관련 규정을 정비하여야 한다.')}",
            ],
        },
    ]
    rendered = []
    for row in rows:
        rendered.append(
            f"""
            <article class="split-row" id="split-{_escape(row['article'])}">
              <div class="split-article">{_escape(row['article'])}</div>
              <div class="split-pane original-pane">
                <h4>원문</h4>
                <div class="law-text">{_paragraphs(row['original'])}</div>
              </div>
              <div class="split-pane revised-pane">
                <h4>수정문</h4>
                <div class="law-text">{_paragraphs(row['revised'])}</div>
              </div>
            </article>
            """
        )
    return f"""
    <div class="split-toolbar">
      <span>왼쪽: 현행 원문</span>
      <span>오른쪽: 수정문</span>
      <span class="revision">빨간색: 신설·수정 내용</span>
    </div>
    <div class="split-document" aria-label="신구조문 2단 스크롤 대비표">
      {''.join(rendered)}
    </div>
    """


def _details_documents(paths: list[Path]) -> str:
    details = []
    for path in paths:
        content = _read_markdown(path)
        if not content:
            continue
        title = path.stem.replace("_", " ")
        details.append(
            f"""
            <details class="doc-detail">
              <summary>{_escape(title)}</summary>
              <div class="prose">{_markdown_to_html(content)}</div>
            </details>
            """
        )
    if not details:
        return '<p class="muted">표시할 원문 문서가 없습니다.</p>'
    return "\n".join(details)


def _plot(fig: go.Figure, include_plotlyjs: str | bool = False) -> str:
    return pio.to_html(
        fig,
        include_plotlyjs=include_plotlyjs,
        full_html=False,
        config={
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {"format": "png", "scale": 2},
        },
    )


def _status_table() -> pd.DataFrame:
    df = GRADUATE_SCHOOL_STATUS.copy()
    df["설치여부"] = df["교육전문대학원_설치"].map({True: "설치", False: "미설치"})
    df["설치연도"] = df["설치연도"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    df["박사전공수"] = df["박사전공수"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    return df[["대학교", "소재지", "설치여부", "설치연도", "설치방식", "박사전공수"]]


def _major_summary() -> pd.DataFrame:
    majors = get_major_comparison()
    if majors.empty:
        return pd.DataFrame()
    return (
        majors.groupby(["대학교", "분야"])
        .size()
        .reset_index(name="전공수")
        .sort_values(["대학교", "분야"])
    )


def _major_bar_chart() -> go.Figure:
    majors = get_major_comparison()
    counts = majors.groupby("대학교").size().reset_index(name="박사전공수")
    counts = counts.sort_values("박사전공수", ascending=False)
    fig = px.bar(
        counts,
        x="대학교",
        y="박사전공수",
        text="박사전공수",
        color="박사전공수",
        color_continuous_scale=["#b7d9f6", "#185c97"],
        title="교육전문대학원 박사전공 수 비교",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=430, showlegend=False, coloraxis_showscale=False)
    return fig


def _student_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
    if summary.empty:
        return None
    total = summary.groupby(["연도", "대학교"], as_index=False)["재학생_전체"].sum()
    fig = px.line(
        total,
        x="연도",
        y="재학생_전체",
        color="대학교",
        markers=True,
        title="교대별 총 대학원 재학생 추이",
    )
    fig.update_layout(height=480, yaxis_title="재학생 수")
    return fig


def _jnue_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
    if summary.empty:
        return None
    jnue = summary[summary["대학교"] == "전주교대"].sort_values("연도")
    if jnue.empty:
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=jnue["연도"],
            y=jnue["재학생_전체"],
            mode="lines+markers+text",
            text=jnue["재학생_전체"].astype(int),
            textposition="top center",
            name="재학생",
            line={"color": "#d64545", "width": 3},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=jnue["연도"],
            y=jnue["지원자_전체"],
            mode="lines+markers",
            name="지원자",
            line={"color": "#d58921", "dash": "dot"},
        )
    )
    fig.update_layout(title="전주교대 교육대학원 재학생·지원자 추이", height=430)
    return fig


def _competition_chart(comp: pd.DataFrame) -> go.Figure | None:
    if comp.empty:
        return None
    latest_year = int(comp["연도"].max())
    latest = comp[comp["연도"] == latest_year].copy().sort_values("경쟁률", ascending=False)
    fig = px.bar(
        latest,
        x="대학교",
        y="경쟁률",
        color="대학원유형",
        text="경쟁률",
        title=f"{latest_year}년 대학원 경쟁률 비교",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=430)
    return fig


def _decline_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    total = summary.groupby(["연도", "대학교"], as_index=False)["재학생_전체"].sum()
    pivot = total.pivot_table(index="연도", columns="대학교", values="재학생_전체", aggfunc="sum")
    if len(pivot.index) < 2:
        return pd.DataFrame()
    first_year = int(pivot.index.min())
    last_year = int(pivot.index.max())
    rows = []
    for university in pivot.columns:
        first = float(pivot.loc[first_year, university])
        last = float(pivot.loc[last_year, university])
        if first <= 0:
            continue
        rows.append(
            {
                "대학교": university,
                f"{first_year} 재학생": int(first),
                f"{last_year} 재학생": int(last),
                "변화율": f"{(last - first) / first * 100:.1f}%",
            }
        )
    return pd.DataFrame(rows).sort_values("변화율")


def _copy_report_asset() -> str:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if REPORT_PATH.exists():
        _validate_hwpx_file(REPORT_PATH)
        shutil.copy2(REPORT_PATH, REPORT_ASSET)
        digest = hashlib.sha256(REPORT_ASSET.read_bytes()).hexdigest()[:12]
        return f"assets/{REPORT_ASSET.name}?v={digest}"
    return ""


def _validate_hwpx_file(path: Path) -> None:
    """Fail fast if the downloadable HWPX is only a ZIP but not a usable HWPX."""
    required = {
        "mimetype",
        "version.xml",
        "Contents/content.hpf",
        "Contents/header.xml",
        "Contents/section0.xml",
        "Preview/PrvText.txt",
    }
    section_ns = "{http://www.hancom.co.kr/hwpml/2011/section}sec"
    text_ns = "{http://www.hancom.co.kr/hwpml/2011/paragraph}t"
    line_break_ns = "{http://www.hancom.co.kr/hwpml/2011/paragraph}lineBreak"
    para_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}

    def display_width(text: str) -> int:
        return sum(2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1 for ch in text)

    def paragraph_lines(paragraph: ET.Element) -> list[str]:
        lines = [""]
        for text_node in paragraph.iter(text_ns):
            if text_node.text:
                lines[-1] += text_node.text
            for child in list(text_node):
                if child.tag == line_break_ns:
                    lines.append(child.tail or "")
        return lines

    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            missing = required - names
            if missing:
                raise ValueError(f"missing HWPX entries: {', '.join(sorted(missing))}")

            first = zf.infolist()[0]
            if first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED:
                raise ValueError("mimetype must be the first uncompressed ZIP entry")
            if zf.read("mimetype").decode("utf-8") != "application/hwp+zip":
                raise ValueError("invalid HWPX mimetype")

            section = ET.fromstring(zf.read("Contents/section0.xml"))
            if section.tag != section_ns:
                raise ValueError(f"unexpected section namespace: {section.tag}")

            texts = []
            visual_lines = []
            for para in section.findall(".//hp:p", para_ns):
                lines = paragraph_lines(para)
                visual_lines.extend(lines)
                texts.append(" ".join(line for line in lines if line))
            body = "\n".join(texts)
            if len(texts) < 100 or "전주교육대학교 교육전문대학원 설치 정책연구" not in body:
                raise ValueError("HWPX body text is incomplete")
            if "부록 6. 원자료 추적표" not in body:
                raise ValueError("HWPX appendix text is incomplete")
            if any(display_width(line) > 110 for line in visual_lines):
                raise ValueError("HWPX visual line wrapping is incomplete")
    except (zipfile.BadZipFile, ET.ParseError, UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError(f"Invalid HWPX report asset: {path}") from exc


def build_site() -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = get_overview_metrics()
    status_table = _status_table()
    timeline = get_timeline_data()
    summary = get_student_summary()
    comp = get_competition_rates()
    decline = _decline_table(summary)
    major_summary = _major_summary()
    report_href = _copy_report_asset()
    chapter_paths = sorted(CHAPTER_DIR.glob("*.md"))
    debate_paths = sorted(DEBATE_DIR.glob("*.md"))

    figs: list[str] = [
        _plot(create_status_table_chart(GRADUATE_SCHOOL_STATUS), include_plotlyjs="cdn"),
        _plot(create_timeline_chart(timeline)),
        _plot(_major_bar_chart()),
        _plot(create_major_heatmap(get_major_heatmap_data())),
    ]
    student_trend = _student_trend_chart(summary)
    if student_trend:
        figs.append(_plot(student_trend))
    jnue_trend = _jnue_trend_chart(summary)
    if jnue_trend:
        figs.append(_plot(jnue_trend))
    competition = _competition_chart(comp)
    if competition:
        figs.append(_plot(competition))

    report_button = (
        f'<a class="button" href="{_escape(report_href)}" download="{_escape(REPORT_ASSET.name)}">최종보고서 HWPX 다운로드</a>'
        if report_href
        else '<span class="muted">HWPX 보고서 파일이 아직 생성되지 않았습니다.</span>'
    )
    roadmap_table = _table(
        pd.DataFrame(
            [
                {"단계": "1단계", "기간": "2026~2027", "핵심 산출물": "A1·A2 조사, 교원 7명 검증표, 학칙 개정안, 재정 추계표"},
                {"단계": "2단계", "기간": "2027~2030", "핵심 산출물": "1기 20~24명 운영, 충원율·학부 수업권 모니터링, 전공 안정화"},
                {"단계": "3단계", "기간": "2030~", "핵심 산출물": "충원율 80% 이상 확인 후 전공·정원 확대 검토"},
            ]
        )
    )
    risk_table = _table(
        pd.DataFrame(
            [
                {"리스크": "전임교원 7명 확보", "대응": "A1 의향조사 + 전공 적합성·연구실적 검증표 + 메리트 패키지"},
                {"리스크": "전북 수요 미검증", "대응": "A2 표본 500명 이상 조사 + 5개 조건 유효수요 산식"},
                {"리스크": "재정 추계 미완성", "대응": "20/24명 × 7개 충원율 14개 조합 손익분기 산식"},
                {"리스크": "학부 수업권 우려", "대응": "학부 6시간 + 대학원 3시간, 제4조의2·제47조·부칙 경과조치"},
            ]
        )
    )
    appendix_table = _table(
        pd.DataFrame(
            [
                {"부록": "부록 1", "내용": "A1 교원 소속 이동 의향조사 설문지", "상태": "문항 포함"},
                {"부록": "부록 2", "내용": "A2 전북 현직교사 수요조사 설문지", "상태": "유효수요 산식 포함"},
                {"부록": "부록 3", "내용": "교원 7명 후보 전공 적합성·연구실적 검증표", "상태": "검증표 포함"},
                {"부록": "부록 4", "내용": "재정 추계 산식표", "상태": "14개 시나리오 포함"},
                {"부록": "부록 5", "내용": "학칙·규정 개정 패키지", "상태": "5-A~5-I 포함"},
                {"부록": "부록 6", "내용": "원자료 추적표", "상태": "감사 ID 연결"},
            ]
        )
    )
    audit_table = _table(
        pd.DataFrame(
            [
                {"검증": "Fact ledger", "결과": "57건 중 PASS 55건, 확인 필요 2건", "의미": "잔여 2건은 공식 전공수와 충원자료 행수의 정의 차이"},
                {"검증": "본문 정합성", "결과": "새 CHECK 0건", "의미": "학교별 충원율·집계 비율 추가 오류 없음"},
                {"검증": "학칙 원문 추출", "결과": "8건 중 8건 PASS", "의미": "타 교대 학칙 원문 변환·추출 안정"},
                {"검증": "최신성", "결과": "2026 기준·대구교대 연도 기준 반영", "의미": "최종 신청서는 2026학년도 기준으로 전환 필요"},
            ]
        )
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>전주교대 교육전문대학원 정책연구 대시보드</title>
  <meta name="description" content="전주교육대학교 교육전문대학원 설치 정책연구 분석 결과 정적 대시보드">
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5d6a78;
      --line: #d9e1e8;
      --panel: #f7fafc;
      --blue: #185c97;
      --red: #b63f3f;
      --gold: #b87512;
      --green: #26735b;
      --bg: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.6;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #f6fbff 0%, #ffffff 100%);
    }}
    .wrap {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .hero {{
      padding: 42px 0 28px;
    }}
    .eyebrow {{
      margin: 0 0 10px;
      color: var(--blue);
      font-size: 14px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(30px, 5vw, 52px);
      line-height: 1.12;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 18px;
      font-size: 26px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 12px; }}
    .lead {{
      max-width: 860px;
      margin-top: 18px;
      color: #33475b;
      font-size: 18px;
    }}
    .tab-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 24px;
    }}
    .tab-button, .button {{
      display: inline-flex;
      min-height: 38px;
      align-items: center;
      justify-content: center;
      padding: 8px 13px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      background: #fff;
      text-decoration: none;
      font-weight: 650;
      white-space: nowrap;
    }}
    .tab-button {{
      cursor: pointer;
    }}
    .tab-button[aria-selected="true"] {{
      border-color: var(--blue);
      color: #fff;
      background: var(--blue);
    }}
    .button {{
      border-color: var(--blue);
      color: #fff;
      background: var(--blue);
    }}
    .tab-panel {{
      display: none;
    }}
    .tab-panel.active {{
      display: block;
    }}
    main section {{
      padding: 34px 0;
      border-bottom: 1px solid var(--line);
    }}
    .tab-panel > section:last-child {{
      border-bottom: 0;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 22px;
    }}
    .metric-card {{
      min-height: 122px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
    }}
    .metric-card strong {{
      display: block;
      margin-top: 8px;
      font-size: 30px;
      line-height: 1.1;
    }}
    .metric-card span {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .plot {{
      min-height: 420px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fff;
      overflow: hidden;
    }}
    .table-wrap {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    table {{
      width: 100%;
      min-width: 680px;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #eef5fb;
      color: #18344f;
      font-weight: 750;
    }}
    .note {{
      padding: 16px;
      border-left: 4px solid var(--gold);
      background: #fff8ec;
      color: #47351d;
    }}
    .prose {{
      max-width: 100%;
    }}
    .prose h3 {{
      margin-top: 28px;
      padding-top: 4px;
      color: #18344f;
    }}
    .prose h4, .prose h5 {{
      margin: 22px 0 10px;
      color: #27445e;
      font-size: 16px;
    }}
    .prose ul {{
      margin: 0 0 16px 20px;
      padding: 0;
    }}
    .prose li {{
      margin: 4px 0;
    }}
    .prose blockquote {{
      margin: 16px 0;
      padding: 12px 14px;
      border-left: 4px solid var(--blue);
      background: #f2f7fb;
      color: #24384a;
    }}
    .prose code {{
      padding: 1px 4px;
      border-radius: 4px;
      background: #eef3f7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }}
    .doc-detail {{
      margin: 12px 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .doc-detail summary {{
      cursor: pointer;
      padding: 13px 16px;
      font-weight: 750;
      color: #18344f;
      background: #f4f8fb;
    }}
    .doc-detail .prose {{
      padding: 16px;
    }}
    .split-toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 16px 0 10px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .split-toolbar span {{
      display: inline-flex;
      min-height: 30px;
      align-items: center;
      padding: 5px 9px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }}
    .split-document {{
      max-height: 78vh;
      overflow-y: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .split-row {{
      display: grid;
      grid-template-columns: 84px minmax(0, 1fr) minmax(0, 1fr);
      border-bottom: 1px solid var(--line);
    }}
    .split-row:last-child {{
      border-bottom: 0;
    }}
    .split-article {{
      position: sticky;
      left: 0;
      z-index: 1;
      padding: 14px 10px;
      border-right: 1px solid var(--line);
      background: #eef5fb;
      color: #18344f;
      font-weight: 800;
      text-align: center;
    }}
    .split-pane {{
      min-height: 180px;
      padding: 14px;
    }}
    .original-pane {{
      border-right: 1px solid var(--line);
      background: #fbfcfd;
    }}
    .revised-pane {{
      background: #fff;
    }}
    .split-pane h4 {{
      margin: 0 0 10px;
      color: #18344f;
      font-size: 14px;
    }}
    .law-text p {{
      margin: 0 0 10px;
      font-size: 14px;
      line-height: 1.68;
    }}
    .revision {{
      color: var(--red);
      font-weight: 750;
    }}
    .full-width {{
      grid-column: 1 / -1;
    }}
    .muted {{ color: var(--muted); }}
    footer {{
      padding: 28px 0 42px;
      color: var(--muted);
      font-size: 14px;
    }}
    @media (max-width: 860px) {{
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      .hero {{ padding-top: 30px; }}
      h1 {{ font-size: 34px; }}
      .split-document {{
        max-height: 80vh;
        overflow-x: auto;
      }}
      .split-row {{
        min-width: 860px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap hero">
      <p class="eyebrow">GitHub Pages 정적 대시보드</p>
      <h1>전주교대 교육전문대학원 설치 정책연구</h1>
      <p class="lead">Streamlit 서버 없이 열람 가능한 분석 결과 대시보드입니다. 전국 교대 설치 현황, 전공 비교, 학생 통계, 경쟁률, 설치 당위성, 학칙 개정 핵심 논리를 한 화면에서 확인할 수 있습니다.</p>
      <div class="tab-nav" role="tablist" aria-label="정책연구 대시보드 탭">
        <button class="tab-button" type="button" role="tab" aria-selected="true" data-tab-target="overview">개요</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="demand">전공·수요</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="model">모델·로드맵</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="law">학칙</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="appendix">부록</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="evidence">검증</button>
        <button class="tab-button" type="button" role="tab" aria-selected="false" data-tab-target="outputs">산출물</button>
      </div>
      <div class="metrics">
        {_metric("전체 교육대학교", f"{metrics['총_교대수']}개교")}
        {_metric("교육전문대학원 설치", f"{metrics['설치_완료']}개교", "2026년 현재 분석 기준")}
        {_metric("미설치 대학", f"{metrics['미설치']}개교", ", ".join(metrics["미설치_대학"]))}
        {_metric("설치 비율", metrics["설치_비율"], "전국 10개 교대 기준")}
      </div>
    </div>
  </header>
  <main class="wrap">
    <div class="tab-panel active" id="tab-overview" role="tabpanel">
      <section>
        <h2>개요와 설치 현황</h2>
        <p class="note">전국 10개 교육대학교 중 7개교가 교육전문대학원을 설치했으며, 전주교대는 부산교대·춘천교대와 함께 미설치 그룹에 남아 있습니다. 이 탭은 전체 판단에 필요한 설치 현황, 시기, 재학생 변화율을 한 번에 보여줍니다.</p>
        <div class="grid">
          <div class="plot">{figs[0]}</div>
          <div class="plot">{figs[1]}</div>
        </div>
        <h3>설치 현황 표</h3>
        {_table(status_table)}
      </section>
      <section>
        <h2>재학생 변화와 경쟁률</h2>
        <div class="grid">
          <div class="plot">{figs[4] if len(figs) > 4 else '<p class="muted">학생 통계 데이터가 없습니다.</p>'}</div>
          <div class="plot">{figs[5] if len(figs) > 5 else '<p class="muted">전주교대 추이 데이터가 없습니다.</p>'}</div>
        </div>
        <div class="plot">{figs[6] if len(figs) > 6 else '<p class="muted">경쟁률 데이터가 없습니다.</p>'}</div>
        <h3>재학생 변화율 요약</h3>
        {_table(decline)}
      </section>
    </div>

    <div class="tab-panel" id="tab-demand" role="tabpanel" hidden>
      <section>
        <h2>전공 구성과 수요</h2>
        <p class="note">전공 탭은 7개 설치대학의 박사전공 분포, 신설 5개교 충원 실적, 전주교대 1기 전공 설계 방향을 함께 검토하도록 구성했습니다.</p>
        <div class="grid">
          <div class="plot">{figs[2]}</div>
          <div class="panel">
            <h3>전공 설계 시사점</h3>
            <p>신청 단계에서는 7개 전공을 포괄하되, 1기 실제 운영은 지도교수 확보와 A2 유효수요가 확인된 4~5개 전공부터 단계 개설하는 구조가 가장 방어적입니다.</p>
            {_table(major_summary)}
          </div>
        </div>
        <div class="plot">{figs[3]}</div>
      </section>
      <section>
        <h2>A1·A2 조사 설계</h2>
        <div class="grid">
          <article class="panel">
            <h3>A1 교원 조사</h3>
            <p>전임교원 59명을 대상으로 소속 이동 의향, 전공 적합성, 연구실적, 학부 겸보 가능성, 메리트 패키지 수용성을 확인합니다. 핵심 판정은 이동 의향만이 아니라 7명 모두 연구실적과 전공 적합성을 충족하는지입니다.</p>
          </article>
          <article class="panel">
            <h3>A2 현직교사 조사</h3>
            <p>전북 현직교사 수요는 단순 관심률이 아니라 관심, 3년 내 지원, 전공 일치, 등록금 수용, 야간·주말 가능의 5개 조건 동시 충족 응답자 수로 판정합니다.</p>
          </article>
        </div>
      </section>
    </div>

    <div class="tab-panel" id="tab-model" role="tabpanel" hidden>
      <section>
        <h2>설치 모델과 로드맵</h2>
        <div class="grid">
          <article class="panel">
            <h3>정책 흐름</h3>
            <p>2025년 대구·광주·공주·청주·진주교대가 병설형 교육전문대학원을 설치하면서, 교육대학교의 박사과정 운영은 확산 단계로 이동했습니다.</p>
          </article>
          <article class="panel">
            <h3>운영 원칙</h3>
            <p>1기 정원은 20~24명, 실제 개설 전공은 4~5개부터 시작하고, 충원율과 지도교수 확보를 확인한 뒤 단계적으로 확대하는 보수적 모델이 적절합니다.</p>
          </article>
          <article class="panel">
            <h3>교원 확보</h3>
            <p>핵심 리스크는 전임교원 7명 소속 이동입니다. 학부 6시간 + 대학원 3시간의 겸보 모델, 책임시수 통합 산정, 교연비·업적평가 실적 인정이 함께 설계되어야 합니다.</p>
          </article>
          <article class="panel">
            <h3>조건부 결론</h3>
            <p>현 보고서는 설치 가능성을 지지하지만, 신청서 전환 전 A1·A2, 교원 검증, 재정 추계, 규정 개정안 확정이 완료되어야 합니다.</p>
          </article>
        </div>
        <h3>추진 로드맵</h3>
        {roadmap_table}
        <h3>핵심 리스크와 대응</h3>
        {risk_table}
      </section>
    </div>

    <div class="tab-panel" id="tab-law" role="tabpanel" hidden>
      <section>
        <h2>학칙 개정 핵심</h2>
        <p class="note">전주교대 학칙 개정은 단순히 제3조에 교육전문대학원을 추가하는 방식으로는 부족합니다. 전임교원 7명의 신분보장, 학부 수업권 보호, 책임시수 인정, 교연비·업적평가 불이익 금지를 함께 담는 신분보장형 패키지 개정이 필요합니다.</p>
        <div class="grid">
          <article class="panel">
            <h3>본칙 핵심 조항</h3>
            <p>제4조의2를 신설해 전임교원의 소속 변경, 겸무·겸보, 학부 겸무 범위에서의 소속 간주, 학부·교육대학원·교육전문대학원 강의시간 통합 산정, 불이익 금지 원칙을 둡니다.</p>
          </article>
          <article class="panel">
            <h3>하위규정 연동</h3>
            <p>교연비 금액이나 배점을 학칙에 직접 쓰지 않고, 학칙은 실적 인정과 불이익 금지 원칙을 둡니다. 세부 기준은 학사운영규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준으로 위임합니다.</p>
          </article>
        </div>
      </section>
      <section>
        <h2>전주교육대학교 학칙 개정(안)</h2>
        <p class="note">교육전문대학원 설치, 전임교원 7명 소속 변경, 학부 수업권 보호, 책임시수 통합 인정, 교연비·업적평가 불이익 금지를 하나의 패키지로 묶은 조문안입니다.</p>
        {_document_panel(POLICY_AMENDMENT_PATH, "전주교육대학교 학칙 개정안")}
      </section>
      <section>
        <h2>신·구조문 대비표</h2>
        <p class="note">왼쪽에는 현행 원문, 오른쪽에는 수정문을 배치했고, 수정문에서 신설·수정된 내용은 빨간색으로 표시했습니다.</p>
        {_split_comparison_view()}
        <h3>표 형식 요약</h3>
        {_document_panel(COMPARISON_TABLE_PATH, "전주교육대학교 학칙 개정 신구조문 대비표")}
      </section>
    </div>

    <div class="tab-panel" id="tab-appendix" role="tabpanel" hidden>
      <section>
        <h2>부록 패키지</h2>
        <p class="note">최종보고서 부록은 단순 목록이 아니라 설문지, 검증표, 재정 산식, 규정 개정 패키지, 원자료 추적표까지 실제 신청서 전환에 필요한 양식으로 확장했습니다.</p>
        {appendix_table}
      </section>
      <section>
        <h2>보고서 장별 본문</h2>
        <p class="note">부록 전문은 제X장 「참고문헌·부록」 접이식 본문에 포함되어 있습니다.</p>
        {_details_documents(chapter_paths)}
      </section>
    </div>

    <div class="tab-panel" id="tab-evidence" role="tabpanel" hidden>
      <section>
        <h2>검증과 쟁점 검토</h2>
        <p class="note">자동 감사 결과와 쟁점별 토론 문서를 묶었습니다. 수치 오류, 기준 혼재, 규정 리스크를 빠르게 점검할 수 있습니다.</p>
        {audit_table}
      </section>
      <section>
        <h2>쟁점별 검토 메모</h2>
        {_details_documents(debate_paths)}
      </section>
    </div>

    <div class="tab-panel" id="tab-outputs" role="tabpanel" hidden>
      <section>
        <h2>산출물</h2>
        <p>정적 대시보드는 `scripts/generate_pages_site.py`로 생성됩니다. GitHub Actions가 main 브랜치 푸시 시 자동으로 이 페이지를 빌드해 GitHub Pages에 배포합니다.</p>
        <p>{report_button}</p>
        <p class="muted">생성 시각: {_escape(generated_at)}</p>
      </section>
    </div>
  </main>
  <script>
    (() => {{
      const buttons = Array.from(document.querySelectorAll("[data-tab-target]"));
      const panels = Array.from(document.querySelectorAll(".tab-panel"));
      const activate = (name) => {{
        buttons.forEach((button) => {{
          const selected = button.dataset.tabTarget === name;
          button.setAttribute("aria-selected", selected ? "true" : "false");
        }});
        panels.forEach((panel) => {{
          const selected = panel.id === `tab-${{name}}`;
          panel.classList.toggle("active", selected);
          panel.hidden = !selected;
        }});
        if (location.hash !== `#${{name}}`) {{
          history.replaceState(null, "", `#${{name}}`);
        }}
        window.setTimeout(() => {{
          window.dispatchEvent(new Event("resize"));
          if (window.Plotly) {{
            document.querySelectorAll(`#tab-${{name}} .js-plotly-plot`).forEach((plot) => {{
              window.Plotly.Plots.resize(plot);
            }});
          }}
        }}, 60);
      }};
      buttons.forEach((button) => {{
        button.addEventListener("click", () => activate(button.dataset.tabTarget));
      }});
      const initial = location.hash ? location.hash.slice(1) : "overview";
      if (buttons.some((button) => button.dataset.tabTarget === initial)) {{
        activate(initial);
      }}
    }})();
  </script>
  <footer>
    <div class="wrap">
      <p>전주교육대학교 교육전문대학원 설치 정책연구 정적 대시보드. 데이터와 산식은 저장소의 `src/`, `data/`, `reports/chapters/` 원자료를 기준으로 생성됩니다.</p>
    </div>
  </footer>
</body>
</html>
"""


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    html_text = build_site()
    (DOCS_DIR / "index.html").write_text(html_text, encoding="utf-8")
    print(f"Generated {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
