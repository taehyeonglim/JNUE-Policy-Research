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
PARA_NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
MAX_VISUAL_WIDTH = 110
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
    for text_node in paragraph.iter(TEXT_TAG):
        if text_node.text:
            lines[-1] += text_node.text
        for child in list(text_node):
            if child.tag == LINE_BREAK_TAG:
                lines.append(child.tail or "")
    return lines


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

            section = ET.fromstring(zf.read("Contents/section0.xml"))
            if section.tag != SECTION_TAG:
                errors.append(f"unexpected section tag: {section.tag}")

            paragraphs = section.findall(".//hp:p", PARA_NS)
            visual_lines: list[str] = []
            texts: list[str] = []
            for para in paragraphs:
                lines = paragraph_lines(para)
                visual_lines.extend(lines)
                texts.append(" ".join(line for line in lines if line))
            body = "\n".join(texts)
            if len(paragraphs) < 100:
                errors.append(f"too few paragraphs: {len(paragraphs)}")
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
