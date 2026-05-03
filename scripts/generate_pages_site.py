"""Generate the GitHub Pages static dashboard for the JNUE policy project."""

from __future__ import annotations

import html
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analyzer import (  # noqa: E402
    get_competition_rates,
    get_major_comparison,
    get_major_heatmap_data,
    get_overview_metrics,
    get_student_summary,
    get_timeline_data,
)
from src.charts import create_major_heatmap, create_status_table_chart, create_timeline_chart  # noqa: E402
from src.data_loader import GRADUATE_SCHOOL_STATUS  # noqa: E402

DOCS_DIR = ROOT / "docs"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def metric(label: str, value: str, note: str = "") -> str:
    note_html = f"<span>{esc(note)}</span>" if note else ""
    return f"""
    <article class="metric-card">
      <div class="metric-label">{esc(label)}</div>
      <strong>{esc(value)}</strong>
      {note_html}
    </article>
    """


def table(df: pd.DataFrame) -> str:
    if df.empty:
        return '<p class="muted">표시할 데이터가 없습니다.</p>'
    header = "".join(f"<th>{esc(col)}</th>" for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        rows.append("<tr>" + "".join(f"<td>{esc(row[col])}</td>" for col in df.columns) + "</tr>")
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def plot(fig: go.Figure, include_plotlyjs: str | bool = False) -> str:
    return pio.to_html(
        fig,
        include_plotlyjs=include_plotlyjs,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )


def status_table() -> pd.DataFrame:
    df = GRADUATE_SCHOOL_STATUS.copy()
    df["설치여부"] = df["교육전문대학원_설치"].map({True: "설치", False: "미설치"})
    df["설치연도"] = df["설치연도"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    df["박사전공수"] = df["박사전공수"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    return df[["대학교", "소재지", "설치여부", "설치연도", "설치방식", "박사전공수"]]


def major_bar_chart() -> go.Figure:
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


def major_summary() -> pd.DataFrame:
    majors = get_major_comparison()
    if majors.empty:
        return pd.DataFrame()
    return (
        majors.groupby(["대학교", "분야"])
        .size()
        .reset_index(name="전공수")
        .sort_values(["대학교", "분야"])
    )


def student_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
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


def jnue_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
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


def competition_chart(comp: pd.DataFrame) -> go.Figure | None:
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


def decline_table(summary: pd.DataFrame) -> pd.DataFrame:
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


def build_site() -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = get_overview_metrics()
    summary = get_student_summary()
    comp = get_competition_rates()

    plots: list[str] = [
        plot(create_status_table_chart(GRADUATE_SCHOOL_STATUS), include_plotlyjs="cdn"),
        plot(create_timeline_chart(get_timeline_data())),
        plot(major_bar_chart()),
        plot(create_major_heatmap(get_major_heatmap_data())),
    ]
    student_trend = student_trend_chart(summary)
    if student_trend:
        plots.append(plot(student_trend))
    jnue_trend = jnue_trend_chart(summary)
    if jnue_trend:
        plots.append(plot(jnue_trend))
    competition = competition_chart(comp)
    if competition:
        plots.append(plot(competition))

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>전주교대 교육전문대학원 정책연구 대시보드</title>
  <meta name="description" content="전주교육대학교 교육전문대학원 설치 정책연구 분석 결과 정적 대시보드">
  <style>
    :root {{ --ink:#17212b; --muted:#5d6a78; --line:#d9e1e8; --panel:#f7fafc; --blue:#185c97; --gold:#b87512; --bg:#fff; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Arial,sans-serif; color:var(--ink); background:var(--bg); line-height:1.6; }}
    header {{ border-bottom:1px solid var(--line); background:linear-gradient(180deg,#f6fbff 0%,#fff 100%); }}
    .wrap {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; }}
    .hero {{ padding:42px 0 28px; }}
    .eyebrow {{ margin:0 0 10px; color:var(--blue); font-size:14px; font-weight:700; }}
    h1 {{ margin:0; font-size:clamp(30px,5vw,52px); line-height:1.12; letter-spacing:0; }}
    h2 {{ margin:0 0 18px; font-size:26px; letter-spacing:0; }}
    h3 {{ margin:0 0 12px; font-size:18px; letter-spacing:0; }}
    p {{ margin:0 0 12px; }}
    .lead {{ max-width:860px; margin-top:18px; color:#33475b; font-size:18px; }}
    nav {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:24px; }}
    nav a {{ display:inline-flex; min-height:38px; align-items:center; padding:8px 13px; border:1px solid var(--line); border-radius:6px; color:var(--ink); background:#fff; text-decoration:none; font-weight:650; }}
    main section {{ padding:34px 0; border-bottom:1px solid var(--line); }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:22px; }}
    .metric-card,.panel {{ padding:18px; border:1px solid var(--line); border-radius:8px; background:var(--panel); }}
    .metric-label {{ color:var(--muted); font-size:14px; font-weight:700; }}
    .metric-card strong {{ display:block; margin-top:8px; font-size:30px; line-height:1.1; }}
    .metric-card span {{ display:block; margin-top:8px; color:var(--muted); font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; align-items:start; }}
    .plot {{ min-height:420px; border:1px solid var(--line); border-radius:8px; padding:10px; background:#fff; overflow:hidden; }}
    .table-wrap {{ width:100%; overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:#fff; }}
    table {{ width:100%; min-width:680px; border-collapse:collapse; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }}
    th {{ background:#eef5fb; color:#18344f; font-weight:750; }}
    .note {{ padding:16px; border-left:4px solid var(--gold); background:#fff8ec; color:#47351d; }}
    .muted {{ color:var(--muted); }}
    footer {{ padding:28px 0 42px; color:var(--muted); font-size:14px; }}
    @media (max-width:860px) {{ .metrics,.grid {{ grid-template-columns:1fr; }} .hero {{ padding-top:30px; }} h1 {{ font-size:34px; }} }}
  </style>
</head>
<body>
  <header><div class="wrap hero">
    <p class="eyebrow">GitHub Pages 정적 대시보드</p>
    <h1>전주교대 교육전문대학원 설치 정책연구</h1>
    <p class="lead">Streamlit 서버 없이 열람 가능한 분석 결과 대시보드입니다. 전국 교대 설치 현황, 전공 비교, 학생 통계, 경쟁률, 설치 당위성, 학칙 개정 핵심 논리를 한 화면에서 확인할 수 있습니다.</p>
    <nav><a href="#overview">현황</a><a href="#majors">전공</a><a href="#students">학생 통계</a><a href="#rationale">설치 당위성</a><a href="#governance">학칙 개정</a><a href="#downloads">산출물</a></nav>
    <div class="metrics">
      {metric("전체 교육대학교", f"{metrics['총_교대수']}개교")}
      {metric("교육전문대학원 설치", f"{metrics['설치_완료']}개교", "2026년 현재 분석 기준")}
      {metric("미설치 대학", f"{metrics['미설치']}개교", ", ".join(metrics["미설치_대학"]))}
      {metric("설치 비율", metrics["설치_비율"], "전국 10개 교대 기준")}
    </div>
  </div></header>
  <main class="wrap">
    <section id="overview"><h2>1. 설치 현황</h2><p class="note">전국 10개 교육대학교 중 7개교가 교육전문대학원을 설치했으며, 전주교대는 부산교대·춘천교대와 함께 미설치 그룹에 남아 있습니다.</p><div class="grid"><div class="plot">{plots[0]}</div><div class="plot">{plots[1]}</div></div><h3>설치 현황 표</h3>{table(status_table())}</section>
    <section id="majors"><h2>2. 박사전공 비교</h2><div class="grid"><div class="plot">{plots[2]}</div><div class="panel"><h3>전공 설계 시사점</h3><p>신설 대학은 병설형을 채택하면서 교과교육, 교육학, 상담·특수, AI·융합 영역을 조합하고 있습니다. 전주교대는 신청 단계에서는 7개 전공을 포괄하되, 1기 운영은 수요와 지도교수 확보 수준에 따라 4~5개 전공부터 단계 개설하는 방식이 적절합니다.</p>{table(major_summary())}</div></div><div class="plot">{plots[3]}</div></section>
    <section id="students"><h2>3. 학생 통계와 경쟁률</h2><div class="grid"><div class="plot">{plots[4] if len(plots)>4 else '<p class="muted">학생 통계 데이터가 없습니다.</p>'}</div><div class="plot">{plots[5] if len(plots)>5 else '<p class="muted">전주교대 추이 데이터가 없습니다.</p>'}</div></div><div class="plot">{plots[6] if len(plots)>6 else '<p class="muted">경쟁률 데이터가 없습니다.</p>'}</div><h3>재학생 변화율 요약</h3>{table(decline_table(summary))}</section>
    <section id="rationale"><h2>4. 설치 당위성</h2><div class="grid"><article class="panel"><h3>정책 흐름</h3><p>2025년 대구·광주·공주·청주·진주교대가 병설형 교육전문대학원을 설치하면서, 교육대학교의 박사과정 운영은 예외가 아니라 확산 단계로 이동했습니다.</p></article><article class="panel"><h3>전주교대 과제</h3><p>전주교대 교육대학원은 재학생 감소와 낮은 충원율 문제를 동시에 겪고 있습니다. 교육전문대학원은 석사 재교육 중심 구조를 박사 수준의 연구·실천형 전문성 개발 체제로 확장하는 방안입니다.</p></article><article class="panel"><h3>운영 원칙</h3><p>1기 정원은 20~24명, 실제 개설 전공은 4~5개부터 시작하고, 충원율과 지도교수 확보를 확인한 뒤 단계적으로 확대하는 보수적 모델이 적절합니다.</p></article><article class="panel"><h3>교원 확보</h3><p>핵심 리스크는 전임교원 7명 소속 이동입니다. 학부 6시간 + 대학원 3시간의 겸보 모델, 책임시수 통합 산정, 교연비·업적평가 실적 인정이 함께 설계되어야 합니다.</p></article></div></section>
    <section id="governance"><h2>5. 학칙 개정 핵심</h2><p class="note">전주교대 학칙 개정은 단순히 제3조에 교육전문대학원을 추가하는 방식으로는 부족합니다. 전임교원 7명의 신분보장, 학부 수업권 보호, 책임시수 인정, 교연비·업적평가 불이익 금지를 함께 담는 신분보장형 패키지 개정이 필요합니다.</p><div class="grid"><article class="panel"><h3>본칙 핵심 조항</h3><p>제4조의2를 신설해 전임교원의 소속 변경, 겸무·겸보, 학부 겸무 범위에서의 소속 간주, 학부·교육대학원·교육전문대학원 강의시간 통합 산정, 불이익 금지 원칙을 둡니다.</p></article><article class="panel"><h3>하위규정 연동</h3><p>교연비 금액이나 배점을 학칙에 직접 쓰지 않고, 학칙은 실적 인정과 불이익 금지 원칙을 둡니다. 세부 기준은 학사운영규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준으로 위임합니다.</p></article></div></section>
    <section id="downloads"><h2>6. 산출물</h2><p>정적 대시보드는 <code>scripts/generate_pages_site.py</code>로 생성됩니다. GitHub Actions가 main 브랜치 푸시 시 자동으로 이 페이지를 빌드해 GitHub Pages에 배포합니다.</p><p class="muted">생성 시각: {esc(generated_at)}</p></section>
  </main>
  <footer><div class="wrap"><p>전주교육대학교 교육전문대학원 설치 정책연구 정적 대시보드. 데이터와 산식은 저장소의 <code>src/</code>, <code>data/</code>, <code>reports/chapters/</code> 원자료를 기준으로 생성됩니다.</p></div></footer>
</body>
</html>
"""


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(build_site(), encoding="utf-8")
    print(f"Generated {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
