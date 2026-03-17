"""전주교대 교육전문대학원 현황 비교 대시보드 — 메인 페이지."""

import sys
import pathlib

# 프로젝트 루트를 sys.path에 추가
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="교육전문대학원 현황 비교",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎓 교육대학교 교육전문대학원 현황 비교 대시보드")
st.caption("전주교육대학교 교육전문대학원(박사과정) 설치를 위한 정책연구 지원 도구")

st.divider()

from src.analyzer import get_overview_metrics
from src.data_loader import GRADUATE_SCHOOL_STATUS
from src.charts import create_status_table_chart, create_timeline_chart
from src.analyzer import get_timeline_data

metrics = get_overview_metrics()

col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 교육대학교", f"{metrics['총_교대수']}개교")
col2.metric("교육전문대학원 설치", f"{metrics['설치_완료']}개교")
col3.metric("미설치", f"{metrics['미설치']}개교")
col4.metric("설치 비율", metrics["설치_비율"])

st.warning(f"**미설치 대학:** {', '.join(metrics['미설치_대학'])}")

st.divider()

st.subheader("설치 현황 테이블")
fig_table = create_status_table_chart(GRADUATE_SCHOOL_STATUS)
st.plotly_chart(fig_table, use_container_width=True)

st.subheader("설치 타임라인")
timeline = get_timeline_data()
fig_timeline = create_timeline_chart(timeline)
st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

st.info("""
**사용 안내**
- 왼쪽 사이드바에서 세부 분석 페이지로 이동할 수 있습니다.
- 현재 샘플 데이터로 운영 중이며, KESS 데이터 투입 시 자동으로 갱신됩니다.
- `data/kess/` 폴더에 KESS 엑셀 파일을 넣어주세요.
""")
