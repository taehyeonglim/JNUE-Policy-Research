"""마크다운 장 파일들을 합쳐서 한컴에서 열리는 HWPX 파일로 변환한다.

HWPX는 ZIP 컨테이너이지만 내부 XML이 한컴 HWPML 구조와 맞지 않으면
압축 검사는 통과해도 한글에서 손상된 파일로 판정된다. 이 생성기는 저장소의
정상 HWPX 문서를 템플릿으로 사용해 패키지 구조, 헤더, 설정 파일을 보존하고
본문 섹션만 교체한다.
"""

import zipfile
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

# ── 경로 설정 ──
BASE = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = BASE / "reports" / "chapters"
OUTPUT = BASE / "reports" / "전주교대_교육전문대학원_설치_정책연구_초안.hwpx"
TEMPLATE = BASE / "data" / "정책연구논문 예시" / "정책 연구 논문 체제.hwpx"

# 장 순서 (라운드 4·5에서 05·09장 신설 반영)
CHAPTER_FILES = [
    "01_서론.md",
    "02_정책환경.md",
    "03_전국교대현황.md",
    "04_전주교대현황.md",
    "05_수요조사설계_예비수요검토.md",
    "06_설치당위성.md",
    "07_모델설계.md",
    "08_운영전략_기대효과.md",
    "09_결론.md",
    "10_참고문헌_부록.md",
]

# ── HWPX 네임스페이스 ──
# 한컴에서 만든 HWPX 템플릿과 같은 2011 계열 네임스페이스를 사용한다.
NS_SEC = "http://www.hancom.co.kr/hwpml/2011/section"
NS_PARA = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS_HEAD = "http://www.hancom.co.kr/hwpml/2011/head"
NS_CORE = "http://www.hancom.co.kr/hwpml/2011/core"
HWPX_NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": NS_PARA,
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": NS_SEC,
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}


STYLE_MAP = {
    0: {"para": "23", "char": "0", "height": 1000, "baseline": 850, "spacing": 800},
    1: {"para": "22", "char": "10", "height": 1500, "baseline": 1275, "spacing": 1200},
    2: {"para": "23", "char": "11", "height": 1300, "baseline": 1105, "spacing": 1040},
    3: {"para": "23", "char": "7", "height": 1100, "baseline": 935, "spacing": 880},
    4: {"para": "23", "char": "7", "height": 1100, "baseline": 935, "spacing": 880},
}
BODY_WRAP_WIDTH = 92
HEADING_WRAP_WIDTH = 64
TABLE_WIDTH = 42520
TABLE_MARGIN = 260
TABLE_MIN_COLUMN_WIDTH = 4200
TABLE_UNIT_PER_DISPLAY_WIDTH = TABLE_WIDTH / BODY_WRAP_WIDTH
TABLE_ROW_LINE_STEP = 1600
TABLE_BORDER_ID = "3"
TABLE_HEADER_BORDER_ID = "4"


def parse_markdown(filepath):
    """마크다운 파일을 HWPX 문단/표 블록 리스트로 변환한다."""
    blocks = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_para = []
    i = 0

    def flush_para() -> None:
        nonlocal current_para
        if current_para:
            blocks.append({"kind": "paragraph", "level": 0, "text": " ".join(current_para)})
            current_para = []

    while i < len(lines):
        stripped = lines[i].rstrip()

        # 빈 줄 → 현재 단락 종료
        if not stripped:
            flush_para()
            i += 1
            continue

        # 헤딩
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            flush_para()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append({"kind": "paragraph", "level": level, "text": text})
            i += 1
            continue

        # 구분선
        if stripped.startswith("---") and len(stripped.replace("-", "")) == 0:
            flush_para()
            i += 1
            continue

        # 표 행 (| ... |)
        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_para()
            table_lines = []
            while i < len(lines):
                candidate = lines[i].rstrip()
                if not (candidate.startswith("|") and "|" in candidate[1:]):
                    break
                table_lines.append(candidate)
                i += 1
            rows = _parse_table_lines(table_lines)
            if rows:
                blocks.append({"kind": "table", "rows": rows})
            continue

        # 인용 (>)
        if stripped.startswith(">"):
            text = stripped.lstrip("> ").strip()
            if text:
                current_para.append(text)
            i += 1
            continue

        # 볼드/이탤릭 마크다운 제거
        clean = _clean_inline(stripped)

        # 리스트 항목
        list_match = re.match(r"^[\-\*]\s+(.+)$", clean)
        if list_match:
            flush_para()
            blocks.append({"kind": "paragraph", "level": 0, "text": "• " + list_match.group(1)})
            i += 1
            continue

        numbered_match = re.match(r"^\d+[\.\)]\s+(.+)$", clean)
        if numbered_match:
            flush_para()
            blocks.append({"kind": "paragraph", "level": 0, "text": clean})
            i += 1
            continue

        current_para.append(clean)
        i += 1

    flush_para()

    return blocks


def _parse_table_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    max_cols = 0
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or _is_table_delimiter(cells):
            continue
        cleaned = [_clean_inline(cell) for cell in cells]
        max_cols = max(max_cols, len(cleaned))
        rows.append(cleaned)

    if not rows:
        return []
    return [row + [""] * (max_cols - len(row)) for row in rows]


def _is_table_delimiter(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells)


def _clean_inline(text: str) -> str:
    """HWPX 본문 텍스트에 남기지 않을 Markdown 표식을 제거한다."""
    text = text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1 for ch in text)


def _take_display_width(text: str, limit: int) -> tuple[str, str]:
    width = 0
    for idx, ch in enumerate(text):
        next_width = width + (2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1)
        if next_width > limit:
            return text[:idx], text[idx:]
        width = next_width
    return text, ""


def _wrap_text(text: str, limit: int) -> list[str]:
    """한컴이 자동 줄바꿈하지 않는 환경을 대비해 실제 줄 단위로 나눈다."""
    text = _clean_inline(text)
    if _display_width(text) <= limit:
        return [text] if text else []

    lines: list[str] = []
    current: list[str] = []
    current_text = ""
    for token in text.split(" "):
        candidate = token if not current_text else f"{current_text} {token}"
        if _display_width(candidate) <= limit:
            current.append(token)
            current_text = candidate
            continue

        if current_text:
            lines.append(current_text)
            current = []
            current_text = ""

        while _display_width(token) > limit:
            head, token = _take_display_width(token, limit)
            if head:
                lines.append(head)
        if token:
            current = [token]
            current_text = token

    if current_text:
        lines.append(current_text)
    return lines


def _xml_with_decl(element: ET.Element) -> str:
    body = ET.tostring(element, encoding="unicode", short_empty_elements=True)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + body


def _add_text_with_line_breaks(parent: ET.Element, lines: list[str]) -> None:
    t = ET.SubElement(parent, f"{{{NS_PARA}}}t")
    t.text = lines[0] if lines else ""
    for line in lines[1:]:
        ET.SubElement(t, f"{{{NS_PARA}}}lineBreak").tail = line


def _add_paragraph(sec: ET.Element, level: int, lines: list[str], index: int) -> int:
    style = STYLE_MAP.get(level, STYLE_MAP[0])
    height = int(style["height"])
    baseline = int(style["baseline"])
    spacing = int(style["spacing"])
    line_step = max(spacing + 800, 1800)

    p = ET.SubElement(
        sec,
        f"{{{NS_PARA}}}p",
        {
            "id": "0" if level in (0, 1, 2) else "2147483648",
            "paraPrIDRef": str(style["para"]),
            "styleIDRef": "0",
            "pageBreak": "0",
            "columnBreak": "0",
            "merged": "0",
        },
    )
    run = ET.SubElement(p, f"{{{NS_PARA}}}run", {"charPrIDRef": str(style["char"])})
    _add_text_with_line_breaks(run, lines)
    line_segments = ET.SubElement(p, f"{{{NS_PARA}}}linesegarray")

    textpos = 0
    for offset, line in enumerate(lines or [""]):
        ET.SubElement(
            line_segments,
            f"{{{NS_PARA}}}lineseg",
            {
                "textpos": str(textpos),
                "vertpos": str((index + offset) * line_step),
                "vertsize": str(height),
                "textheight": str(height),
                "baseline": str(baseline),
                "spacing": str(spacing),
                "horzpos": "0",
                "horzsize": "42520",
                "flags": "393216",
            },
        )
        textpos += len(line) + 1

    return max(1, len(lines))


def _column_widths(rows: list[list[str]], col_count: int) -> list[int]:
    weights = []
    for col in range(col_count):
        max_width = max(_display_width(row[col]) for row in rows)
        weights.append(max(8, min(max_width, 42)))

    min_width = min(TABLE_MIN_COLUMN_WIDTH, TABLE_WIDTH // col_count)
    total_weight = sum(weights) or col_count
    widths = [max(min_width, int(TABLE_WIDTH * weight / total_weight)) for weight in weights]

    while sum(widths) > TABLE_WIDTH:
        adjustable = max(range(col_count), key=lambda idx: widths[idx] - min_width)
        if widths[adjustable] <= min_width:
            break
        widths[adjustable] -= min(widths[adjustable] - min_width, sum(widths) - TABLE_WIDTH)
    widths[-1] += TABLE_WIDTH - sum(widths)
    return widths


def _cell_wrap_width(cell_width: int) -> int:
    usable = max(1200, cell_width - (TABLE_MARGIN * 2))
    return max(8, int(usable / TABLE_UNIT_PER_DISPLAY_WIDTH))


def _line_segment(
    parent: ET.Element,
    *,
    textpos: int,
    vertpos: int,
    height: int,
    baseline: int,
    spacing: int,
    horzsize: int,
) -> None:
    ET.SubElement(
        parent,
        f"{{{NS_PARA}}}lineseg",
        {
            "textpos": str(textpos),
            "vertpos": str(vertpos),
            "vertsize": str(height),
            "textheight": str(height),
            "baseline": str(baseline),
            "spacing": str(spacing),
            "horzpos": "0",
            "horzsize": str(horzsize),
            "flags": "393216",
        },
    )


def _add_cell_paragraph(parent: ET.Element, lines: list[str], is_header: bool, cell_width: int) -> None:
    level = 3 if is_header else 0
    style = STYLE_MAP[level]
    height = int(style["height"])
    baseline = int(style["baseline"])
    spacing = int(style["spacing"])

    p = ET.SubElement(
        parent,
        f"{{{NS_PARA}}}p",
        {
            "id": "2147483648",
            "paraPrIDRef": str(style["para"]),
            "styleIDRef": "0",
            "pageBreak": "0",
            "columnBreak": "0",
            "merged": "0",
        },
    )
    run = ET.SubElement(p, f"{{{NS_PARA}}}run", {"charPrIDRef": str(style["char"])})
    _add_text_with_line_breaks(run, lines or [""])
    line_segments = ET.SubElement(p, f"{{{NS_PARA}}}linesegarray")

    textpos = 0
    for offset, line in enumerate(lines or [""]):
        _line_segment(
            line_segments,
            textpos=textpos,
            vertpos=offset * TABLE_ROW_LINE_STEP,
            height=height,
            baseline=baseline,
            spacing=spacing,
            horzsize=max(1000, cell_width - (TABLE_MARGIN * 2)),
        )
        textpos += len(line) + 1


def _add_table(sec: ET.Element, rows: list[list[str]], index: int) -> int:
    col_count = max(len(row) for row in rows)
    rows = [row + [""] * (col_count - len(row)) for row in rows]
    widths = _column_widths(rows, col_count)

    prepared_rows = []
    row_heights = []
    for row_idx, row in enumerate(rows):
        prepared_cells = []
        max_lines = 1
        for col_idx, cell in enumerate(row):
            lines = _wrap_text(cell, _cell_wrap_width(widths[col_idx])) or [""]
            max_lines = max(max_lines, len(lines))
            prepared_cells.append(lines)
        prepared_rows.append(prepared_cells)
        base_padding = 980 if row_idx == 0 else 760
        row_heights.append(max(1800, max_lines * TABLE_ROW_LINE_STEP + base_padding))

    table_height = sum(row_heights) + (TABLE_MARGIN * 2)
    line_step = max(table_height + 600, 2200)

    p = ET.SubElement(
        sec,
        f"{{{NS_PARA}}}p",
        {
            "id": "2147483648",
            "paraPrIDRef": str(STYLE_MAP[0]["para"]),
            "styleIDRef": "0",
            "pageBreak": "0",
            "columnBreak": "0",
            "merged": "0",
        },
    )
    run = ET.SubElement(p, f"{{{NS_PARA}}}run", {"charPrIDRef": str(STYLE_MAP[0]["char"])})
    tbl = ET.SubElement(
        run,
        f"{{{NS_PARA}}}tbl",
        {
            "id": str(1000000000 + index),
            "zOrder": "24",
            "numberingType": "TABLE",
            "textWrap": "TOP_AND_BOTTOM",
            "textFlow": "BOTH_SIDES",
            "lock": "0",
            "dropcapstyle": "None",
            "pageBreak": "CELL",
            "repeatHeader": "1",
            "rowCnt": str(len(rows)),
            "colCnt": str(col_count),
            "cellSpacing": "0",
            "borderFillIDRef": TABLE_BORDER_ID,
            "noAdjust": "0",
        },
    )
    ET.SubElement(
        tbl,
        f"{{{NS_PARA}}}sz",
        {
            "width": str(TABLE_WIDTH),
            "widthRelTo": "ABSOLUTE",
            "height": str(table_height),
            "heightRelTo": "ABSOLUTE",
            "protect": "0",
        },
    )
    ET.SubElement(
        tbl,
        f"{{{NS_PARA}}}pos",
        {
            "treatAsChar": "1",
            "affectLSpacing": "0",
            "flowWithText": "1",
            "allowOverlap": "0",
            "holdAnchorAndSO": "0",
            "vertRelTo": "PARA",
            "horzRelTo": "COLUMN",
            "vertAlign": "TOP",
            "horzAlign": "LEFT",
            "vertOffset": "0",
            "horzOffset": "0",
        },
    )
    for name in ("outMargin", "inMargin"):
        ET.SubElement(
            tbl,
            f"{{{NS_PARA}}}{name}",
            {"left": "0", "right": "0", "top": "0", "bottom": "0"},
        )

    for row_idx, prepared_cells in enumerate(prepared_rows):
        tr = ET.SubElement(tbl, f"{{{NS_PARA}}}tr")
        for col_idx, cell_lines in enumerate(prepared_cells):
            is_header = row_idx == 0
            tc = ET.SubElement(
                tr,
                f"{{{NS_PARA}}}tc",
                {
                    "name": "",
                    "header": "1" if is_header else "0",
                    "hasMargin": "1",
                    "protect": "0",
                    "editable": "0",
                    "dirty": "0",
                    "borderFillIDRef": TABLE_HEADER_BORDER_ID if is_header else TABLE_BORDER_ID,
                },
            )
            sub_list = ET.SubElement(
                tc,
                f"{{{NS_PARA}}}subList",
                {
                    "id": "",
                    "textDirection": "HORIZONTAL",
                    "lineWrap": "BREAK",
                    "vertAlign": "CENTER" if is_header else "TOP",
                    "linkListIDRef": "0",
                    "linkListNextIDRef": "0",
                    "textWidth": "0",
                    "textHeight": "0",
                    "hasTextRef": "0",
                    "hasNumRef": "0",
                },
            )
            _add_cell_paragraph(sub_list, cell_lines, is_header, widths[col_idx])
            ET.SubElement(tc, f"{{{NS_PARA}}}cellAddr", {"colAddr": str(col_idx), "rowAddr": str(row_idx)})
            ET.SubElement(tc, f"{{{NS_PARA}}}cellSpan", {"colSpan": "1", "rowSpan": "1"})
            ET.SubElement(tc, f"{{{NS_PARA}}}cellSz", {"width": str(widths[col_idx]), "height": str(row_heights[row_idx])})
            ET.SubElement(
                tc,
                f"{{{NS_PARA}}}cellMargin",
                {
                    "left": str(TABLE_MARGIN),
                    "right": str(TABLE_MARGIN),
                    "top": str(TABLE_MARGIN),
                    "bottom": str(TABLE_MARGIN),
                },
            )

    ET.SubElement(run, f"{{{NS_PARA}}}t")
    line_segments = ET.SubElement(p, f"{{{NS_PARA}}}linesegarray")
    _line_segment(
        line_segments,
        textpos=0,
        vertpos=index * line_step,
        height=table_height,
        baseline=max(0, table_height - 400),
        spacing=900,
        horzsize=TABLE_WIDTH,
    )
    return max(2, table_height // 1800 + 1)


def _add_blank_paragraph(sec: ET.Element, index: int) -> int:
    return _add_paragraph(sec, 0, [""], index)


def build_section_xml(all_blocks):
    """섹션 XML (Contents/section0.xml) 생성."""
    for prefix, uri in HWPX_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    sec = ET.Element(f"{{{NS_SEC}}}sec")

    _add_paragraph(sec, 1, ["전주교육대학교 교육전문대학원 설치 정책연구"], 0)
    _add_paragraph(sec, 2, ["최종보고서 초안"], 1)
    _add_paragraph(sec, 0, ["생성 기준: reports/chapters 10개 장 원고"], 2)

    paragraph_index = 4
    for block in all_blocks:
        if block["kind"] == "table":
            paragraph_index += _add_table(sec, block["rows"], paragraph_index)
            continue

        level = block["level"]
        text = block["text"]
        if not text.strip():
            paragraph_index += 1
            continue
        wrap_width = HEADING_WRAP_WIDTH if level else BODY_WRAP_WIDTH
        lines = _wrap_text(text, wrap_width)
        if level:
            paragraph_index += _add_blank_paragraph(sec, paragraph_index)
            paragraph_index += _add_blank_paragraph(sec, paragraph_index)
        paragraph_index += _add_paragraph(sec, min(level, 4), lines, paragraph_index)

    return _xml_with_decl(sec)


def _prepare_header_xml(header_bytes: bytes) -> bytes:
    """제목 굵게와 실제 표 테두리/헤더 배경 서식을 템플릿 헤더에 추가한다."""
    for prefix, uri in HWPX_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    root = ET.fromstring(header_bytes)
    ns = {"hh": NS_HEAD}

    for char_id in ("7", "10", "11"):
        char_pr = root.find(f".//hh:charPr[@id='{char_id}']", ns)
        if char_pr is None or char_pr.find(f"{{{NS_HEAD}}}bold") is not None:
            continue
        bold = ET.Element(f"{{{NS_HEAD}}}bold")
        underline_index = next(
            (idx for idx, child in enumerate(list(char_pr)) if child.tag == f"{{{NS_HEAD}}}underline"),
            len(char_pr),
        )
        char_pr.insert(underline_index, bold)

    border_fills = root.find(".//hh:borderFills", ns)
    if border_fills is None:
        return _xml_with_decl(root).encode("utf-8")

    existing = {child.attrib.get("id"): child for child in border_fills.findall(f"{{{NS_HEAD}}}borderFill")}
    for border_id, face_color in ((TABLE_BORDER_ID, None), (TABLE_HEADER_BORDER_ID, "#E9EFF7")):
        if border_id in existing:
            border_fills.remove(existing[border_id])
        border_fills.append(_make_border_fill(border_id, face_color))
    border_fills.set("itemCnt", str(len(border_fills.findall(f"{{{NS_HEAD}}}borderFill"))))

    return _xml_with_decl(root).encode("utf-8")


def _make_border_fill(border_id: str, face_color: str | None) -> ET.Element:
    border_fill = ET.Element(
        f"{{{NS_HEAD}}}borderFill",
        {"id": border_id, "threeD": "0", "shadow": "0", "centerLine": "NONE", "breakCellSeparateLine": "0"},
    )
    ET.SubElement(border_fill, f"{{{NS_HEAD}}}slash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    ET.SubElement(border_fill, f"{{{NS_HEAD}}}backSlash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    for side in ("leftBorder", "rightBorder", "topBorder", "bottomBorder"):
        ET.SubElement(border_fill, f"{{{NS_HEAD}}}{side}", {"type": "SOLID", "width": "0.12 mm", "color": "#333333"})
    ET.SubElement(border_fill, f"{{{NS_HEAD}}}diagonal", {"type": "NONE", "width": "0.1 mm", "color": "#000000"})
    if face_color:
        fill_brush = ET.SubElement(border_fill, f"{{{NS_CORE}}}fillBrush")
        ET.SubElement(fill_brush, f"{{{NS_CORE}}}winBrush", {"faceColor": face_color, "hatchColor": "#999999", "alpha": "0"})
    return border_fill


def package_hwpx(section_xml: str, preview: str) -> None:
    """정상 HWPX 템플릿을 복사하고 본문 섹션만 교체한다."""
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"HWPX 템플릿을 찾을 수 없습니다: {TEMPLATE}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE, "r") as src, zipfile.ZipFile(OUTPUT, "w") as dst:
        replacements = {
            "Contents/header.xml": _prepare_header_xml(src.read("Contents/header.xml")),
            "Contents/section0.xml": section_xml.encode("utf-8"),
            "Preview/PrvText.txt": preview.encode("utf-8"),
        }
        for info in src.infolist():
            data = replacements.get(info.filename, src.read(info.filename))
            out = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            out.compress_type = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            out.external_attr = info.external_attr
            dst.writestr(out, data)


def main():
    print("=== HWPX 생성 시작 ===")

    # 1. 마크다운 파싱
    all_blocks = []
    for fname in CHAPTER_FILES:
        fpath = CHAPTERS_DIR / fname
        if not fpath.exists():
            print(f"  [SKIP] {fname} — 파일 없음")
            continue
        print(f"  [READ] {fname}")
        blocks = parse_markdown(fpath)
        all_blocks.extend(blocks)
        # 장 구분 빈 줄
        all_blocks.append({"kind": "paragraph", "level": 0, "text": ""})

    print(f"  총 {len(all_blocks)}개 블록 파싱 완료")

    # 2. XML 생성
    section_xml = build_section_xml(all_blocks)
    preview = "전주교육대학교 교육전문대학원 설치 정책연구 최종보고서 초안"

    # 3. HWPX (ZIP) 패키징
    package_hwpx(section_xml, preview)

    fsize = OUTPUT.stat().st_size
    print(f"\n=== 완료: {OUTPUT} ({fsize:,} bytes) ===")


if __name__ == "__main__":
    main()
