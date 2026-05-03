# Streamlit 검증 결과

## 실행 검증

| 항목 | 결과 | 비고 |
|---|---|---|
| `python3 -m compileall src dashboard scripts` | PASS | Python 문법 컴파일 통과 |
| `streamlit.testing.v1.AppTest` - `dashboard/app.py` | PASS | 예외 0건 |
| `streamlit.testing.v1.AppTest` - `01_현황개요.py` | PASS | 예외 0건 |
| `streamlit.testing.v1.AppTest` - `02_전공비교.py` | PASS | 예외 0건 |
| `streamlit.testing.v1.AppTest` - `03_학생통계.py` | PASS | 예외 0건 |
| `streamlit.testing.v1.AppTest` - `04_경쟁률분석.py` | PASS | 예외 0건 |
| `streamlit.testing.v1.AppTest` - `05_설치당위성.py` | PASS | 예외 0건 |
| 로컬 서버 `dashboard/app.py` | PASS | `http://127.0.0.1:8501` HEAD 200 OK |
| 로컬 서버 `05_설치당위성.py` | PASS | `http://127.0.0.1:8502` HEAD 200 OK |

## 수정 확인

- 대구교대 정원 셀 `('25년) 30 / (26년) 42`를 연도별로 파싱하도록 수정했다.
- `05_설치당위성.py`의 충원율 계산은 이제 2025학년도 30명, 2026학년도 42명을 각각 분모로 사용한다.
- 충원 현황 엑셀의 전공 행 수는 공식 전공 수와 일치하지 않는 학교가 있어, 대시보드 표시명을 `전공수`에서 `충원자료 전공행수`로 낮췄다.

## 잔여 기술부채

- Streamlit 1.55.0에서 `use_container_width`는 2025-12-31 이후 제거 예정이라는 경고가 출력된다. 동작 오류는 아니지만, 추후 `width="stretch"`로 전환하는 정비가 필요하다.
