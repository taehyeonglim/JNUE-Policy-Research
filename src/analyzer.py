"""타 교대 교육전문대학원 비교 분석 로직."""

import pandas as pd
from src.data_loader import (
    GRADUATE_SCHOOL_STATUS,
    MAJORS_DATA,
    get_sangbangi,
    get_habangi,
)


def get_overview_metrics() -> dict:
    """현황 개요 핵심 지표를 반환한다."""
    df = GRADUATE_SCHOOL_STATUS
    total = len(df)
    installed = df["교육전문대학원_설치"].sum()
    return {
        "총_교대수": total,
        "설치_완료": int(installed),
        "미설치": total - int(installed),
        "설치_비율": f"{installed / total * 100:.0f}%",
        "미설치_대학": df.loc[~df["교육전문대학원_설치"], "대학교"].tolist(),
    }


def get_timeline_data() -> pd.DataFrame:
    """설치 연도별 타임라인 데이터를 반환한다."""
    df = GRADUATE_SCHOOL_STATUS.dropna(subset=["설치연도"]).copy()
    df["설치연도"] = df["설치연도"].astype(int)
    timeline = df.groupby("설치연도").agg(
        대학수=("대학교", "count"),
        대학목록=("대학교", lambda x: ", ".join(x)),
    ).reset_index()
    timeline["누적"] = timeline["대학수"].cumsum()
    return timeline


def get_major_comparison() -> pd.DataFrame:
    return MAJORS_DATA


def get_major_heatmap_data() -> pd.DataFrame:
    standardized = {
        # 국어
        "국어교육": "국어교육", "초등국어교육": "국어교육",
        # 사회
        "사회과교육": "사회과교육", "초등사회과교육": "사회과교육",
        # 수학
        "수학교육": "수학교육", "초등수학교육": "수학교육",
        # 과학
        "과학교육": "과학교육", "초등과학교육": "과학교육",
        # 음악
        "음악교육": "음악교육", "초등음악교육": "음악교육", "음악교육학": "음악교육",
        # 미술
        "미술교육": "미술교육", "초등미술교육": "미술교육",
        # 체육
        "체육교육": "체육교육", "초등체육교육": "체육교육", "체육학과": "체육교육",
        # 영어
        "영어교육": "영어교육", "초등영어교육": "영어교육", "어린이영어융합교육": "영어교육",
        # 컴퓨터/AI
        "컴퓨터교육": "컴퓨터교육", "초등생활과학/컴퓨터교육": "컴퓨터교육",
        "AI교육": "AI/컴퓨터교육", "AI융합교육": "AI/컴퓨터교육",
        # 윤리/인성
        "윤리/인성교육": "윤리·인성교육", "초등윤리/인성교육": "윤리·인성교육",
        "윤리·철학교육": "윤리·인성교육", "윤리인성교육": "윤리·인성교육",
        "윤리·인성교육": "윤리·인성교육",
        # 상담/특수
        "학생상담/특수교육": "상담·특수교육", "교육심리/상담/특수교육": "상담·특수교육",
        "교육심리·상담·특수교육": "상담·특수교육", "심리·상담·특수교육": "상담·특수교육",
        "학교상담": "상담·특수교육", "교육상담": "상담·특수교육", "상담심리": "상담·특수교육",
        "특수통합·유아교육": "유아/특수교육",
        # 유아
        "유아교육": "유아교육", "유아및아동교육": "유아교육", "아동청소년교육·상담": "유아교육",
        # 교육학/행정
        "교육행정/교육사회": "교육행정·정책", "교육정책및리더십": "교육행정·정책",
        "교육행정·정책": "교육행정·정책", "교육학": "교육학",
        "교육방법": "교육방법", "교육과정과수업": "교육방법",
        # 과학영재
        "과학영재교육": "과학영재교육", "융합과학과영재교육": "과학영재교육",
        # 다문화
        "다문화교육": "다문화교육", "교육연극/다문화교육": "다문화교육",
    }
    df = MAJORS_DATA.copy()
    df["표준전공"] = df["전공명"].map(standardized).fillna(df["전공명"])
    pivot = df.pivot_table(index="표준전공", columns="대학교", aggfunc="size", fill_value=0)
    return pivot


# ---------------------------------------------------------------------------
# KESS 실제 데이터 기반 분석 함수
# ---------------------------------------------------------------------------

def get_student_stats() -> pd.DataFrame:
    """상반기 KESS 데이터에서 교대별 대학원 재학생 통계를 추출한다."""
    df = get_sangbangi()
    if df.empty:
        return pd.DataFrame()

    # 교육대학원 + 교육전문대학원 모두 포함
    cols_to_keep = ["연도", "대학교", "대학원유형", "학교명"]
    # 재학생 관련 컬럼 찾기
    재학생_cols = [c for c in df.columns if "재학생" in str(c)]
    학과수_cols = [c for c in df.columns if "학과수" in str(c)]
    입학자_cols = [c for c in df.columns if "입학자_전체" in str(c) or "입학자_석사" in str(c) or "입학자_박사" in str(c)]
    졸업자_cols = [c for c in df.columns if "졸업자" in str(c)]

    all_cols = cols_to_keep + 재학생_cols + 학과수_cols + 입학자_cols + 졸업자_cols
    available_cols = [c for c in all_cols if c in df.columns]

    result = df[available_cols].copy()
    return result


def get_student_summary() -> pd.DataFrame:
    """교대별/연도별 교육대학원 재학생 요약 (대시보드용)."""
    df = get_sangbangi()
    if df.empty:
        return pd.DataFrame()

    summary_rows = []
    for _, row in df.iterrows():
        entry = {
            "연도": row["연도"],
            "대학교": row["대학교"],
            "대학원유형": row["대학원유형"],
        }
        # 컬럼명이 파일마다 약간 다를 수 있으므로 안전하게 접근
        for col_key, col_names in {
            "재학생_전체": ["재학생_전체_계"],
            "재학생_석사": ["재학생_석사_계"],
            "재학생_박사": ["재학생_박사_계"],
            "학과수_전체": ["학과수_전체"],
            "학과수_석사": ["학과수_석사"],
            "학과수_박사": ["학과수_박사"],
            "입학자_전체": ["입학자_전체_계"],
            "입학자_석사": ["입학자_석사_계"],
            "입학자_박사": ["입학자_박사_계"],
            "졸업자_전체": ["졸업자_전체_계"],
            "졸업자_석사": ["졸업자_석사_계"],
            "졸업자_박사": ["졸업자_박사_계"],
            "지원자_전체": ["지원자_전체_계"],
            "지원자_석사": ["지원자_석사_계"],
            "지원자_박사": ["지원자_박사_계"],
            "모집인원": ["모집인원_계"],
            "입학정원_전체": ["입학정원_전체"],
        }.items():
            for cn in col_names:
                if cn in row.index:
                    entry[col_key] = row[cn]
                    break
            else:
                entry[col_key] = 0
        summary_rows.append(entry)

    return pd.DataFrame(summary_rows)


def get_competition_rates() -> pd.DataFrame:
    """상반기 데이터에서 경쟁률을 계산한다.

    모집인원이 0인 경우가 많아, 입학정원_전체를 기준으로 경쟁률을 계산한다.
    경쟁률 = 지원자 / 입학정원
    """
    summary = get_student_summary()
    if summary.empty:
        return pd.DataFrame()

    df = summary[(summary["입학정원_전체"] > 0) & (summary["지원자_전체"] > 0)].copy()
    df["경쟁률"] = (df["지원자_전체"] / df["입학정원_전체"]).round(2)
    return df[["연도", "대학교", "대학원유형", "입학정원_전체", "지원자_전체", "입학자_전체", "경쟁률"]]
