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


def rows_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "".join(f"<th>{esc(col)}</th>" for col in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
    """


def plot(fig: go.Figure, include_plotlyjs: str | bool = False) -> str:
    return pio.to_html(fig, include_plotlyjs=include_plotlyjs, full_html=False, config={"displaylogo": False, "responsive": True})


def red(text: str) -> str:
    return f'<span class="revision">{esc(text)}</span>'


def paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{item}</p>" for item in items)


def status_table() -> pd.DataFrame:
    df = GRADUATE_SCHOOL_STATUS.copy()
    df["설치여부"] = df["교육전문대학원_설치"].map({True: "설치", False: "미설치"})
    df["설치연도"] = df["설치연도"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    df["박사전공수"] = df["박사전공수"].apply(lambda v: str(int(v)) if pd.notna(v) else "-")
    return df[["대학교", "소재지", "설치여부", "설치연도", "설치방식", "박사전공수"]]


def major_bar_chart() -> go.Figure:
    majors = get_major_comparison()
    counts = majors.groupby("대학교").size().reset_index(name="박사전공수").sort_values("박사전공수", ascending=False)
    fig = px.bar(counts, x="대학교", y="박사전공수", text="박사전공수", color="박사전공수", color_continuous_scale=["#b7d9f6", "#185c97"], title="교육전문대학원 박사전공 수 비교")
    fig.update_traces(textposition="outside")
    fig.update_layout(height=430, showlegend=False, coloraxis_showscale=False)
    return fig


def major_summary() -> pd.DataFrame:
    majors = get_major_comparison()
    if majors.empty:
        return pd.DataFrame()
    return majors.groupby(["대학교", "분야"]).size().reset_index(name="전공수").sort_values(["대학교", "분야"])


def student_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
    if summary.empty:
        return None
    total = summary.groupby(["연도", "대학교"], as_index=False)["재학생_전체"].sum()
    fig = px.line(total, x="연도", y="재학생_전체", color="대학교", markers=True, title="교대별 총 대학원 재학생 추이")
    fig.update_layout(height=480, yaxis_title="재학생 수")
    return fig


def jnue_trend_chart(summary: pd.DataFrame) -> go.Figure | None:
    if summary.empty:
        return None
    jnue = summary[summary["대학교"] == "전주교대"].sort_values("연도")
    if jnue.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=jnue["연도"], y=jnue["재학생_전체"], mode="lines+markers+text", text=jnue["재학생_전체"].astype(int), textposition="top center", name="재학생", line={"color": "#d64545", "width": 3}))
    fig.add_trace(go.Scatter(x=jnue["연도"], y=jnue["지원자_전체"], mode="lines+markers", name="지원자", line={"color": "#d58921", "dash": "dot"}))
    fig.update_layout(title="전주교대 교육대학원 재학생·지원자 추이", height=430)
    return fig


def competition_chart(comp: pd.DataFrame) -> go.Figure | None:
    if comp.empty:
        return None
    latest_year = int(comp["연도"].max())
    latest = comp[comp["연도"] == latest_year].copy().sort_values("경쟁률", ascending=False)
    fig = px.bar(latest, x="대학교", y="경쟁률", color="대학원유형", text="경쟁률", title=f"{latest_year}년 대학원 경쟁률 비교")
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
        rows.append({"대학교": university, f"{first_year} 재학생": int(first), f"{last_year} 재학생": int(last), "변화율": f"{(last - first) / first * 100:.1f}%"})
    return pd.DataFrame(rows).sort_values("변화율")


def split_comparison_view() -> str:
    rows = [
        {"article": "제2조", "original": ["<strong>제2조(교육목적 및 교육목표)</strong>", "① 우리 대학교의 교육목적은 도덕성과 전문성을 갖춘 유능하고 창의적인 초등교원을 양성하는 데 있다."], "revised": ["<strong>제2조(교육목적 및 교육목표)</strong>", f"① 우리 대학교의 교육목적은 도덕성과 전문성을 갖춘 유능하고 창의적인 초등교원을 양성하고, {red('초등교육의 발전에 기여하는 교육전문가 및 연구인력을 양성')}하는 데 있다."]},
        {"article": "제3조", "original": ["<strong>제3조(편제 및 학생정원)</strong>", "① 우리 대학교에 초등교육전공과정과 교육대학원을 둔다.", "② 우리 대학교의 입학정원은 「고등교육법시행령」 제28조제3항에 따라 매년 조정되는 인원으로 한다.", "③ 「고등교육법시행령」 제29조제2항에 해당하는 자를 선발하는 경우에는 그 정원이 따로 있는 것으로 본다."], "revised": ["<strong>제3조(편제 및 학생정원)</strong>", f"① 우리 대학교에 초등교육전공과정, 교육대학원 {red('및 교육전문대학원')}을 둔다.", f"② 우리 대학교의 입학정원은 「고등교육법 시행령」 제28조제3항 {red('및 관계 법령')}에 따라 매년 조정되는 인원으로 한다.", "③ 「고등교육법 시행령」 제29조제2항에 해당하는 자를 선발하는 경우에는 그 정원이 따로 있는 것으로 본다.", red("④ 교육전문대학원의 학위과정, 전공, 학생정원 및 운영에 관한 사항은 관계 법령과 이 학칙 및 교육전문대학원 학칙으로 정한다.")]},
        {"article": "제4조", "original": ["<strong>제4조(교육대학원)</strong>", "교육대학원의 학사운영에 필요한 사항은 교육대학원학칙으로 정한다."], "revised": [f"<strong>{red('제4조(대학원)')}</strong>", "① 교육대학원의 학사운영에 필요한 사항은 교육대학원 학칙으로 정한다.", red("② 교육전문대학원의 조직, 학위과정, 전공, 교육과정, 수업, 학위수여, 학생정원 및 학사운영에 필요한 사항은 교육전문대학원 학칙으로 정한다."), red("③ 교육대학원과 교육전문대학원은 교육과정, 교원, 시설, 행정지원 등을 상호 연계하여 운영할 수 있으며, 이에 필요한 사항은 총장이 따로 정한다.")]},
        {"article": "제4조의2", "original": ["<strong>&lt;신설&gt;</strong>", "현행 학칙에는 교육전문대학원 설치에 따른 전임교원의 소속 변경, 겸무·겸보, 교수시간 통합 산정, 신분보장 및 실적 인정 조항이 없다."], "revised": [f"<strong>{red('제4조의2(전임교원의 소속·겸무·교수시간 및 신분보장)')}</strong>", red("① 전임교원은 초등교육전공과정의 심화과정, 교육대학원 또는 교육전문대학원의 학과·전공에 소속될 수 있다."), red("② 총장은 교육·연구 및 학사운영상 필요하다고 인정하는 경우 관계 법령과 이 학칙 및 관련 규정에 따라 전임교원의 소속 변경, 겸무 또는 겸보를 명할 수 있다."), red("③ 소속 변경 또는 겸무·겸보는 전공 적합성, 연구실적, 교육전문대학원 전공 운영 필요성, 초등교육전공과정의 교육과정 운영에 미치는 영향, 해당 교원의 의견 및 관련 위원회의 심의를 고려하여 정한다."), red("④ 교육전문대학원 소속 전임교원이 초등교육전공과정의 심화과정 또는 교육대학원을 겸무·겸보하는 경우에는 그 겸무·겸보 범위에서 해당 심화과정 또는 교육대학원 소속 전임교원으로 본다."), red("⑤ 교육전문대학원 소속 전임교원은 초등교육전공과정, 교육대학원 및 교육전문대학원의 강의, 교육실습, 논문지도, 학위논문 심사, 학생지도, 전공운영 및 관련 보직을 담당할 수 있다."), red("⑥ 교육전문대학원 소속 전임교원이 담당하는 초등교육전공과정, 교육대학원 및 교육전문대학원의 강의시간은 제47조에 따른 교수시간 및 관련 규정에 따른 책임시간에 포함한다."), red("⑦ 총장은 교육전문대학원 설치·운영으로 초등교육전공과정의 수업권이 침해되지 아니하도록 매 학년도 교원 배치 및 수업분담 계획을 수립하여야 한다."), red("⑧ 전임교원은 교육전문대학원 소속 변경 또는 겸무·겸보를 이유로 임용, 승진, 재임용, 보수, 교육·연구 및 학생지도 비용, 교원업적평가, 성과평가, 연구년, 복무, 후생복지 및 그 밖의 근무조건에서 불리하게 처우받지 아니한다."), red("⑨ 교육전문대학원 소속 또는 겸무·겸보 교원의 교육전문대학원 강의, 논문지도, 학위논문 심사, 전공운영, 학생지도, 현장연계 연구 및 초등교육전공과정 겸무 업무는 교육·연구 및 학생지도 비용, 교원업적평가 및 성과평가에서 실적으로 인정한다."), red("⑩ 시행에 필요한 사항은 학사운영규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준, 직제 및 사무분장 규정, 보수·수당 관련 규정으로 정한다.")]},
        {"article": "제5조", "original": ["<strong>제5조(하부조직)</strong>", "② 교무처는 학칙관리, 교육공무원인사, 비전임 교원인사, 교육과정관리, 학적관리, 수업 및 성적관리, 교육실습, 학술연구지원, 그 밖의 총장이 정하는 사항을 분장한다."], "revised": ["<strong>제5조(하부조직)</strong>", f"② 교무처는 학칙관리, 교육공무원인사, 비전임 교원인사, 교육과정관리, 학적관리, 수업 및 성적관리, 교육실습, 학술연구지원, {red('교육전문대학원 설치에 따른 교원 소속·겸무·겸보 및 수업분담 조정')}, 그 밖의 총장이 정하는 사항을 분장한다."]},
        {"article": "제5조의4", "original": ["<strong>&lt;신설&gt;</strong>", "현행 학칙에는 교육전문대학원장, 전공주임교수, 교육전문대학원 보직의 설치 근거가 없다."], "revised": [f"<strong>{red('제5조의4(교육전문대학원장 등)')}</strong>", red("① 교육전문대학원에 교육전문대학원장을 두며, 교육전문대학원장은 부교수 이상의 전임교원으로 보한다."), red("② 교육전문대학원장은 총장의 명을 받아 교육전문대학원의 교무를 총괄하고, 소속 교직원을 감독하며, 학생을 지도한다."), red("③ 교육전문대학원에 전공주임교수 등 필요한 보직을 둘 수 있으며, 전공주임교수는 전임교원으로 보한다."), red("④ 교육전문대학원 전공주임교수는 초등교육전공과정의 교과과장 또는 교육대학원 전공주임교수를 겸보할 수 있다."), red("⑤ 교육전문대학원장, 전공주임교수 및 그 밖의 보직에 관한 세부사항은 교육전문대학원 학칙 및 직제 관련 규정으로 정한다.")]},
        {"article": "제29조의2", "original": ["<strong>제29조의2(수업방법)</strong>", "수업은 주간에 실시함을 원칙으로 한다. 다만, 특별한 경우 총장의 허가를 얻어 야간수업, 방송·통신에 의한 수업 및 현장실습수업 등을 할 수 있고, 이에 필요한 세부사항은 총장이 따로 정한다."], "revised": ["<strong>제29조의2(수업방법)</strong>", "① 초등교육전공과정의 수업은 주간에 실시함을 원칙으로 한다. 다만, 특별한 경우 총장의 허가를 얻어 야간수업, 방송·통신에 의한 수업 및 현장실습수업 등을 할 수 있고, 이에 필요한 세부사항은 총장이 따로 정한다.", red("② 교육대학원 및 교육전문대학원의 수업은 각 대학원 학칙에 따라 야간, 주말, 계절제, 집중수업, 원격수업, 현장실습수업 등으로 운영할 수 있다."), red("③ 총장은 제2항에 따른 수업 운영이 초등교육전공과정의 필수수업, 교육실습 및 학생지도에 지장을 주지 아니하도록 수업시간표와 교원 수업분담을 조정하여야 한다.")]},
        {"article": "제47조", "original": ["<strong>제47조(교수시간)</strong>", "① 우리 대학교 교원(강사 제외)의 교수시간은 매 학년도 30주를 기준으로 주당 9시간을 원칙으로 한다. 다만, 학사운영상 특별히 필요하다고 인정하는 경우에는 총장이 다르게 정할 수 있다.", "③ 보직교원에 대한 책임시간의 일부면제와 교원에 대한 초과강의시간의 제한에 대하여는 총장이 따로 정한다."], "revised": ["<strong>제47조(교수시간)</strong>", f"① 우리 대학교 교원(강사 제외)의 교수시간은 매 학년도 30주를 기준으로 주당 9시간을 원칙으로 하며, {red('초등교육전공과정, 교육대학원 및 교육전문대학원에서 담당한 강의시간을 통합하여 산정한다.')}", f"③ {red('보직교원, 교육전문대학원장, 교육전문대학원 전공주임교수, 교육전문대학원 소속 전임교원 및 겸무·겸보 교원')}에 대한 책임시간의 일부면제, 수업분담 기준과 교원에 대한 초과강의시간의 제한에 대하여는 총장이 따로 정한다.", red("④ 교육전문대학원 소속 전임교원의 초등교육전공과정 및 교육대학원 강의시간은 교수시간 및 책임시간에 포함하며, 소속 변경만을 이유로 교수시간 산정에서 불리하게 취급하지 아니한다.")]},
        {"article": "제66조", "original": ["<strong>제66조(위원회)</strong>", "① 우리 대학교에 교무위원회, 대학인사위원회, 대학원위원회, 대학입학전형관리위원회, 학생지도위원회, 장애학생특별지원위원회를 둔다.", "③ 위원회의 설치와 운영에 관한 사항은 총장이 따로 정한다."], "revised": ["<strong>제66조(위원회)</strong>", f"① 우리 대학교에 교무위원회, 대학인사위원회, 대학원위원회, {red('교육전문대학원위원회')}, 대학입학전형관리위원회, 학생지도위원회, 장애학생특별지원위원회를 둔다.", f"③ 위원회의 설치와 운영에 관한 사항은 총장이 따로 정한다. {red('다만, 교육전문대학원위원회는 교육전문대학원의 학사운영, 전공 설치·폐지, 교육과정, 학위수여, 교원 배치 및 그 밖에 교육전문대학원 운영에 관한 중요 사항을 심의한다.')}"]},
        {"article": "부칙", "original": ["<strong>&lt;신설&gt;</strong>", "현행 학칙에는 교육전문대학원 최초 설치와 최초 전임교원 7명 소속 변경, 학부 수업권 보호, 하위규정 정비에 관한 경과조치가 없다."], "revised": [f"<strong>{red('부칙')}</strong>", red("제1조(시행일) 이 학칙은 공포한 날부터 시행한다. 다만, 교육전문대학원의 학위과정, 전공, 학생정원 및 교원 배치에 관한 사항은 교육부 승인 및 관계 법령에 따른 절차가 완료된 날부터 시행한다."), red("제2조(교육전문대학원 설치 준비행위) 총장은 이 학칙 시행 전이라도 교육전문대학원 설치를 위하여 학칙 제정, 전공 편성, 교원 배치계획, 의견수렴, 교육과정 편성, 하위규정 정비 등 필요한 준비행위를 할 수 있다."), red("제3조(최초 전임교원 소속 변경에 관한 경과조치) 최초 설치에 따라 교육전문대학원 소속으로 변경되는 전임교원은 관련 분야 전임교원 7명을 기준으로 하되, 전공 적합성, 연구실적, 전공 운영 필요성, 학부 수업 운영 영향, 해당 교원의 의견을 종합하여 정한다."), red("제4조(학부 수업권 보호에 관한 경과조치) 총장은 개원 최초 3년간 매 학년도 학부 필수수업, 심화과정 수업, 교육실습 및 학생지도 운영 현황을 점검하고 수업분담 계획을 교수회에 보고하여야 한다."), red("제5조(다른 규정의 정비) 총장은 시행일부터 6개월 이내에 학사운영규정, 직제 및 사무분장 규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준, 보수·수당 관련 규정을 정비하여야 한다.")]},
    ]
    rendered = []
    for row in rows:
        rendered.append(f"""
        <article class="split-row" id="split-{esc(row['article'])}">
          <div class="split-article">{esc(row['article'])}</div>
          <div class="split-pane original-pane"><h4>원문</h4><div class="law-text">{paragraphs(row['original'])}</div></div>
          <div class="split-pane revised-pane"><h4>수정문</h4><div class="law-text">{paragraphs(row['revised'])}</div></div>
        </article>
        """)
    return f"""
    <div class="split-toolbar"><span>왼쪽: 현행 원문</span><span>오른쪽: 수정문</span><span class="revision">빨간색: 신설·수정 내용</span></div>
    <div class="split-document" aria-label="신구조문 2단 스크롤 대비표">{''.join(rendered)}</div>
    """


def policy_detail_html() -> str:
    lower_rules = [
        ["학사운영규정", "학부 6시간 + 대학원 3시간 기본 수업분담, 책임시간 통합 산정, 보직 감면, 초과강의 제한"],
        ["직제 및 사무분장 규정", "교육전문대학원장, 전공주임, 행정지원, 교무처와 교육전문대학원 간 교원 배치 조정권"],
        ["교육전문대학원 학칙", "학위과정, 전공, 정원, 교육과정, 지도교수, 논문지도, 학위수여, 위원회"],
        ["교원업적평가규정", "박사과정 강의, 논문지도, 논문심사, 현장연계 연구, 전공운영, 학부 겸무 실적 반영"],
        ["교육·연구 및 학생지도 비용 지급 기준", "교육전문대학원 실적과 학부 겸무 실적의 인정 항목, 심사 절차, 중복 실적 방지, 환수 기준"],
        ["보수·수당 관련 규정", "교육전문대학원장, 전공주임교수, 박사과정 운영 책임자 보직수당 또는 책임시간 감면"],
    ]
    return f"""
    <section id="amendment">
      <h2>6. 전주교육대학교 학칙 개정(안)</h2>
      <p class="note">교육전문대학원 설치는 제3조에 명칭만 추가하는 방식으로는 부족합니다. 전임교원 7명 소속 변경, 학부 수업권 보호, 책임시수 통합 인정, 교연비·업적평가 불이익 금지를 하나의 패키지로 설계해야 합니다.</p>
      <div class="grid">
        <article class="panel"><h3>개정 패키지의 결론</h3><p>핵심은 <strong>제4조의2 신설</strong>입니다. 이 조항에서 전임교원의 교육전문대학원 소속 가능성, 총장의 소속 변경·겸무·겸보 권한, 학부 겸무 시 학부 소속 간주, 학부·교육대학원·교육전문대학원 강의시간 통합 산정, 소속 변경을 이유로 한 불이익 금지, 교연비·업적평가 실적 인정 원칙을 모두 담아야 합니다.</p></article>
        <article class="panel"><h3>왜 신분보장형 개정인가</h3><p>교육전문대학원 설치 요건을 충족하려면 관련 분야 전임교원 7명의 소속 이동이 필요합니다. 그러나 소속 변경이 학부 이탈, 책임시수 불이익, 교연비·업적평가 손실로 이해되면 내부 수용성이 낮아집니다. 따라서 학칙 단계에서 권리보장 원칙을 먼저 선언하고 세부 기준은 하위규정으로 위임하는 구조가 안전합니다.</p></article>
      </div>
    </section>
    <section id="comparison">
      <h2>7. 신·구조문 대비표</h2>
      <p class="note">창 화면을 2단으로 분할했습니다. 왼쪽에는 현행 원문을, 오른쪽에는 수정문을 배치했고, 수정문에서 신설·수정된 내용은 빨간색으로 표시했습니다. 아래 문서 영역은 독립적으로 스크롤하여 전체 조문을 검토할 수 있습니다.</p>
      {split_comparison_view()}
    </section>
    <section id="detail">
      <h2>8. 상세 검토와 후속 정비</h2>
      <div class="grid">
        <article class="panel"><h3>교연비·업적평가 설계 원칙</h3><p>학칙은 특정 금액이나 가산점 수치를 직접 보장하지 않고, 소속 변경만을 이유로 한 불이익 금지와 실적 인정 원칙을 선언합니다. 구체적 배점, 심사 항목, 계획서·실적 제출 방식은 교육·연구 및 학생지도 비용 지급 기준과 교원업적평가규정에서 정합니다.</p></article>
        <article class="panel"><h3>7명 소속 이동 운영 모델</h3><p>기본 모델은 “교육전문대학원 소속 + 학부 심화과정 겸무 + 책임시수 통합 인정”입니다. 수업분담은 학부 6시간 + 교육전문대학원 3시간을 기본값으로 두되, 학기별 개설 상황에 따라 유연하게 운영합니다.</p></article>
      </div>
      <h3>하위규정 동시 개정 대상</h3>
      {rows_table(["규정", "필수 정비 내용"], lower_rules)}
      <h3>추진 순서</h3>
      <div class="table-wrap"><table><thead><tr><th>단계</th><th>조치</th><th>산출물</th></tr></thead><tbody>
        <tr><td>1</td><td>제3조·제4조·제4조의2·제47조·부칙 중심 학칙 개정안 확정</td><td>전주교육대학교 학칙 개정안, 신·구조문 대비표</td></tr>
        <tr><td>2</td><td>교육전문대학원 학칙 제정 및 학사운영규정 특례 조항 설계</td><td>전공, 정원, 수업, 지도교수, 학위수여, 책임시수 특례</td></tr>
        <tr><td>3</td><td>교원업적평가규정과 교연비 지급 기준 개정</td><td>박사과정 강의·논문지도·논문심사·전공운영·학부 겸무 실적 인정표</td></tr>
        <tr><td>4</td><td>최초 7명 소속 변경 의견수렴 및 위원회 심의</td><td>교원 배치계획, 수업분담계획, 교수회 보고자료</td></tr>
        <tr><td>5</td><td>개원 후 3년간 학부 수업권 점검</td><td>연도별 학부 필수수업·심화과정·교육실습·학생지도 점검표</td></tr>
      </tbody></table></div>
    </section>
    """


def build_site() -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = get_overview_metrics()
    summary = get_student_summary()
    comp = get_competition_rates()
    plots: list[str] = [plot(create_status_table_chart(GRADUATE_SCHOOL_STATUS), include_plotlyjs="cdn"), plot(create_timeline_chart(get_timeline_data())), plot(major_bar_chart()), plot(create_major_heatmap(get_major_heatmap_data()))]
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
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>전주교대 교육전문대학원 정책연구 대시보드</title><style>
:root {{ --ink:#17212b; --muted:#5d6a78; --line:#d9e1e8; --panel:#f7fafc; --blue:#185c97; --red:#b63f3f; --gold:#b87512; --bg:#fff; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Arial,sans-serif; color:var(--ink); background:var(--bg); line-height:1.6; }} header {{ border-bottom:1px solid var(--line); background:linear-gradient(180deg,#f6fbff 0%,#fff 100%); }} .wrap {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; }} .hero {{ padding:42px 0 28px; }} .eyebrow {{ margin:0 0 10px; color:var(--blue); font-size:14px; font-weight:700; }} h1 {{ margin:0; font-size:clamp(30px,5vw,52px); line-height:1.12; letter-spacing:0; }} h2 {{ margin:0 0 18px; font-size:26px; letter-spacing:0; }} h3 {{ margin:24px 0 12px; font-size:18px; letter-spacing:0; color:#18344f; }} p {{ margin:0 0 12px; }} .lead {{ max-width:900px; margin-top:18px; color:#33475b; font-size:18px; }} nav {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:24px; }} nav a {{ display:inline-flex; min-height:38px; align-items:center; padding:8px 13px; border:1px solid var(--line); border-radius:6px; color:var(--ink); background:#fff; text-decoration:none; font-weight:650; }} main section {{ padding:34px 0; border-bottom:1px solid var(--line); }} .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:22px; }} .metric-card,.panel {{ padding:18px; border:1px solid var(--line); border-radius:8px; background:var(--panel); }} .metric-label {{ color:var(--muted); font-size:14px; font-weight:700; }} .metric-card strong {{ display:block; margin-top:8px; font-size:30px; line-height:1.1; }} .metric-card span {{ display:block; margin-top:8px; color:var(--muted); font-size:13px; }} .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; align-items:start; }} .plot {{ min-height:420px; border:1px solid var(--line); border-radius:8px; padding:10px; background:#fff; overflow:hidden; }} .table-wrap {{ width:100%; overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:#fff; margin:14px 0 20px; }} table {{ width:100%; min-width:760px; border-collapse:collapse; }} th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }} th {{ background:#eef5fb; color:#18344f; font-weight:750; }} .note {{ padding:16px; border-left:4px solid var(--gold); background:#fff8ec; color:#47351d; }} .split-toolbar {{ display:flex; flex-wrap:wrap; gap:10px; margin:16px 0 10px; color:var(--muted); font-size:13px; font-weight:700; }} .split-toolbar span {{ display:inline-flex; min-height:30px; align-items:center; padding:5px 9px; border:1px solid var(--line); border-radius:6px; background:#fff; }} .split-document {{ max-height:78vh; overflow-y:auto; border:1px solid var(--line); border-radius:8px; background:#fff; }} .split-row {{ display:grid; grid-template-columns:84px minmax(0,1fr) minmax(0,1fr); border-bottom:1px solid var(--line); }} .split-article {{ padding:14px 10px; border-right:1px solid var(--line); background:#eef5fb; color:#18344f; font-weight:800; text-align:center; }} .split-pane {{ min-height:180px; padding:14px; }} .original-pane {{ border-right:1px solid var(--line); background:#fbfcfd; }} .split-pane h4 {{ margin:0 0 10px; color:#18344f; font-size:14px; }} .law-text p {{ margin:0 0 10px; font-size:14px; line-height:1.68; }} .revision {{ color:var(--red); font-weight:750; }} .muted {{ color:var(--muted); }} footer {{ padding:28px 0 42px; color:var(--muted); font-size:14px; }} @media (max-width:860px) {{ .metrics,.grid {{ grid-template-columns:1fr; }} .split-document {{ max-height:80vh; overflow-x:auto; }} .split-row {{ min-width:860px; }} }}
</style></head><body>
<header><div class="wrap hero"><p class="eyebrow">GitHub Pages 정적 대시보드</p><h1>전주교대 교육전문대학원 설치 정책연구</h1><p class="lead">Streamlit 서버 없이 열람 가능한 분석 결과 대시보드입니다. 신·구조문 대비표는 2단 분할 화면에서 원문과 수정문을 스크롤하며 비교할 수 있고, 수정된 문구는 빨간색으로 표시됩니다.</p><nav><a href="#overview">현황</a><a href="#majors">전공</a><a href="#students">학생 통계</a><a href="#rationale">설치 당위성</a><a href="#governance">학칙 개정 핵심</a><a href="#amendment">학칙 개정안</a><a href="#comparison">신구조문 대비표</a><a href="#detail">상세 검토</a><a href="#downloads">산출물</a></nav><div class="metrics">{metric("전체 교육대학교", f"{metrics['총_교대수']}개교")}{metric("교육전문대학원 설치", f"{metrics['설치_완료']}개교", "2026년 현재 분석 기준")}{metric("미설치 대학", f"{metrics['미설치']}개교", ", ".join(metrics["미설치_대학"]))}{metric("설치 비율", metrics["설치_비율"], "전국 10개 교대 기준")}</div></div></header>
<main class="wrap"><section id="overview"><h2>1. 설치 현황</h2><p class="note">전국 10개 교육대학교 중 7개교가 교육전문대학원을 설치했으며, 전주교대는 부산교대·춘천교대와 함께 미설치 그룹에 남아 있습니다.</p><div class="grid"><div class="plot">{plots[0]}</div><div class="plot">{plots[1]}</div></div><h3>설치 현황 표</h3>{table(status_table())}</section><section id="majors"><h2>2. 박사전공 비교</h2><div class="grid"><div class="plot">{plots[2]}</div><div class="panel"><h3>전공 설계 시사점</h3><p>신설 대학은 병설형을 채택하면서 교과교육, 교육학, 상담·특수, AI·융합 영역을 조합하고 있습니다. 전주교대는 신청 단계에서는 7개 전공을 포괄하되, 1기 운영은 수요와 지도교수 확보 수준에 따라 4~5개 전공부터 단계 개설하는 방식이 적절합니다.</p>{table(major_summary())}</div></div><div class="plot">{plots[3]}</div></section><section id="students"><h2>3. 학생 통계와 경쟁률</h2><div class="grid"><div class="plot">{plots[4] if len(plots)>4 else '<p class="muted">학생 통계 데이터가 없습니다.</p>'}</div><div class="plot">{plots[5] if len(plots)>5 else '<p class="muted">전주교대 추이 데이터가 없습니다.</p>'}</div></div><div class="plot">{plots[6] if len(plots)>6 else '<p class="muted">경쟁률 데이터가 없습니다.</p>'}</div><h3>재학생 변화율 요약</h3>{table(decline_table(summary))}</section><section id="rationale"><h2>4. 설치 당위성</h2><div class="grid"><article class="panel"><h3>정책 흐름</h3><p>2025년 대구·광주·공주·청주·진주교대가 병설형 교육전문대학원을 설치하면서, 교육대학교의 박사과정 운영은 예외가 아니라 확산 단계로 이동했습니다.</p></article><article class="panel"><h3>전주교대 과제</h3><p>전주교대 교육대학원은 재학생 감소와 낮은 충원율 문제를 동시에 겪고 있습니다. 교육전문대학원은 석사 재교육 중심 구조를 박사 수준의 연구·실천형 전문성 개발 체제로 확장하는 방안입니다.</p></article><article class="panel"><h3>운영 원칙</h3><p>1기 정원은 20~24명, 실제 개설 전공은 4~5개부터 시작하고, 충원율과 지도교수 확보를 확인한 뒤 단계적으로 확대하는 보수적 모델이 적절합니다.</p></article><article class="panel"><h3>교원 확보</h3><p>핵심 리스크는 전임교원 7명 소속 이동입니다. 학부 6시간 + 대학원 3시간의 겸보 모델, 책임시수 통합 산정, 교연비·업적평가 실적 인정이 함께 설계되어야 합니다.</p></article></div></section><section id="governance"><h2>5. 학칙 개정 핵심</h2><p class="note">전주교대 학칙 개정은 단순히 제3조에 교육전문대학원을 추가하는 방식으로는 부족합니다. 전임교원 7명의 신분보장, 학부 수업권 보호, 책임시수 인정, 교연비·업적평가 불이익 금지를 함께 담는 신분보장형 패키지 개정이 필요합니다.</p><div class="grid"><article class="panel"><h3>본칙 핵심 조항</h3><p>제4조의2를 신설해 전임교원의 소속 변경, 겸무·겸보, 학부 겸무 범위에서의 소속 간주, 학부·교육대학원·교육전문대학원 강의시간 통합 산정, 불이익 금지 원칙을 둡니다.</p></article><article class="panel"><h3>하위규정 연동</h3><p>교연비 금액이나 배점을 학칙에 직접 쓰지 않고, 학칙은 실적 인정과 불이익 금지 원칙을 둡니다. 세부 기준은 학사운영규정, 교원업적평가규정, 교육·연구 및 학생지도 비용 지급 기준으로 위임합니다.</p></article></div></section>{policy_detail_html()}<section id="downloads"><h2>9. 산출물</h2><p>정적 대시보드는 <code>scripts/generate_pages_site.py</code>로 생성됩니다. GitHub Actions가 main 브랜치 푸시 시 자동으로 이 페이지를 빌드해 GitHub Pages에 배포합니다.</p><p class="muted">생성 시각: {esc(generated_at)}</p></section></main><footer><div class="wrap"><p>전주교육대학교 교육전문대학원 설치 정책연구 정적 대시보드.</p></div></footer></body></html>"""


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(build_site(), encoding="utf-8")
    print(f"Generated {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
