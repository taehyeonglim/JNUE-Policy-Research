"""전주교대 교육전문대학원 설치 당위성 — 데이터 기반 자동 생성."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.data_loader import GRADUATE_SCHOOL_STATUS, MAJORS_DATA, get_sangbangi
from src.analyzer import get_student_summary, get_competition_rates

st.set_page_config(page_title="설치 당위성", page_icon="📋", layout="wide")
st.title("📋 전주교대 교육전문대학원 설치 당위성")
st.caption("KESS 교육통계 데이터 기반 — 데이터 갱신 시 자동 업데이트")

summary = get_student_summary()
comp = get_competition_rates()
status = GRADUATE_SCHOOL_STATUS

# ---------------------------------------------------------------------------
# 1. 설치 현황: 이미 표준이 되었다
# ---------------------------------------------------------------------------
st.header("1. 교육전문대학원은 이미 '표준'이 되었다")

total = len(status)
installed = int(status["교육전문대학원_설치"].sum())
not_installed = total - installed
pct = installed / total * 100
미설치_list = status.loc[~status["교육전문대학원_설치"], "대학교"].tolist()

col1, col2, col3 = st.columns(3)
col1.metric("전체 교육대학교", f"{total}개교")
col2.metric("설치 완료", f"{installed}개교 ({pct:.0f}%)")
col3.metric("미설치", f"{not_installed}개교")

st.warning(f"**미설치 대학:** {', '.join(미설치_list)}")

# 설치 연도 타임라인
설치df = status.dropna(subset=["설치연도"]).copy()
설치df["설치연도"] = 설치df["설치연도"].astype(int)
timeline = 설치df.groupby("설치연도").agg(
    대학수=("대학교", "count"),
    대학목록=("대학교", lambda x: ", ".join(x)),
).reset_index()
timeline["누적"] = timeline["대학수"].cumsum()

fig_tl = go.Figure()
fig_tl.add_trace(go.Bar(x=timeline["설치연도"], y=timeline["대학수"],
                        text=timeline["대학목록"], textposition="outside",
                        marker_color="#2563EB", name="신규 설치"))
fig_tl.add_trace(go.Scatter(x=timeline["설치연도"], y=timeline["누적"],
                            mode="lines+markers+text", text=timeline["누적"],
                            textposition="top center", name="누적",
                            marker=dict(size=10, color="#2563EB"), line=dict(dash="dot")))
fig_tl.add_vline(x=2027, line_dash="dash", line_color="#F59E0B",
                 annotation_text="전주교대 목표 (2027)")
fig_tl.update_layout(title="교육전문대학원 설치 타임라인", height=400, xaxis=dict(dtick=1))
st.plotly_chart(fig_tl, use_container_width=True)

st.markdown(f"""
> **{total}개 교육대학교 중 {installed}개교({pct:.0f}%)가 이미 설치**를 완료했습니다.
> 특히 2024~2025년에 집중적으로 신설되어, 교육전문대학원 설치가 교육대학교의 표준적 발전 경로임을 보여줍니다.
""")

st.divider()

# ---------------------------------------------------------------------------
# 2. 전주교대 교육대학원 위기
# ---------------------------------------------------------------------------
st.header("2. 전주교대 교육대학원: 정원 미달의 지속")

if not summary.empty:
    jnue = summary[summary["대학교"] == "전주교대"].sort_values("연도")

    if not jnue.empty:
        # 핵심 지표
        first_year = jnue.iloc[0]
        latest_year = jnue.iloc[-1]
        재학생_변화 = int(latest_year["재학생_전체"] - first_year["재학생_전체"])
        변화율 = (재학생_변화 / first_year["재학생_전체"] * 100) if first_year["재학생_전체"] > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric(f"재학생 ({int(first_year['연도'])})", f"{int(first_year['재학생_전체'])}명")
        col2.metric(f"재학생 ({int(latest_year['연도'])})", f"{int(latest_year['재학생_전체'])}명",
                    delta=f"{재학생_변화}명 ({변화율:.0f}%)")
        col3.metric("입학정원", f"{int(latest_year['입학정원_전체'])}명")

        # 경쟁률 계산
        jnue_comp = jnue[jnue["입학정원_전체"] > 0].copy()
        jnue_comp["경쟁률"] = (jnue_comp["지원자_전체"] / jnue_comp["입학정원_전체"]).round(2)

        # 테이블
        display = jnue_comp[["연도", "재학생_전체", "입학자_전체", "지원자_전체", "입학정원_전체", "경쟁률"]].copy()
        display.columns = ["연도", "재학생", "입학자", "지원자", "입학정원", "경쟁률"]
        display["연도"] = display["연도"].astype(int)
        display[["재학생", "입학자", "지원자", "입학정원"]] = display[["재학생", "입학자", "지원자", "입학정원"]].astype(int)
        st.dataframe(display, use_container_width=True, hide_index=True)

        # 추이 차트
        fig_jnue = go.Figure()
        fig_jnue.add_trace(go.Scatter(x=jnue["연도"], y=jnue["재학생_전체"],
                                      mode="lines+markers+text", text=jnue["재학생_전체"].astype(int),
                                      textposition="top center", name="재학생",
                                      line=dict(color="#DC2626", width=3)))
        fig_jnue.add_trace(go.Scatter(x=jnue["연도"], y=jnue["지원자_전체"],
                                      mode="lines+markers", name="지원자",
                                      line=dict(color="#F59E0B", dash="dot")))
        fig_jnue.add_hline(y=jnue["입학정원_전체"].iloc[-1], line_dash="dash",
                           line_color="#6B7280", annotation_text="입학정원")
        fig_jnue.update_layout(title="전주교대 교육대학원 추이", height=400)
        st.plotly_chart(fig_jnue, use_container_width=True)

        avg_경쟁률 = jnue_comp["경쟁률"].mean()
        st.error(f"""
        **재학생 {abs(변화율):.0f}% 감소** ({int(first_year['재학생_전체'])}→{int(latest_year['재학생_전체'])}명, {int(first_year['연도'])}~{int(latest_year['연도'])}),
        **평균 경쟁률 {avg_경쟁률:.2f}** — 석사과정만으로는 수요를 유지하기 어려운 상태입니다.
        """)

st.divider()

# ---------------------------------------------------------------------------
# 3. 타 교대 비교: 전주교대의 위치
# ---------------------------------------------------------------------------
st.header("3. 타 교대 대비 전주교대의 위치")

if not summary.empty:
    latest_yr = summary["연도"].max()
    latest_all = summary[summary["연도"] == latest_yr].copy()
    # 교대별 합산 (교육대학원+교육전문대학원)
    합산 = latest_all.groupby("대학교").agg(
        재학생=("재학생_전체", "sum"),
        입학자=("입학자_전체", "sum"),
        지원자=("지원자_전체", "sum"),
    ).reset_index().sort_values("재학생", ascending=False)

    colors = ["#DC2626" if u == "전주교대" else "#2563EB" for u in 합산["대학교"]]

    fig_comp = go.Figure(go.Bar(
        x=합산["대학교"], y=합산["재학생"], text=합산["재학생"],
        textposition="outside", marker_color=colors,
    ))
    fig_comp.update_layout(title=f"교대별 대학원 재학생 수 ({latest_yr}) — 전주교대 빨간색 표시",
                           height=450)
    st.plotly_chart(fig_comp, use_container_width=True)

    전주_순위 = list(합산["대학교"]).index("전주교대") + 1 if "전주교대" in 합산["대학교"].values else None
    if 전주_순위:
        st.warning(f"전주교대는 {len(합산)}개 교대 중 재학생 수 **{전주_순위}위** (최하위권)입니다.")

st.divider()

# ---------------------------------------------------------------------------
# 4. 신설 대학의 수요 검증
# ---------------------------------------------------------------------------
st.header("4. 교육전문대학원 신설 대학의 수요 검증")

if not summary.empty:
    # 교육전문대학원만 필터
    전문대학원 = summary[summary["대학원유형"] == "교육전문대학원"].copy()
    # 2024~2025년 신설 대학 (경인/서울 제외)
    신설 = 전문대학원[~전문대학원["대학교"].isin(["경인교대", "서울교대"])]

    if not 신설.empty:
        신설_display = 신설[["연도", "대학교", "입학정원_전체", "지원자_전체", "입학자_전체", "재학생_전체"]].copy()
        신설_display.columns = ["연도", "대학교", "입학정원", "지원자", "입학자", "재학생"]
        신설_display["경쟁률"] = (신설_display["지원자"] / 신설_display["입학정원"]).round(2)
        신설_display[["연도", "입학정원", "지원자", "입학자", "재학생"]] = 신설_display[["연도", "입학정원", "지원자", "입학자", "재학생"]].astype(int)
        st.dataframe(신설_display.sort_values(["연도", "대학교"]), use_container_width=True, hide_index=True)

        max_row = 신설_display.loc[신설_display["경쟁률"].idxmax()]
        st.success(f"""
        **{max_row['대학교']}**는 첫 해 경쟁률 **{max_row['경쟁률']:.2f}:1**을 기록했습니다.
        현직 교사들의 박사학위 수요가 명확히 존재합니다.
        """)
    else:
        st.info("신설 교육전문대학원 데이터가 아직 없습니다.")

st.divider()

# ---------------------------------------------------------------------------
# 5. 선발 전환 대학 성공 사례
# ---------------------------------------------------------------------------
st.header("5. 선발 전환 대학의 안정적 운영 (12년 경과)")

if not summary.empty:
    전환 = 전문대학원[전문대학원["대학교"].isin(["경인교대", "서울교대"])]
    latest_전환 = 전환[전환["연도"] == 전환["연도"].max()]

    if not latest_전환.empty:
        for _, row in latest_전환.iterrows():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(f"{row['대학교']}", f"재학생 {int(row['재학생_전체'])}명")
            col2.metric("석사", f"{int(row['재학생_석사'])}명")
            col3.metric("박사", f"{int(row['재학생_박사'])}명")
            col4.metric("박사학과수", f"{int(row['학과수_박사'])}개")

        st.markdown("""
        > 2013년 전환 후 12년이 경과한 경인교대·서울교대는 **석사+박사 합산 1,100~1,300명 규모**로
        > 안정적으로 운영되고 있으며, 교육전문대학원 모델의 장기적 지속 가능성을 입증합니다.
        """)

st.divider()

# ---------------------------------------------------------------------------
# 6. 지역적 필요성
# ---------------------------------------------------------------------------
st.header("6. 전북 지역의 구조적 필요성")

st.markdown("""
현재 교육전문대학원이 **미설치된 3개 교대의 소재지**:

| 대학교 | 소재지 | 가장 가까운 교육전문대학원 |
|--------|--------|--------------------------|
| **전주교대** | **전북** | **광주교대(광주) / 공주교대(충남)** |
| 부산교대 | 부산 | 진주교대(경남) |
| 춘천교대 | 강원 | 청주교대(충북) |

전북 지역 현직 초등교사가 박사과정을 이수하려면 **타 지역으로 이동**해야 하며,
이는 전북 지역 교육 전문인력의 유출을 초래합니다.

전주교대에 교육전문대학원이 설치되면:
- 전북 지역 현직 교사의 **재직 중 박사학위 취득 경로** 마련
- 지역 교육 전문인력의 **타 지역 유출 방지**
- 전북 교육 생태계의 **자생력 확보**
""")

st.divider()

# ---------------------------------------------------------------------------
# 7. 결론
# ---------------------------------------------------------------------------
st.header("7. 결론")

if not summary.empty and not jnue.empty:
    st.error(f"""
    ### 교육전문대학원 설치는 선택이 아닌 생존의 문제

    - **{total}개 교대 중 {installed}개교({pct:.0f}%)**가 이미 설치 완료
    - 전주교대 교육대학원 재학생 **{abs(변화율):.0f}% 감소**, 경쟁률 **{avg_경쟁률:.2f}**
    - 신설 대학의 높은 경쟁률로 **박사과정 수요 검증 완료**
    - 전북 지역 교육 전문인력 양성을 위한 **구조적 필요성**

    박사과정 신설을 통해 **(1) 대학원 수요 활성화**, **(2) 전북 지역 교육 전문인력 양성**,
    **(3) 대학 경쟁력 확보**를 동시에 달성할 수 있습니다.
    """)

st.divider()
st.caption("※ 본 분석은 KESS 교육통계 데이터베이스(kess.kedi.re.kr) 데이터를 기반으로 자동 생성되었습니다. 데이터 갱신 시 내용이 자동으로 업데이트됩니다.")
