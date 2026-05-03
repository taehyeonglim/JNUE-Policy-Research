"""Validate that a generated HWPX report is structurally usable."""

from __future__ import annotations

import argparse
import sys
import unicodedata
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


REQUIRED_ENTRIES = {
    "mimetype",
    "version.xml",
    "Contents/content.hpf",
    "Contents/header.xml",
    "Contents/section0.xml",
    "Preview/PrvText.txt",
}
SECTION_TAG = "{http://www.hancom.co.kr/hwpml/2011/section}sec"
TEXT_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}t"
LINE_BREAK_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}lineBreak"
RUN_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}run"
TABLE_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}tbl"
BOLD_TAG = "{http://www.hancom.co.kr/hwpml/2011/head}bold"
PARA_NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
HEAD_NS = {"hh": "http://www.hancom.co.kr/hwpml/2011/head", "hc": "http://www.hancom.co.kr/hwpml/2011/core"}
MAX_VISUAL_WIDTH = 110
HEADING_CHAR_IDS = {"7", "10", "11"}
REQUIRED_TABLE_BORDER_IDS = {"3", "4"}
REQUIRED_TEXTS = [
    "전주교육대학교 교육전문대학원 설치 정책연구",
    "제I장 서론",
    "제IX장 결론",
    "부록 6. 원자료 추적표",
]


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1 for ch in text)


def paragraph_lines(paragraph: ET.Element) -> list[str]:
    lines = [""]
    for run in paragraph.findall(RUN_TAG):
        if run.find(TABLE_TAG) is not None:
            continue
        for text_node in run.findall(TEXT_TAG):
            _append_text_node_lines(lines, text_node)
    return lines


def _append_text_node_lines(lines: list[str], text_node: ET.Element) -> None:
        if text_node.text:
            lines[-1] += text_node.text
        for child in list(text_node):
            if child.tag == LINE_BREAK_TAG:
                lines.append(child.tail or "")


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join(line for line in paragraph_lines(paragraph) if line).strip()


def paragraph_char_id(paragraph: ET.Element) -> str:
    run = paragraph.find(RUN_TAG)
    return run.attrib.get("charPrIDRef", "") if run is not None else ""


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"file does not exist: {path}"]

    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            missing = REQUIRED_ENTRIES - names
            if missing:
                errors.append(f"missing entries: {', '.join(sorted(missing))}")

            infos = zf.infolist()
            if not infos:
                errors.append("zip has no entries")
                return errors
            first = infos[0]
            if first.filename != "mimetype":
                errors.append("mimetype is not the first ZIP entry")
            if first.compress_type != zipfile.ZIP_STORED:
                errors.append("mimetype is compressed")
            if "mimetype" in names and zf.read("mimetype").decode("utf-8") != "application/hwp+zip":
                errors.append("invalid mimetype content")

            for info in infos:
                with zf.open(info) as fh:
                    while fh.read(1024 * 1024):
                        pass

            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))
            if section.tag != SECTION_TAG:
                errors.append(f"unexpected section tag: {section.tag}")

            paragraphs = section.findall(".//hp:p", PARA_NS)
            top_level_paragraphs = section.findall("hp:p", PARA_NS)
            visual_lines: list[str] = []
            texts: list[str] = []
            for para in paragraphs:
                lines = paragraph_lines(para)
                visual_lines.extend(lines)
                texts.append(" ".join(line for line in lines if line))
            body = "\n".join(texts)
            if len(paragraphs) < 100:
                errors.append(f"too few paragraphs: {len(paragraphs)}")
            tables = section.findall(".//hp:tbl", PARA_NS)
            if not tables:
                errors.append("missing HWPX table objects")
            for required in REQUIRED_TEXTS:
                if required not in body:
                    errors.append(f"missing required text: {required}")
            too_wide = [
                (idx + 1, display_width(line), line[:80])
                for idx, line in enumerate(visual_lines)
                if display_width(line) > MAX_VISUAL_WIDTH
            ]
            if too_wide:
                sample = "; ".join(f"line {idx} width {width}: {text}" for idx, width, text in too_wide[:3])
                errors.append(f"visual lines exceed width {MAX_VISUAL_WIDTH}: {sample}")

            for char_id in HEADING_CHAR_IDS:
                char_pr = header.find(f".//hh:charPr[@id='{char_id}']", HEAD_NS)
                if char_pr is None or char_pr.find(BOLD_TAG) is None:
                    errors.append(f"heading charPr {char_id} is not bold")

            for border_id in REQUIRED_TABLE_BORDER_IDS:
                border_fill = header.find(f".//hh:borderFill[@id='{border_id}']", HEAD_NS)
                if border_fill is None:
                    errors.append(f"missing table borderFill {border_id}")
                    continue
                for side in ("leftBorder", "rightBorder", "topBorder", "bottomBorder"):
                    side_node = border_fill.find(f"hh:{side}", HEAD_NS)
                    if side_node is None or side_node.attrib.get("type") != "SOLID":
                        errors.append(f"table borderFill {border_id} has no solid {side}")
                if border_id == "4" and border_fill.find("hc:fillBrush", HEAD_NS) is None:
                    errors.append("table header borderFill 4 has no fillBrush")

            for idx, para in enumerate(top_level_paragraphs):
                if idx < 3 or paragraph_char_id(para) not in HEADING_CHAR_IDS or not paragraph_text(para):
                    continue
                previous_two = top_level_paragraphs[idx - 2 : idx]
                if len(previous_two) < 2 or any(paragraph_text(candidate) for candidate in previous_two):
                    errors.append(f"heading paragraph {idx + 1} is not preceded by two blank paragraphs")
                    break
    except (zipfile.BadZipFile, ET.ParseError, UnicodeDecodeError, KeyError) as exc:
        errors.append(f"parse error: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        errors = validate(path)
        if errors:
            failed = True
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
