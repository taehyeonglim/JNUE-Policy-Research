"""학생 통계 페이지 — KESS 실제 데이터 기반."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from src.analyzer import get_student_summary

st.set_page_config(page_title="학생 통계", page_icon="👨‍🎓", layout="wide")
st.title("👨‍🎓 교육대학교 대학원 학생 통계")

summary = get_student_summary()

if summary.empty:
    st.error("KESS 데이터가 없습니다. data/kess/ 폴더에 엑셀 파일을 넣어주세요.")
    st.stop()

# 대학원유형 필터
grad_types = sorted(summary["대학원유형"].unique())
selected_type = st.selectbox("대학원 유형", ["전체"] + grad_types)
if selected_type != "전체":
    summary = summary[summary["대학원유형"] == selected_type]

years = sorted(summary["연도"].unique())

st.divider()

# --- 재학생 비교 ---
st.subheader("대학별 재학생 수 비교")
selected_year = st.select_slider("연도 선택", options=years, value=years[-1])
year_data = summary[summary["연도"] == selected_year].sort_values("재학생_전체", ascending=False)

fig = px.bar(
    year_data, x="대학교", y="재학생_전체", color="대학원유형",
    text="재학생_전체",
    title=f"대학별 대학원 재학생 수 ({selected_year})",
    labels={"재학생_전체": "재학생 수", "대학원유형": "유형"},
)
fig.update_traces(textposition="outside")
fig.update_layout(height=450)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 연도별 추이 ---
st.subheader("연도별 재학생 추이")
# 교대별로 교육대학원 + 교육전문대학원 합산
trend = summary.groupby(["연도", "대학교"])["재학생_전체"].sum().reset_index()

fig2 = px.line(
    trend, x="연도", y="재학생_전체", color="대학교", markers=True,
    title="연도별 대학원 재학생 추이 (교육대학원+교육전문대학원 합산)",
    labels={"재학생_전체": "재학생 수"},
)
fig2.update_layout(height=450)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- 석사/박사 비율 ---
st.subheader("석사/박사 재학생 비율")
latest = summary[summary["연도"] == years[-1]]
ratio_data = latest.groupby("대학교").agg(
    석사=("재학생_석사", "sum"),
    박사=("재학생_박사", "sum"),
).reset_index()
ratio_data["합계"] = ratio_data["석사"] + ratio_data["박사"]
ratio_data = ratio_data[ratio_data["합계"] > 0].sort_values("합계", ascending=False)

fig3 = go.Figure()
fig3.add_trace(go.Bar(name="석사", x=ratio_data["대학교"], y=ratio_data["석사"], marker_color="#2563EB"))
fig3.add_trace(go.Bar(name="박사", x=ratio_data["대학교"], y=ratio_data["박사"], marker_color="#DC2626"))
fig3.update_layout(
    barmode="stack", title=f"석사/박사 재학생 비율 ({years[-1]})",
    height=400,
)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# --- 전주교대 하이라이트 ---
st.subheader("전주교대 교육대학원 추이")
jnue = summary[summary["대학교"] == "전주교대"].sort_values("연도")
if not jnue.empty:
    col1, col2, col3 = st.columns(3)
    latest_jnue = jnue.iloc[-1]
    first_jnue = jnue.iloc[0]
    change = int(latest_jnue["재학생_전체"] - first_jnue["재학생_전체"])
    col1.metric("최신 재학생", f"{int(latest_jnue['재학생_전체'])}명")
    col2.metric(f"{int(first_jnue['연도'])}년 대비 변화", f"{change}명",
                delta=f"{change}명", delta_color="normal")
    col3.metric("기간", f"{int(first_jnue['연도'])}~{int(latest_jnue['연도'])}")

    st.dataframe(jnue[["연도", "대학원유형", "재학생_전체", "재학생_석사", "재학생_박사",
                        "입학자_전체", "졸업자_전체"]],
                 use_container_width=True, hide_index=True)

st.divider()

# --- 상세 데이터 ---
st.subheader("전체 상세 데이터")
st.dataframe(summary.sort_values(["연도", "대학교"]), use_container_width=True, hide_index=True)
