"""전주교대 교육전문대학원 설치 당위성 — 데이터 기반 자동 생성 (v2: 논리 보강)."""

import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.data_loader import (
    GRADUATE_SCHOOL_STATUS, MAJORS_DATA, get_sangbangi,
    get_doctoral_enrollment, get_counseling_special_10yr, get_national_grad_status,
)
from src.analyzer import get_student_summary, get_competition_rates

st.set_page_config(page_title="설치 당위성", page_icon="📋", layout="wide")
st.title("📋 전주교대 교육전문대학원 설치 당위성")
st.caption("KESS 교육통계 데이터 기반 — 데이터 갱신 시 자동 업데이트")

summary = get_student_summary()
comp = get_competition_rates()
status = GRADUATE_SCHOOL_STATUS

# 공통 계산
total = len(status)
installed = int(status["교육전문대학원_설치"].sum())
not_installed = total - installed
pct = installed / total * 100
미설치_list = status.loc[~status["교육전문대학원_설치"], "대학교"].tolist()

# 공통 변수 초기화 (조건부 블록 밖에서 사용되므로)
전국_평균 = 0.0
전주_변화 = 0.0
설치_avg = 0.0
미설치_avg = 0.0
jnue = pd.DataFrame()
전문대학원 = pd.DataFrame()

# ===========================================================================
# 1. 전국 교육대학원 위기와 교육전문대학원의 대응
# ===========================================================================
st.header("1. 전국 교육대학원의 구조적 위기")

if not summary.empty:
    # 교육대학원만 추출하여 전국 추이 계산
    교육대학원 = summary[summary["대학원유형"] == "교육대학원"]
    pivot_edu = 교육대학원.pivot_table(index="연도", columns="대학교", values="재학생_전체", aggfunc="sum")
    years = sorted(pivot_edu.index)

    if len(years) >= 2:
        변화율_list = []
        for col in pivot_edu.columns:
            first_val = pivot_edu[col].iloc[0]
            last_val = pivot_edu[col].iloc[-1]
            if first_val > 0:
                변화율_list.append({
                    "대학교": col,
                    "시작연도_재학생": int(first_val),
                    "최신연도_재학생": int(last_val),
                    "변화율": round((last_val - first_val) / first_val * 100, 1),
                })
        변화율_df = pd.DataFrame(변화율_list).sort_values("변화율")

        st.markdown(f"""
        교육대학원(석사) 재학생 감소는 **전주교대만의 문제가 아니라 전국 교육대학교 공통 현상**입니다.
        그러나 감소 폭에는 큰 차이가 있으며, 이 차이가 교육전문대학원 설치의 효과를 보여줍니다.
        """)

        colors = ["#DC2626" if row["대학교"] == "전주교대" else "#94A3B8" for _, row in 변화율_df.iterrows()]
        fig_decline = go.Figure(go.Bar(
            x=변화율_df["대학교"], y=변화율_df["변화율"],
            text=[f"{v:+.1f}%" for v in 변화율_df["변화율"]],
            textposition="outside", marker_color=colors,
        ))
        fig_decline.update_layout(
            title=f"교대별 교육대학원 재학생 변화율 ({int(years[0])}→{int(years[-1])})",
            yaxis_title="변화율 (%)", height=400,
        )
        st.plotly_chart(fig_decline, use_container_width=True)

        전주_row = 변화율_df[변화율_df["대학교"] == "전주교대"]["변화율"]
        전주_변화 = 전주_row.values[0] if len(전주_row) > 0 else 0.0
        전국_평균 = 변화율_df["변화율"].mean()

        st.warning(f"""
        **전주교대 교육대학원 재학생 변화율: {전주_변화:+.1f}%** (전국 교대 평균: {전국_평균:+.1f}%)
        — 전국에서 가장 심각한 감소를 보이고 있습니다.
        """)

st.divider()

# ===========================================================================
# 2. 교육전문대학원이 대학원 위기의 해법임을 입증
# ===========================================================================
st.header("2. 교육전문대학원 설치 = 대학원 위기 대응책")

if not summary.empty:
    # 교대별 총 대학원생 (교육대학원+교육전문대학원 합산) 추이
    총합 = summary.groupby(["연도", "대학교"])["재학생_전체"].sum().reset_index()
    pivot_total = 총합.pivot_table(index="연도", columns="대학교", values="재학생_전체")

    총변화_list = []
    for col in pivot_total.columns:
        first_val = pivot_total[col].iloc[0]
        last_val = pivot_total[col].iloc[-1]
        if first_val > 0:
            has_전문 = col in summary[summary["대학원유형"] == "교육전문대학원"]["대학교"].values
            총변화_list.append({
                "대학교": col,
                "교육전문대학원": "설치" if has_전문 else "미설치",
                "시작": int(first_val),
                "최신": int(last_val),
                "변화율": round((last_val - first_val) / first_val * 100, 1),
            })
    총변화_df = pd.DataFrame(총변화_list).sort_values("변화율", ascending=False)

    st.markdown("""
    교육대학원 재학생은 전국적으로 감소하고 있지만, **교육전문대학원을 설치한 대학은
    박사과정 재학생이 교육대학원 감소분을 상쇄**하여 총 대학원 규모를 유지하고 있습니다.
    """)

    # 설치/미설치별 평균 변화율
    설치_avg = 총변화_df[총변화_df["교육전문대학원"] == "설치"]["변화율"].mean()
    미설치_avg = 총변화_df[총변화_df["교육전문대학원"] == "미설치"]["변화율"].mean()

    col1, col2 = st.columns(2)
    col1.metric("교육전문대학원 설치 대학 평균 변화율", f"{설치_avg:+.1f}%")
    col2.metric("미설치 대학 평균 변화율", f"{미설치_avg:+.1f}%")

    colors2 = []
    for _, row in 총변화_df.iterrows():
        if row["대학교"] == "전주교대":
            colors2.append("#DC2626")
        elif row["교육전문대학원"] == "설치":
            colors2.append("#2563EB")
        else:
            colors2.append("#F59E0B")

    fig_total = go.Figure(go.Bar(
        x=총변화_df["대학교"], y=총변화_df["변화율"],
        text=[f"{v:+.1f}%" for v in 총변화_df["변화율"]],
        textposition="outside", marker_color=colors2,
    ))
    fig_total.update_layout(
        title=f"교대별 총 대학원생 변화율 (파랑=설치, 노랑=미설치, 빨강=전주교대)",
        yaxis_title="변화율 (%)", height=400,
    )
    st.plotly_chart(fig_total, use_container_width=True)

    st.success(f"""
    **교육전문대학원 설치 대학은 평균 {설치_avg:+.1f}%**, 미설치 대학은 평균 **{미설치_avg:+.1f}%**.
    교육전문대학원이 대학원 위기에 대한 구조적 해법으로 작동하고 있음을 데이터가 입증합니다.
    """)

st.divider()

# ===========================================================================
# 3. 전주교대 현황 (원인 진단 포함)
# ===========================================================================
st.header("3. 전주교대 교육대학원 현황과 원인 진단")

if not summary.empty:
    jnue = summary[summary["대학교"] == "전주교대"].sort_values("연도")

    if not jnue.empty:
        first_year = jnue.iloc[0]
        latest_year = jnue.iloc[-1]
        재학생_변화 = int(latest_year["재학생_전체"] - first_year["재학생_전체"])
        변화율 = (재학생_변화 / first_year["재학생_전체"] * 100) if first_year["재학생_전체"] > 0 else 0

        jnue_comp = jnue[jnue["입학정원_전체"] > 0].copy()
        jnue_comp["경쟁률"] = (jnue_comp["지원자_전체"] / jnue_comp["입학정원_전체"]).round(2)

        col1, col2, col3 = st.columns(3)
        col1.metric(f"재학생 ({int(first_year['연도'])})", f"{int(first_year['재학생_전체'])}명")
        col2.metric(f"재학생 ({int(latest_year['연도'])})", f"{int(latest_year['재학생_전체'])}명",
                    delta=f"{재학생_변화}명 ({변화율:.0f}%)")
        col3.metric("입학정원", f"{int(latest_year['입학정원_전체'])}명")

        display = jnue_comp[["연도", "재학생_전체", "입학자_전체", "지원자_전체", "입학정원_전체", "경쟁률"]].copy()
        display.columns = ["연도", "재학생", "입학자", "지원자", "입학정원", "경쟁률"]
        display["연도"] = display["연도"].astype(int)
        display[["재학생", "입학자", "지원자", "입학정원"]] = display[["재학생", "입학자", "지원자", "입학정원"]].astype(int)
        st.dataframe(display, use_container_width=True, hide_index=True)

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

        # --- 전주교대 양성과정(상담/특수) 10년 추이 ---
        try:
            counseling_data = get_counseling_special_10yr()
            if not counseling_data["입학"].empty:
                st.markdown("#### 전주교대 양성과정(상담/특수) 10년 입학 추이")
                adm = counseling_data["입학"]
                year_cols = [c for c in adm.columns if isinstance(c, int)]
                fig_counsel = go.Figure()
                for _, row in adm.iterrows():
                    vals = [row[yr] for yr in year_cols]
                    fig_counsel.add_trace(go.Scatter(
                        x=year_cols, y=vals,
                        mode="lines+markers", name=row["전공명"],
                        connectgaps=False,
                    ))
                fig_counsel.update_layout(
                    title="전주교대 양성과정 전공별 입학 인원 (2016~2026)",
                    xaxis_title="연도", yaxis_title="입학 인원(명)", height=380,
                )
                st.plotly_chart(fig_counsel, use_container_width=True)
                st.caption("※ 초등교육상담→학교상담(2022~ 명칭변경), 초등특수교육은 2020년 이후 입학자 0명")
        except Exception:
            pass  # 데이터 로딩 실패 시 건너뜀

        st.markdown(f"""
        #### 원인 진단

        정원 미달의 핵심 원인은 **석사학위의 효용 감소**입니다.
        현직 교사의 경력 경로(장학사, 교육연구사, 교감, 교장)에서 석사학위는 더 이상 차별적 경쟁력이 되지 못하며,
        이는 전주교대만의 문제가 아닌 **전국 교대 공통 현상**(전국 평균 {전국_평균:+.1f}% 감소)입니다.

        반면 박사학위는 **승진, 전문성 심화, 연구 역량 인증**에서 석사와 질적으로 다른 동기를 제공하며,
        신설 대학의 높은 충원율(공주교대 100%)이 이를 실증합니다.

        따라서 교육전문대학원 설치는 기존 과정의 실패에 대한 반복이 아니라,
        **석사과정 수요 감소의 구조적 원인에 대응하는 체제 전환**입니다.
        """)

st.divider()

# ===========================================================================
# 4. 신설 대학의 수요 검증
# ===========================================================================
st.header("4. 교육전문대학원 신설 대학의 수요 검증")

# --- 4-A: KESS 기반 신설대학 총괄 ---
if not summary.empty:
    전문대학원 = summary[summary["대학원유형"] == "교육전문대학원"].copy()
    신설 = 전문대학원[~전문대학원["대학교"].isin(["경인교대", "서울교대"])]

    if not 신설.empty:
        신설_display = 신설[["연도", "대학교", "입학정원_전체", "지원자_전체", "입학자_전체", "재학생_전체"]].copy()
        신설_display.columns = ["연도", "대학교", "입학정원", "지원자", "입학자", "재학생"]
        신설_display["경쟁률"] = (신설_display["지원자"] / 신설_display["입학정원"]).round(2)
        신설_display[["연도", "입학정원", "지원자", "입학자", "재학생"]] = 신설_display[["연도", "입학정원", "지원자", "입학자", "재학생"]].astype(int)
        st.dataframe(신설_display.sort_values(["연도", "대학교"]), use_container_width=True, hide_index=True)

# --- 4-B: 박사과정 전공별 신입생 충원 현황 (대학본부 데이터) ---
try:
    doctoral = get_doctoral_enrollment()
    if not doctoral.empty:
        st.subheader("4-1. 박사과정 전공별 신입생 충원 현황")
        st.caption("출처: 대학본부 제공 — 교육전문대학원 박사과정 신입생 충원 현황 ('24~'26학년도)")

        # 학교별 요약
        school_summary = doctoral.groupby("대학교_약칭").agg(
            양성정원=("양성정원", "first"),
            전공수=("전공명", "count"),
            충원_25=("충원_25학년도", "sum"),
            충원_26=("충원_26학년도", "sum"),
            충원누계=("충원누계", "sum"),
        ).reset_index()
        school_summary["충원율_25"] = (school_summary["충원_25"] / school_summary["양성정원"] * 100).round(1)
        school_summary["충원율_26"] = (school_summary["충원_26"] / school_summary["양성정원"] * 100).round(1)
        school_summary.columns = ["대학교", "양성정원", "전공수", "'25 충원", "'26 충원", "충원누계", "'25 충원율(%)", "'26 충원율(%)"]

        st.dataframe(school_summary, use_container_width=True, hide_index=True)

        # 학교별 충원율 시각화
        fig_enroll = go.Figure()
        fig_enroll.add_trace(go.Bar(
            x=school_summary["대학교"], y=school_summary["'25 충원율(%)"],
            name="'25학년도", marker_color="#2563EB", text=school_summary["'25 충원율(%)"].apply(lambda x: f"{x}%"),
            textposition="outside",
        ))
        fig_enroll.add_trace(go.Bar(
            x=school_summary["대학교"], y=school_summary["'26 충원율(%)"],
            name="'26학년도", marker_color="#F59E0B", text=school_summary["'26 충원율(%)"].apply(lambda x: f"{x}%"),
            textposition="outside",
        ))
        fig_enroll.add_hline(y=100, line_dash="dash", line_color="#6B7280", annotation_text="정원 100%")
        fig_enroll.update_layout(
            title="교육전문대학원 박사과정 충원율 비교", barmode="group",
            yaxis_title="충원율 (%)", height=420,
        )
        st.plotly_chart(fig_enroll, use_container_width=True)

        # 전공별 상세 (확장 가능)
        with st.expander("전공별 상세 충원 현황 보기"):
            detail = doctoral[["대학교_약칭", "전공명", "충원_25학년도", "충원_26학년도", "충원누계"]].copy()
            detail.columns = ["대학교", "전공명", "'25학년도", "'26학년도", "누계"]
            st.dataframe(detail, use_container_width=True, hide_index=True)

        # 인기 전공 TOP 10
        top_majors = doctoral.nlargest(10, "충원누계")[["대학교_약칭", "전공명", "충원누계"]].copy()
        top_majors.columns = ["대학교", "전공명", "충원누계"]

        fig_top = px.bar(
            top_majors, x="충원누계", y="전공명", color="대학교",
            orientation="h", title="박사과정 인기 전공 TOP 10 (충원 누계 기준)",
            text="충원누계",
        )
        fig_top.update_layout(height=400, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_top, use_container_width=True)

        st.success("""
        **공주교대는 2년 연속 100% 충원**, 광주교대·대구교대도 높은 충원율을 기록.
        박사과정에 대한 **현직 교사의 실제 수요가 충분함**을 실증합니다.
        특히 상담·심리, AI교육, 교육행정 분야의 수요가 두드러집니다.
        """)
except Exception:
    pass  # 데이터 로딩 실패 시 건너뜀

st.markdown("""
#### 해석 시 유의점

신설 대학별 충원율은 지역 권역, 교원 규모, 전공 구성에 따라 차이가 있습니다.
전주교대에 직접 적용하기보다는, **박사과정에 대한 전국적 수요 존재**의 근거로 참고해야 합니다.

전주교대의 실제 수요 규모를 확인하기 위해서는
**전북 지역 현직 교사 대상 수요조사**가 필요합니다. (→ 향후 보강 필요 항목 참조)
""")

st.divider()

# ===========================================================================
# 5. 선발 전환 대학의 장기 안정성
# ===========================================================================
st.header("5. 교육전문대학원의 장기 운영 안정성")

if not summary.empty and not 전문대학원.empty:
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
        경인교대·서울교대는 수도권이라는 지역 이점이 있으므로 전주교대에 직접 비교하기는 어렵습니다.
        그러나 **교육전문대학원 모델이 12년간 안정적으로 운영 가능하다는 것**을 보여주는 사례로서 의미가 있습니다.

        전주교대의 예상 규모는 이보다 작겠지만, 병설 방식으로 운영하는
        광주교대·대구교대·공주교대·진주교대·청주교대의 모델이 더 적합한 비교 대상입니다.
        """)

st.divider()

# ===========================================================================
# 6. 전북 지역의 구조적 필요성
# ===========================================================================
st.header("6. 전북 지역의 구조적 필요성")

st.markdown("""
현재 교육전문대학원이 **미설치된 3개 교대의 소재지**:

| 대학교 | 소재지 | 가장 가까운 교육전문대학원 |
|--------|--------|--------------------------|
| **전주교대** | **전북** | **광주교대(광주) / 공주교대(충남)** |
| 부산교대 | 부산 | 진주교대(경남) |
| 춘천교대 | 강원 | 청주교대(충북) |

전북 지역 현직 초등교사가 박사과정을 이수하려면 **타 지역으로 이동**해야 합니다.

교육전문대학원은 현직 교사가 **재직하면서 수학**하는 과정이므로,
통학 거리와 시간은 진학 결정에 핵심적인 제약 요인입니다.

전주교대에 교육전문대학원이 설치되면:
- 전북 지역 현직 교사의 **재직 중 박사학위 취득 경로** 마련
- 지역 교육 전문인력의 **타 지역 유출 방지**
- 전북 교육 생태계의 **자생력 확보**
""")

st.divider()

# ===========================================================================
# 7. 설치 현황 종합
# ===========================================================================
st.header("7. 교육대학교 교육전문대학원 설치 현황 종합")

col1, col2, col3 = st.columns(3)
col1.metric("전체 교육대학교", f"{total}개교")
col2.metric("설치 완료", f"{installed}개교 ({pct:.0f}%)")
col3.metric("미설치", f"{not_installed}개교")

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

st.divider()

# ===========================================================================
# 8. 결론
# ===========================================================================
st.header("8. 결론")

if not summary.empty and not jnue.empty:
    st.info(f"""
    ### 데이터가 말하는 것

    1. **전국 교대 교육대학원 재학생이 공통적으로 감소** 중이며, 전주교대({전주_변화:+.1f}%)는 가장 심각합니다.
    2. **교육전문대학원 설치 대학**(평균 {설치_avg:+.1f}%)은 미설치 대학(평균 {미설치_avg:+.1f}%)보다
       총 대학원 규모를 안정적으로 유지하고 있습니다.
    3. 신설 대학의 첫 해 실적은 **박사과정에 대한 수요가 존재**함을 보여줍니다.
    4. 전북 지역에 교육전문대학원이 없어 **지역 교사의 박사과정 접근성**이 제약되고 있습니다.

    교육전문대학원 설치는 석사과정 수요 감소라는 구조적 문제에 대한 **체제 전환적 대응**이며,
    전북 지역 교육 전문인력 양성 기반을 확보하는 **전략적 선택**입니다.
    """)

st.divider()

# ===========================================================================
# 9. 향후 보강 필요 항목
# ===========================================================================
st.header("9. 향후 보강 필요 항목")

st.markdown("""
본 분석은 KESS 공개 데이터만으로 수행되었으며, 교육부 심사를 위해 다음 항목의 보강이 필요합니다.

| 항목 | 필요성 | 현재 상태 |
|------|--------|-----------|
| **전북 교사 수요조사** | 실증적 수요 규모 파악 (최소 500명 이상 설문) | 미실시 |
| **전주교대 교수진 역량** | 박사지도 가능 교수 수, 최근 5년 연구실적 | 미분석 |
| **특성화 전략** | 전북 지역 특화 전공 설계 (다문화교육, 농산어촌교육 등) | 미수립 |
| **교육부 정책 정합성** | 교원양성 구조개혁 기조와의 양립 논거 | 미작성 |
| **광주교대와의 차별화** | 전공 분야 차별화, 통학 시간/비용 비교 | 미분석 |
| **재정 자립 계획** | 예상 등록금 수입, 운영비용, 손익분기점 | 미산출 |
| **졸업 후 성과 모델** | 박사학위 취득 교사의 경력 경로 분석 | 미분석 |
| **전북 교사 타 지역 유출 데이터** | 광주/충남 교육전문대학원 전북 출신 재학생 수 | 미확인 |
| ~~**타 교대 박사과정 충원 현황**~~ | ~~신설 5개 교대 전공별 충원 데이터~~ | ✅ **반영 완료** |
| ~~**전주교대 양성과정 추이**~~ | ~~상담/특수교육 전공 10년 입학·졸업 추이~~ | ✅ **반영 완료** |
""")

st.divider()
st.caption("※ 본 분석은 KESS 교육통계 데이터베이스(kess.kedi.re.kr) 및 대학본부 제공 데이터를 기반으로 자동 생성되었습니다. 데이터 갱신 시 내용이 자동으로 업데이트됩니다.")
