"""현황 개요 상세 페이지."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.data_loader import GRADUATE_SCHOOL_STATUS
from src.analyzer import get_overview_metrics, get_timeline_data
from src.charts import create_status_table_chart, create_timeline_chart

st.set_page_config(page_title="현황 개요", page_icon="📊", layout="wide")
st.title("📊 교육전문대학원 설치 현황 개요")

metrics = get_overview_metrics()

st.subheader("핵심 지표")
col1, col2, col3 = st.columns(3)
col1.metric("설치 완료", f"{metrics['설치_완료']} / {metrics['총_교대수']}개교")
col2.metric("미설치", f"{metrics['미설치']}개교", delta=f"-{metrics['미설치']}", delta_color="inverse")
col3.metric("설치 비율", metrics["설치_비율"])

st.divider()

st.subheader("전체 현황 테이블")
st.dataframe(
    GRADUATE_SCHOOL_STATUS.style.applymap(
        lambda v: "background-color: #DBEAFE" if v is True
        else ("background-color: #FEE2E2" if v is False else ""),
        subset=["교육전문대학원_설치"],
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

st.subheader("설치 연도 타임라인")
timeline = get_timeline_data()
fig = create_timeline_chart(timeline)
st.plotly_chart(fig, use_container_width=True)

st.subheader("설치 방식 분포")
method_counts = GRADUATE_SCHOOL_STATUS.dropna(subset=["설치방식"])["설치방식"].value_counts()
col1, col2 = st.columns(2)
for method, count in method_counts.items():
    col1.metric(f"{method} 방식", f"{count}개교")

st.caption("※ 전환: 기존 교육대학원을 교육전문대학원으로 전환 / 병설: 교육대학원과 교육전문대학원을 병행 운영")
