"""전공 비교 페이지."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.analyzer import get_major_comparison, get_major_heatmap_data
from src.charts import create_major_heatmap

st.set_page_config(page_title="전공 비교", page_icon="📚", layout="wide")
st.title("📚 교육전문대학원 전공 비교")

majors = get_major_comparison()
universities = majors["대학교"].unique().tolist()

st.subheader("대학별 전공 목록")

selected = st.multiselect("대학 선택", universities, default=universities)
filtered = majors[majors["대학교"].isin(selected)]

for univ in selected:
    univ_data = filtered[filtered["대학교"] == univ]
    with st.expander(f"**{univ}** ({len(univ_data)}개 전공)", expanded=True):
        st.dataframe(
            univ_data[["전공명", "분야"]].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

st.subheader("전공 분야별 히트맵")
st.caption("표준화된 전공명 기준으로 어떤 전공이 여러 대학에 공통으로 개설되어 있는지 보여줍니다.")

heatmap_data = get_major_heatmap_data()
fig = create_major_heatmap(heatmap_data)
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("전공 분야 분포")
field_counts = majors.groupby(["대학교", "분야"]).size().reset_index(name="전공수")
st.dataframe(
    field_counts.pivot(index="대학교", columns="분야", values="전공수").fillna(0).astype(int),
    use_container_width=True,
)
