"""KESS 엑셀 및 기타 데이터 소스 로딩/전처리 모듈."""

import pathlib
import glob
import re
import pandas as pd

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

# 10개 교육대학교 키워드 (학교명 매칭용)
_교대_KEYWORDS = [
    "경인교육대학교", "서울교육대학교", "부산교육대학교", "대구교육대학교",
    "광주교육대학교", "전주교육대학교", "춘천교육대학교", "청주교육대학교",
    "진주교육대학교", "공주교육대학교",
]

_교대_SHORT = {
    "경인교육대학교": "경인교대", "서울교육대학교": "서울교대",
    "부산교육대학교": "부산교대", "대구교육대학교": "대구교대",
    "광주교육대학교": "광주교대", "전주교육대학교": "전주교대",
    "춘천교육대학교": "춘천교대", "청주교육대학교": "청주교대",
    "진주교육대학교": "진주교대", "공주교육대학교": "공주교대",
}


def _short_name(full_name: str) -> str:
    """학교명에서 교대 약칭을 추출한다."""
    for full, short in _교대_SHORT.items():
        if full in full_name:
            return short
    return full_name


def _is_교대_대학원(school_name: str) -> bool:
    """학교명이 교육대학교의 대학원(교육대학원 또는 교육전문대학원)인지 판별."""
    return any(kw in school_name for kw in _교대_KEYWORDS) and (
        "교육대학원" in school_name or "교육전문대학원" in school_name
    )


def _detect_header_row(filepath: str) -> int:
    """엑셀 파일에서 '연도' 컬럼이 있는 헤더 행 번호를 찾는다."""
    df_raw = pd.read_excel(filepath, engine="openpyxl", header=None, nrows=20)
    for i in range(20):
        row_vals = [str(v) for v in df_raw.iloc[i].values]
        if "연도" in row_vals and "학제" in row_vals:
            return i
    return 13  # fallback


def load_sangbangi(filepath: str) -> pd.DataFrame:
    """상반기 KESS 파일에서 교육대학교 교육대학원/교육전문대학원 행만 추출한다."""
    header_row = _detect_header_row(filepath)
    df = pd.read_excel(filepath, engine="openpyxl", header=None, skiprows=header_row)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    # 교대 교육대학원 + 교육전문대학원 필터
    mask = df["학교명"].astype(str).apply(_is_교대_대학원)
    filtered = df[mask].copy()

    # 약칭 및 대학원유형 추가
    filtered["대학교"] = filtered["학교명"].apply(_short_name)
    filtered["대학원유형"] = filtered["학교명"].apply(
        lambda x: "교육전문대학원" if "교육전문대학원" in str(x) else "교육대학원"
    )

    # 숫자 컬럼 변환
    numeric_cols = [c for c in filtered.columns if any(
        k in str(c) for k in ["학과수", "입학정원", "모집인원", "지원자", "입학자",
                               "재적생", "재학생", "휴학생", "졸업자", "전임교원",
                               "비전임교원", "직원", "외국"]
    )]
    for col in numeric_cols:
        filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0).astype(int)

    filtered["연도"] = pd.to_numeric(filtered["연도"], errors="coerce").astype(int)
    return filtered


def load_habangi(filepath: str) -> pd.DataFrame:
    """하반기 KESS 파일에서 교육대학교 교육대학원/교육전문대학원 행만 추출한다."""
    header_row = _detect_header_row(filepath)
    df = pd.read_excel(filepath, engine="openpyxl", header=None, skiprows=header_row)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    mask = df["학교명"].astype(str).apply(_is_교대_대학원)
    filtered = df[mask].copy()

    filtered["대학교"] = filtered["학교명"].apply(_short_name)
    filtered["대학원유형"] = filtered["학교명"].apply(
        lambda x: "교육전문대학원" if "교육전문대학원" in str(x) else "교육대학원"
    )

    numeric_cols = [c for c in filtered.columns if any(
        k in str(c) for k in ["학과수", "재적생", "재학생", "휴학생", "전임교원",
                               "비전임교원", "시간강사", "외국인"]
    )]
    for col in numeric_cols:
        filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0).astype(int)

    filtered["연도"] = pd.to_numeric(filtered["연도"], errors="coerce").astype(int)
    return filtered


def load_all_sangbangi() -> pd.DataFrame:
    """data/kess/ 내 모든 상반기 파일을 통합 로드한다."""
    files = sorted(glob.glob(str(DATA_DIR / "kess" / "*상반기*")))
    if not files:
        return pd.DataFrame()
    frames = [load_sangbangi(f) for f in files]
    return pd.concat(frames, ignore_index=True)


def load_all_habangi() -> pd.DataFrame:
    """data/kess/ 내 모든 하반기 파일을 통합 로드한다."""
    files = sorted(glob.glob(str(DATA_DIR / "kess" / "*하반기*")))
    if not files:
        return pd.DataFrame()
    frames = [load_habangi(f) for f in files]
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# 통합 데이터 로드 (모듈 import 시 자동 실행)
# ---------------------------------------------------------------------------

_sangbangi_cache = None
_habangi_cache = None


def get_sangbangi() -> pd.DataFrame:
    global _sangbangi_cache
    if _sangbangi_cache is None:
        _sangbangi_cache = load_all_sangbangi()
    return _sangbangi_cache


def get_habangi() -> pd.DataFrame:
    global _habangi_cache
    if _habangi_cache is None:
        _habangi_cache = load_all_habangi()
    return _habangi_cache


# ---------------------------------------------------------------------------
# 정적 데이터 (KESS에 없는 메타 정보)
# ---------------------------------------------------------------------------

UNIVERSITIES = [
    "경인교대", "서울교대", "부산교대", "대구교대", "광주교대",
    "전주교대", "춘천교대", "청주교대", "진주교대", "공주교대",
]

GRADUATE_SCHOOL_STATUS = pd.DataFrame({
    "대학교": UNIVERSITIES,
    "소재지": ["인천/경기", "서울", "부산", "대구", "광주", "전북", "강원", "충북", "경남", "충남"],
    "교육전문대학원_설치": [True, True, False, True, True, False, False, True, True, True],
    "설치연도": pd.array([2013, 2013, pd.NA, 2024, 2024, pd.NA, pd.NA, 2025, 2025, 2025], dtype=pd.Int64Dtype()),
    "설치방식": ["전환", "전환", "-", "병설", "병설", "-", "-", "병설", "병설", "병설"],
    "박사전공수": pd.array([13, 14, pd.NA, 8, 8, pd.NA, pd.NA, 10, 8, 7], dtype=pd.Int64Dtype()),
})

MAJORS_DATA = pd.DataFrame({
    "대학교": [
        # 경인교대 (2013 전환) — 13개
        "경인교대", "경인교대", "경인교대", "경인교대", "경인교대",
        "경인교대", "경인교대", "경인교대", "경인교대", "경인교대",
        "경인교대", "경인교대", "경인교대",
        # 서울교대 (2013 전환) — 14개
        "서울교대", "서울교대", "서울교대", "서울교대", "서울교대",
        "서울교대", "서울교대", "서울교대", "서울교대", "서울교대",
        "서울교대", "서울교대", "서울교대", "서울교대",
        # 광주교대 (2024 병설) — 8개
        "광주교대", "광주교대", "광주교대", "광주교대",
        "광주교대", "광주교대", "광주교대", "광주교대",
        # 대구교대 (2024 병설) — 8개
        "대구교대", "대구교대", "대구교대", "대구교대",
        "대구교대", "대구교대", "대구교대", "대구교대",
        # 진주교대 (2025 병설) — 8개
        "진주교대", "진주교대", "진주교대", "진주교대",
        "진주교대", "진주교대", "진주교대", "진주교대",
        # 공주교대 (2025 병설) — 7개
        "공주교대", "공주교대", "공주교대", "공주교대",
        "공주교대", "공주교대", "공주교대",
        # 청주교대 (2025 병설) — 10개
        "청주교대", "청주교대", "청주교대", "청주교대", "청주교대",
        "청주교대", "청주교대", "청주교대", "청주교대", "청주교대",
    ],
    "전공명": [
        # 경인교대 13개
        "교육행정/교육사회", "교육방법", "국어교육", "사회과교육", "수학교육",
        "과학교육", "음악교육", "미술교육", "영어교육", "체육교육",
        "컴퓨터교육", "윤리/인성교육", "학생상담/특수교육",
        # 서울교대 14개
        "초등윤리/인성교육", "초등국어교육", "초등사회과교육", "초등수학교육", "초등과학교육",
        "초등체육교육", "초등음악교육", "초등미술교육", "초등생활과학/컴퓨터교육", "교육정책및리더십",
        "교육심리/상담/특수교육", "교육연극/다문화교육", "박물관/미술관교육", "초등영어교육",
        # 광주교대 8개
        "윤리·철학교육", "지속가능환경·시민교육", "과학교육", "체육교육",
        "교육과정과수업", "교육행정·정책", "교육심리·상담·특수교육", "컴퓨터교육",
        # 대구교대 8개
        "윤리인성교육", "초등국어교육", "초등수학교육", "초등과학교육",
        "초등체육교육", "초등영어교육", "특수통합·유아교육", "AI교육",
        # 진주교대 8개
        "사회과교육", "과학교육", "과학영재교육", "체육교육",
        "문화예술콘텐츠", "문화예술경영정책", "컴퓨터교육", "학교상담",
        # 공주교대 7개
        "AI융합교육", "교육상담", "국어교육", "다문화교육",
        "상담심리", "아동청소년교육·상담", "유아교육",
        # 청주교대 10개
        "윤리·인성교육", "초등국어교육", "수학교육", "융합과학과영재교육", "체육교육",
        "음악교육", "교육학", "심리·상담·특수교육", "어린이영어융합교육", "유아및아동교육",
    ],
    "분야": [
        # 경인교대
        "교육학", "교육학", "교과교육", "교과교육", "교과교육",
        "교과교육", "교과교육", "교과교육", "교과교육", "교과교육",
        "교과교육", "교과교육", "교육학",
        # 서울교대
        "교과교육", "교과교육", "교과교육", "교과교육", "교과교육",
        "교과교육", "교과교육", "교과교육", "교과교육", "교육학",
        "교육학", "융합교육", "융합교육", "교과교육",
        # 광주교대
        "교과교육", "융합교육", "교과교육", "교과교육",
        "교육학", "교육학", "교육학", "교과교육",
        # 대구교대
        "교과교육", "교과교육", "교과교육", "교과교육",
        "교과교육", "교과교육", "교육학", "융합교육",
        # 진주교대
        "교과교육", "교과교육", "교과교육", "교과교육",
        "융합교육", "융합교육", "교과교육", "교육학",
        # 공주교대
        "융합교육", "교육학", "교과교육", "융합교육",
        "교육학", "교육학", "교육학",
        # 청주교대
        "교과교육", "교과교육", "교과교육", "융합교육", "교과교육",
        "교과교육", "교육학", "교육학", "융합교육", "교육학",
    ],
})
