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
    """전공 원어명 그대로 히트맵 데이터를 생성한다."""
    df = MAJORS_DATA.copy()
    pivot = df.pivot_table(index="전공명", columns="대학교", aggfunc="size", fill_value=0)
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
