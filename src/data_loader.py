"""KESS 엑셀 및 기타 데이터 소스 로딩/전처리 모듈."""

import pathlib
import glob
import re
import numpy as np
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
    "설치연도": pd.array([2013, 2013, pd.NA, 2025, 2025, pd.NA, pd.NA, 2025, 2025, 2025], dtype=pd.Int64Dtype()),
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
    "양성정원": [
        # 경인교대
        *([None] * 13),
        # 서울교대
        *([None] * 14),
        # 광주교대 — 32명
        *([32] * 8),
        # 대구교대 — 30→42명
        *([30] * 8),
        # 진주교대 — 30명
        *([30] * 8),
        # 공주교대 — 30명
        *([30] * 7),
        # 청주교대 — 33명
        *([33] * 10),
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


# ---------------------------------------------------------------------------
# 신규 데이터 로딩: 대학본부 제공 자료
# ---------------------------------------------------------------------------

_GRAD_CSV = DATA_DIR / "전국교대 대학원 현황" / "전국대학원 최근 5년간 현황.csv"
_JNUE_CSV = DATA_DIR / "전국교대 대학원 현황" / "전주교대 교육대학원(양성과정, 재교육과정 포함) 최근 5년간 현황.csv"
_ENROLLMENT_XLSX = DATA_DIR / "전국교대 대학원 현황" / "전국 교대 교육전문대학원 신입생 충원 현황.xlsx"
_COUNSELING_XLSX = DATA_DIR / "전국교대 대학원 현황" / "전주교대 교육대학원 상담 및 특수 전공(양성과정) 최근 10년 현황.xlsx"


def load_national_grad_status() -> pd.DataFrame:
    """전국교대 대학원 최근 5년간 현황 CSV를 로드한다."""
    if not _GRAD_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(_GRAD_CSV, encoding="utf-8-sig")
    return df


def load_doctoral_enrollment() -> pd.DataFrame:
    """전국 교대 교육전문대학원 박사과정 신입생 충원 현황을 파싱한다.

    복잡한 merged header 구조를 수동 파싱하여 학교별/전공별 충원 데이터를 반환.
    """
    if not _ENROLLMENT_XLSX.exists():
        return pd.DataFrame()

    df = pd.read_excel(_ENROLLMENT_XLSX, header=None, engine="openpyxl")

    records = []
    current_school = None
    current_capacity = None

    def _parse_major_row(row_data, school, capacity):
        """전공 데이터 행에서 충원 수치를 추출한다."""
        col2 = str(row_data.iloc[2]) if pd.notna(row_data.iloc[2]) else ""
        if not col2 or col2 in ("소계", "nan") or "※" in col2:
            return None

        # 각 학년도별 개별 충원 수치 합산 (수식 대신 직접 계산)
        # '24학년도: cols 3-7 (전기, 전기추가, 후기, 후기추가, 합계)
        # '25학년도: cols 8-12
        # '26학년도: cols 13-17
        # 충원누계: col 18 (엑셀 수식이라 0일 수 있음)

        def _sum_cols(row_data, start, end):
            """start~end-1 컬럼의 합계 (합계열 제외하고 개별값 합산)."""
            total = 0
            for i in range(start, end):
                v = pd.to_numeric(row_data.iloc[i], errors="coerce")
                if pd.notna(v):
                    total += int(v)
            return total

        # 합계열(index 7, 12, 17)을 먼저 시도, 0이면 개별 합산
        충원_24 = pd.to_numeric(row_data.iloc[7], errors="coerce")
        if pd.isna(충원_24) or 충원_24 == 0:
            충원_24 = _sum_cols(row_data, 3, 7)
        else:
            충원_24 = int(충원_24)

        충원_25 = pd.to_numeric(row_data.iloc[12], errors="coerce")
        if pd.isna(충원_25) or 충원_25 == 0:
            충원_25 = _sum_cols(row_data, 8, 12)
        else:
            충원_25 = int(충원_25)

        충원_26 = pd.to_numeric(row_data.iloc[17], errors="coerce")
        if pd.isna(충원_26) or 충원_26 == 0:
            충원_26 = _sum_cols(row_data, 13, 17)
        else:
            충원_26 = int(충원_26)

        누계 = 충원_24 + 충원_25 + 충원_26

        return {
            "대학교": school,
            "양성정원": capacity,
            "전공명": col2,
            "충원_24학년도": 충원_24,
            "충원_25학년도": 충원_25,
            "충원_26학년도": 충원_26,
            "충원누계": 누계,
        }

    for idx, row in df.iterrows():
        if idx < 5:
            continue  # 헤더 스킵

        col0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        col1 = row.iloc[1]
        col2 = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""

        # 학교명 감지
        if "교육대학교" in col0 or "교육전문대학원" in col0:
            current_school = col0.replace("\n", " ").strip()
            if pd.notna(col1):
                try:
                    current_capacity = int(col1)
                except (ValueError, TypeError):
                    capacity_str = str(col1)
                    nums = re.findall(r"\d+", capacity_str)
                    current_capacity = int(nums[0]) if nums else None

            # 학교명 행에도 전공 데이터가 있을 수 있음
            if col2 and col2 not in ("소계", "nan", ""):
                rec = _parse_major_row(row, current_school, current_capacity)
                if rec:
                    records.append(rec)
            continue

        # 소계 또는 빈 행 스킵
        if col2 in ("소계", "", "nan") or "※" in col2 or col2.startswith("※"):
            continue

        # 전공 데이터 행
        if current_school and col2 and col2 not in ("소계", "nan"):
            rec = _parse_major_row(row, current_school, current_capacity)
            if rec:
                records.append(rec)

    result = pd.DataFrame(records)

    # 대학교 약칭 변환
    if not result.empty:
        name_map = {
            "청주교육대학교 교육전문대학원": "청주교대",
            "진주교육대학교 교육전문대학원": "진주교대",
            "대구교육대학교 교육전문대학원": "대구교대",
            "광주교육대학교 교육전문대학원": "광주교대",
            "공주교육대학교 교육전문대학원": "공주교대",
        }
        result["대학교_약칭"] = result["대학교"].map(name_map).fillna(result["대학교"])

    return result


def load_counseling_special_10yr() -> dict[str, pd.DataFrame]:
    """전주교대 교육대학원 상담/특수 전공 최근 10년 현황을 로드한다.

    Returns: {"입학": DataFrame, "졸업": DataFrame}
    """
    if not _COUNSELING_XLSX.exists():
        return {"입학": pd.DataFrame(), "졸업": pd.DataFrame()}

    df = pd.read_excel(_COUNSELING_XLSX, header=None, engine="openpyxl")

    # 입학 인원 (rows 5-7, cols 5-15 → 2016-2026)
    years_admission = list(range(2016, 2027))
    admission_rows = []
    for i in [5, 6, 7]:
        if i >= len(df):
            continue
        major = str(df.iloc[i, 3]) if pd.notna(df.iloc[i, 3]) else ""
        cert = str(df.iloc[i, 4]) if pd.notna(df.iloc[i, 4]) else ""
        values = []
        for j, yr in enumerate(years_admission):
            val = pd.to_numeric(df.iloc[i, 5 + j], errors="coerce")
            values.append(int(val) if pd.notna(val) else None)
        admission_rows.append({"전공명": major, "자격종별": cert, **dict(zip(years_admission, values))})

    # 졸업 인원 (rows 13-15, cols 5-14 → 2017-2026)
    years_graduation = list(range(2017, 2027))
    graduation_rows = []
    for i in [13, 14, 15]:
        if i >= len(df):
            continue
        major = str(df.iloc[i, 3]) if pd.notna(df.iloc[i, 3]) else ""
        cert = str(df.iloc[i, 4]) if pd.notna(df.iloc[i, 4]) else ""
        values = []
        for j, yr in enumerate(years_graduation):
            val = pd.to_numeric(df.iloc[i, 5 + j], errors="coerce")
            values.append(int(val) if pd.notna(val) else None)
        graduation_rows.append({"전공명": major, "자격종별": cert, **dict(zip(years_graduation, values))})

    return {
        "입학": pd.DataFrame(admission_rows),
        "졸업": pd.DataFrame(graduation_rows),
    }


# 캐시
_national_grad_cache = None
_doctoral_enrollment_cache = None
_counseling_cache = None


def get_national_grad_status() -> pd.DataFrame:
    global _national_grad_cache
    if _national_grad_cache is None:
        _national_grad_cache = load_national_grad_status()
    return _national_grad_cache


def get_doctoral_enrollment() -> pd.DataFrame:
    global _doctoral_enrollment_cache
    if _doctoral_enrollment_cache is None:
        _doctoral_enrollment_cache = load_doctoral_enrollment()
    return _doctoral_enrollment_cache


def get_counseling_special_10yr() -> dict[str, pd.DataFrame]:
    global _counseling_cache
    if _counseling_cache is None:
        _counseling_cache = load_counseling_special_10yr()
    return _counseling_cache
