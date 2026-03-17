"""경쟁률 분석 페이지 — KESS 실제 데이터 기반."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.express as px
from src.analyzer import get_competition_rates

st.set_page_config(page_title="경쟁률 분석", page_icon="📈", layout="wide")
st.title("📈 교육대학원 경쟁률 분석")
st.caption("경쟁률 = 지원자 수 / 입학정원")

comp_df = get_competition_rates()

if comp_df.empty:
    st.warning("경쟁률 데이터가 없습니다.")
    st.stop()

# 대학원유형 필터
grad_types = sorted(comp_df["대학원유형"].unique())
selected_type = st.selectbox("대학원 유형", ["전체"] + grad_types)
if selected_type != "전체":
    comp_df = comp_df[comp_df["대학원유형"] == selected_type]

years = sorted(comp_df["연도"].unique())

st.divider()

# --- 연도별 경쟁률 비교 ---
st.subheader("대학별 경쟁률 비교")
selected_year = st.select_slider("연도 선택", options=years, value=years[-1])
year_data = comp_df[comp_df["연도"] == selected_year].sort_values("경쟁률", ascending=False)

fig = px.bar(
    year_data, x="대학교", y="경쟁률", color="대학원유형",
    text="경쟁률",
    title=f"대학별 경쟁률 ({selected_year})",
)
fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
fig.update_layout(height=450)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 추이 ---
st.subheader("연도별 경쟁률 추이")
fig2 = px.line(
    comp_df, x="연도", y="경쟁률", color="대학교", markers=True,
    symbol="대학원유형",
    title="연도별 경쟁률 추이",
)
fig2.update_layout(height=450)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- 입학정원 대비 지원/입학 ---
st.subheader("입학정원 vs 지원자 vs 입학자")
year_detail = comp_df[comp_df["연도"] == selected_year].copy()
fig3 = px.bar(
    year_detail.melt(
        id_vars=["대학교", "대학원유형"],
        value_vars=["입학정원_전체", "지원자_전체", "입학자_전체"],
        var_name="구분", value_name="인원",
    ),
    x="대학교", y="인원", color="구분", barmode="group",
    title=f"입학정원 vs 지원자 vs 입학자 ({selected_year})",
)
fig3.update_layout(height=450)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

st.subheader("상세 데이터")
st.dataframe(comp_df.sort_values(["연도", "대학교"]), use_container_width=True, hide_index=True)
