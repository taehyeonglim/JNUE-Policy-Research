"""Plotly 차트 생성 함수들."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


COLOR_INSTALLED = "#2563EB"
COLOR_NOT_INSTALLED = "#DC2626"
COLOR_JNUE = "#F59E0B"


def create_timeline_chart(timeline_df: pd.DataFrame) -> go.Figure:
    """설치 연도 타임라인 차트."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=timeline_df["설치연도"],
        y=timeline_df["대학수"],
        text=timeline_df["대학목록"],
        textposition="outside",
        marker_color=COLOR_INSTALLED,
        name="신규 설치",
    ))

    fig.add_trace(go.Scatter(
        x=timeline_df["설치연도"],
        y=timeline_df["누적"],
        mode="lines+markers+text",
        text=timeline_df["누적"],
        textposition="top center",
        marker=dict(size=10, color=COLOR_INSTALLED),
        line=dict(dash="dot"),
        name="누적 설치 수",
    ))

    # 전주교대 목표 표시
    fig.add_vline(x=2027, line_dash="dash", line_color=COLOR_JNUE,
                  annotation_text="전주교대 목표 (2027)")

    fig.update_layout(
        title="교육대학교 교육전문대학원 설치 타임라인",
        xaxis_title="연도",
        yaxis_title="대학 수",
        xaxis=dict(dtick=1),
        showlegend=True,
        height=450,
    )
    return fig


def create_status_table_chart(status_df: pd.DataFrame) -> go.Figure:
    """설치 현황 테이블 차트."""
    colors = [
        COLOR_INSTALLED if installed else COLOR_NOT_INSTALLED
        for installed in status_df["교육전문대학원_설치"]
    ]

    has_majors = "박사전공수" in status_df.columns
    header_vals = ["대학교", "소재지", "설치여부", "설치연도", "설치방식"]
    cell_vals = [
        status_df["대학교"],
        status_df["소재지"],
        ["설치" if v else "미설치" for v in status_df["교육전문대학원_설치"]],
        [str(int(v)) if pd.notna(v) else "-" for v in status_df["설치연도"]],
        [v if pd.notna(v) and v != "-" else "-" for v in status_df["설치방식"]],
    ]
    if has_majors:
        header_vals.append("박사전공수")
        cell_vals.append([str(int(v)) if pd.notna(v) else "-" for v in status_df["박사전공수"]])

    num_cols = len(header_vals)

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=header_vals,
            fill_color="#1E3A5F",
            font=dict(color="white", size=13),
            align="center",
        ),
        cells=dict(
            values=cell_vals,
            fill_color=[
                ["#E8F4FD" if c == COLOR_INSTALLED else "#FDE8E8" for c in colors]
            ] * num_cols,
            font=dict(size=12),
            align="center",
            height=30,
        ),
    )])

    fig.update_layout(title="교육대학교 교육전문대학원 설치 현황", height=400)
    return fig


def create_major_heatmap(pivot_df: pd.DataFrame) -> go.Figure:
    """전공 분야별 대학 히트맵."""
    fig = px.imshow(
        pivot_df.values,
        labels=dict(x="대학교", y="전공", color="개설"),
        x=pivot_df.columns.tolist(),
        y=pivot_df.index.tolist(),
        color_continuous_scale=["#F3F4F6", COLOR_INSTALLED],
        aspect="auto",
    )
    fig.update_layout(
        title="전공별 대학 개설 현황 히트맵",
        height=max(400, len(pivot_df) * 35),
    )
    return fig


def create_student_bar_chart(student_df: pd.DataFrame, year: int | None = None) -> go.Figure:
    """대학별 재학생 수 비교 막대 차트."""
    df = student_df.copy()
    if year:
        df = df[df["연도"] == year]

    fig = px.bar(
        df,
        x="대학교",
        y="재학생",
        color="대학교",
        text="재학생",
        title=f"대학별 박사과정 재학생 수 {'(' + str(year) + ')' if year else ''}",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=400)
    return fig


def create_student_trend_chart(student_df: pd.DataFrame) -> go.Figure:
    """연도별 재학생 추이 선 그래프."""
    fig = px.line(
        student_df,
        x="연도",
        y="재학생",
        color="대학교",
        markers=True,
        title="연도별 박사과정 재학생 추이",
    )
    fig.update_layout(height=400)
    return fig


def create_competition_chart(comp_df: pd.DataFrame) -> go.Figure:
    """경쟁률 비교 차트."""
    fig = px.bar(
        comp_df,
        x="대학교",
        y="경쟁률",
        color="연도",
        barmode="group",
        text="경쟁률",
        title="대학별 박사과정 신입생 경쟁률",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400)
    return fig


def create_competition_trend_chart(comp_df: pd.DataFrame) -> go.Figure:
    """연도별 경쟁률 추이."""
    fig = px.line(
        comp_df,
        x="연도",
        y="경쟁률",
        color="대학교",
        markers=True,
        title="연도별 박사과정 경쟁률 추이",
    )
    fig.update_layout(height=400)
    return fig
