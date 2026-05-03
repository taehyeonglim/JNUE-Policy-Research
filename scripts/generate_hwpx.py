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


def parse_markdown(filepath):
    """마크다운 파일을 (level, text) 튜플 리스트로 변환.
    level: 0=본문, 1=#, 2=##, 3=###, 4=####
    """
    blocks = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_para = []
    in_table = False

    for line in lines:
        stripped = line.rstrip()

        # 빈 줄 → 현재 단락 종료
        if not stripped:
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            in_table = False
            continue

        # 헤딩
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append((level, text))
            continue

        # 구분선
        if stripped.startswith("---") and len(stripped.replace("-", "")) == 0:
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            continue

        # 표 행 (| ... |)
        if stripped.startswith("|"):
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            # 구분행 무시
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                continue
            # 표 내용을 텍스트로
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            blocks.append((0, "  |  ".join(cells)))
            continue

        # 인용 (>)
        if stripped.startswith(">"):
            text = stripped.lstrip("> ").strip()
            if text:
                current_para.append(text)
            continue

        # 볼드/이탤릭 마크다운 제거
        clean = stripped
        clean = clean.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
        clean = re.sub(r"\*(.+?)\*", r"\1", clean)
        clean = re.sub(r"`(.+?)`", r"\1", clean)
        clean = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", clean)

        # 리스트 항목
        list_match = re.match(r"^[\-\*]\s+(.+)$", clean)
        if list_match:
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            blocks.append((0, "• " + list_match.group(1)))
            continue

        numbered_match = re.match(r"^\d+[\.\)]\s+(.+)$", clean)
        if numbered_match:
            if current_para:
                blocks.append((0, " ".join(current_para)))
                current_para = []
            blocks.append((0, clean))
            continue

        current_para.append(clean)

    if current_para:
        blocks.append((0, " ".join(current_para)))

    return blocks


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


def build_section_xml(all_blocks):
    """섹션 XML (Contents/section0.xml) 생성."""
    for prefix, uri in HWPX_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    sec = ET.Element(f"{{{NS_SEC}}}sec")

    _add_paragraph(sec, 1, ["전주교육대학교 교육전문대학원 설치 정책연구"], 0)
    _add_paragraph(sec, 2, ["최종보고서 초안"], 1)
    _add_paragraph(sec, 0, ["생성 기준: reports/chapters 10개 장 원고"], 2)

    paragraph_index = 4
    for level, text in all_blocks:
        if not text.strip():
            paragraph_index += 1
            continue
        wrap_width = HEADING_WRAP_WIDTH if level else BODY_WRAP_WIDTH
        lines = _wrap_text(text, wrap_width)
        paragraph_index += _add_paragraph(sec, min(level, 4), lines, paragraph_index)

    return _xml_with_decl(sec)


def package_hwpx(section_xml: str, preview: str) -> None:
    """정상 HWPX 템플릿을 복사하고 본문 섹션만 교체한다."""
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"HWPX 템플릿을 찾을 수 없습니다: {TEMPLATE}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    replacements = {
        "Contents/section0.xml": section_xml.encode("utf-8"),
        "Preview/PrvText.txt": preview.encode("utf-8"),
    }

    with zipfile.ZipFile(TEMPLATE, "r") as src, zipfile.ZipFile(OUTPUT, "w") as dst:
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
        all_blocks.append((0, ""))

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
