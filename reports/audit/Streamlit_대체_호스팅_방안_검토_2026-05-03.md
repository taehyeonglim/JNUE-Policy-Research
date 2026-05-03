# Streamlit 대체 호스팅 방안 검토

작성일: 2026-05-03

## 1. 현 구조 진단

현재 프로젝트의 대시보드는 다음 구조다.

- 진입점: `dashboard/app.py`
- 세부 페이지: `dashboard/pages/01_현황개요.py` ~ `05_설치당위성.py`
- 데이터 로딩: `src/data_loader.py`
- 분석 함수: `src/analyzer.py`
- 차트: `src/charts.py`
- 의존성: `streamlit`, `pandas`, `plotly`, `openpyxl`

이 구조는 서버 기반 웹앱이다. 사용자는 `streamlit run dashboard/app.py`를 실행해야 하고, 실행 환경에는 Python 패키지와 KESS 엑셀 파일 경로가 맞아야 한다. 내부 연구자가 혼자 탐색할 때는 편하지만, 최종보고서와 함께 공유하거나 심의위원·교내 구성원에게 보여주기에는 불편하다.

가장 큰 문제는 현재 대시보드가 “입력-처리-저장” 앱이 아니라 “분석 결과 시각화”에 가깝다는 점이다. 이런 경우에는 굳이 서버를 계속 띄우는 방식보다, 정적 HTML 또는 문서형 대시보드가 더 단순하고 안정적이다.

## 2. 불편 지점

| 구분 | Streamlit 현재 방식의 불편 |
|---|---|
| 실행 | Python 환경, 패키지 설치, `streamlit run` 필요 |
| 배포 | Streamlit Cloud 또는 별도 서버 필요 |
| 공유 | 링크 공유는 가능하나 내부 데이터 파일·환경 의존성 관리 필요 |
| 보존 | 최종보고서 특정 시점의 분석 결과를 그대로 고정하기 어렵다 |
| 심의자료 | HWPX/PDF 보고서와 별도 앱으로 분리되어 논리 연결이 약하다 |
| 장기 유지 | Streamlit 버전, pandas/openpyxl 버전, 경로 문제에 취약 |

## 3. 대안 비교

| 대안 | 난이도 | 장점 | 단점 | 이 프로젝트 적합도 |
|---|---:|---|---|---|
| A. Streamlit 유지 + 개선 | 낮음 | 기존 코드 재사용, 빠른 수정 | 여전히 서버 실행 필요 | 중 |
| B. 정적 HTML 대시보드 생성 | 낮음~중 | 서버 불필요, 파일 하나로 공유, GitHub Pages 가능 | 사용자 입력형 앱에는 부적합 | 최상 |
| C. Quarto HTML 보고서 | 중 | 본문+표+차트+근거를 한 문서에 통합 | Quarto 설치 필요 | 상 |
| D. Evidence.dev | 중~상 | 데이터 대시보드형 정적 사이트에 강함 | Node/SQL 구조 도입 필요 | 중 |
| E. Jupyter Notebook / Voilà | 중 | 분석 과정 설명에 좋음 | 비개발자 공유에는 어색, 서버 필요 가능 | 중하 |
| F. Looker Studio / Tableau Public | 중 | 비개발자 친화적 | 데이터 업로드·보안·재현성 문제 | 중하 |
| G. GitHub Pages + Markdown/HTML | 낮음 | 유지보수 쉬움, 정적 배포 | 인터랙션 제한 | 상 |

## 4. 권장안

권장 구조는 **Streamlit을 폐기하지 않고, 기본 공유물은 정적 HTML 대시보드로 전환**하는 방식이다.

즉, 다음 2트랙 구조가 가장 현실적이다.

1. 내부 분석용: Streamlit 유지
2. 외부 공유·최종보고서 첨부용: 정적 HTML 대시보드 생성

이유는 명확하다. 현재 대시보드는 분석 결과를 보여주는 성격이 강하고, 사용자가 직접 값을 입력해 시뮬레이션하는 핵심 워크플로가 없다. 따라서 매번 서버를 띄우기보다, `python3 scripts/generate_dashboard_html.py` 한 번으로 `reports/dashboard/index.html`을 생성하고, 이 파일을 브라우저로 열거나 GitHub Pages에 올리는 방식이 더 쉽다.

## 5. 추천 구조

```text
src/
  data_loader.py
  analyzer.py
  charts.py

dashboard/
  app.py                         # 내부 탐색용 Streamlit 유지
  pages/

scripts/
  generate_dashboard_html.py     # 신규: 정적 HTML 생성

reports/
  dashboard/
    index.html                   # 신규: 공유용 대시보드
    assets/                      # 필요 시 CSV/이미지 저장
```

## 6. 정적 HTML 방식의 장점

정적 HTML 방식은 다음 이유로 이 프로젝트에 적합하다.

1. 서버가 필요 없다.
2. 인터넷이 없어도 열린다.
3. Plotly 차트는 HTML 안에서 확대, 호버, 다운로드가 가능하다.
4. 최종보고서 산출 시점의 데이터가 고정된다.
5. HWPX/PDF 보고서와 함께 `reports/` 폴더에 보관할 수 있다.
6. GitHub Pages, Netlify, 학교 내부 웹서버 어디든 올릴 수 있다.
7. 심의위원에게는 “앱을 실행하세요”가 아니라 “HTML 파일을 여세요”라고 안내할 수 있다.

## 7. 구현 방식

기존 Streamlit 페이지의 차트 로직을 전부 재작성할 필요는 없다. 이미 `src/charts.py`와 `src/analyzer.py`가 분리되어 있으므로, 정적 생성 스크립트에서 같은 함수를 호출하면 된다.

생성 스크립트의 기본 흐름은 다음과 같다.

```python
from pathlib import Path
import plotly.io as pio
from src.analyzer import get_overview_metrics, get_timeline_data
from src.data_loader import GRADUATE_SCHOOL_STATUS
from src.charts import create_status_table_chart, create_timeline_chart

OUT = Path("reports/dashboard/index.html")
OUT.parent.mkdir(parents=True, exist_ok=True)

metrics = get_overview_metrics()
fig1 = create_status_table_chart(GRADUATE_SCHOOL_STATUS)
fig2 = create_timeline_chart(get_timeline_data())

html = f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>전주교대 교육전문대학원 분석 대시보드</title>
</head>
<body>
  <h1>전주교대 교육전문대학원 분석 대시보드</h1>
  <section>
    <h2>핵심 지표</h2>
    <p>설치 완료: {metrics["설치_완료"]} / {metrics["총_교대수"]}</p>
    <p>미설치: {", ".join(metrics["미설치_대학"])}</p>
  </section>
  {pio.to_html(fig1, full_html=False, include_plotlyjs="cdn")}
  {pio.to_html(fig2, full_html=False, include_plotlyjs=False)}
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
```

최종 구현에서는 Streamlit의 5개 페이지를 그대로 5개 섹션으로 옮기거나, `index.html`, `majors.html`, `students.html`, `competition.html`, `rationale.html`처럼 5개 HTML로 나눌 수 있다.

## 8. 더 쉬운 최단기 대안

가장 빠른 임시 해결책은 Streamlit에서 “정적 캡처”를 만드는 것이다.

1. 현재 Streamlit을 실행한다.
2. 핵심 차트만 PNG 또는 HTML로 저장한다.
3. 최종보고서 부록에 이미지 또는 HTML 링크를 넣는다.

하지만 이 방식은 재생성 자동화가 약하다. 장기적으로는 `generate_dashboard_html.py`를 두는 편이 낫다.

## 9. 최종 권고

이 프로젝트에는 다음 순서가 가장 적절하다.

1. **1순위: 정적 HTML 대시보드 생성 스크립트 추가**
   - `scripts/generate_dashboard_html.py`
   - 산출물: `reports/dashboard/index.html`
   - 서버 없이 공유 가능

2. **2순위: Streamlit은 내부 탐색용으로 유지**
   - 연구팀이 데이터 확인할 때만 사용
   - 외부 공유용으로는 사용하지 않음

3. **3순위: 최종보고서와 HTML 대시보드 연결**
   - `reports/chapters/10_참고문헌_부록.md`의 부록 6 또는 별도 부록에 HTML 대시보드 경로 추가
   - HWPX 생성 시 “대화형 부록”으로 명시

4. **4순위: 필요하면 GitHub Pages 또는 학교 내부 정적 웹서버 배포**
   - Python 서버 불필요
   - `reports/dashboard/`만 배포하면 됨

## 10. 결론

Streamlit은 “분석 중 탐색 도구”로는 유지할 가치가 있지만, “분석결과 호스팅” 수단으로는 이 프로젝트에 과하다. 최종보고서와 함께 공유해야 하는 산출물이라면 **정적 HTML 대시보드**가 가장 쉽고 안정적이다.

따라서 권장 의사결정은 다음과 같다.

> Streamlit은 내부용으로 남기고, 외부 공유·최종보고서 첨부용 산출물은 `reports/dashboard/index.html` 정적 대시보드로 전환한다.
