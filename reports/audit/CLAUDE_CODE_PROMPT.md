# Claude Code 전달용 프롬프트

아래 내용을 그대로 Claude Code에게 전달하세요.

```text
너는 이 저장소(`/Users/taehyeong/JNUE-Policy-Research`)의 정책연구 보고서와 Streamlit 대시보드를 검수하는 코드 리뷰어다.

목표:
전주교대 교육전문대학원 정책연구 자료의 최근 수정사항이 정확한지, 수치와 원자료가 일치하는지, Streamlit 계산이 올바른지, 남은 확인 필요 항목이 적절히 분류되었는지 검토해줘. 필요하면 추가 수정까지 제안하되, 사용자가 만든 unrelated 변경은 되돌리지 마.

먼저 읽어야 할 파일:
- `reports/audit/수정사항_검수리포트.md`
- `reports/audit/AUDIT_REPORT.md`
- `reports/audit/FACT_LEDGER.csv`
- `reports/audit/SOURCE_TRACE.md`
- `reports/audit/STREAMLIT_CHECKS.md`

주요 수정 파일:
- `src/data_loader.py`
- `dashboard/pages/05_설치당위성.py`
- `reports/chapters/01_서론.md`
- `reports/chapters/02_정책환경.md`
- `reports/chapters/10_참고문헌_부록.md`
- `scripts/audit_report_facts.py`

검토해야 할 핵심 사항:
1. `src/data_loader.py`에서 대구교대 정원 셀 `('25년) 30 / (26년) 42`가 연도별로 제대로 파싱되는지 확인해.
2. `dashboard/pages/05_설치당위성.py`에서 2025학년도 충원율은 `37/30=123.3%`, 2026학년도 충원율은 `29/42=69.0%`로 계산되는지 확인해.
3. 충원 현황 엑셀의 행 수가 공식 전공 수와 다른 학교가 있으므로, 대시보드가 이를 `전공수`가 아니라 `충원자료 전공행수`로 표시하는지 확인해.
4. 보고서 본문에서 고등교육법 제29조와 제29조의2가 올바르게 구분되어 있는지 확인해. 제29조는 대학원 설치, 제29조의2는 대학원 종류 구분이다.
5. `scripts/audit_report_facts.py`를 실행했을 때 `reports/audit/FACT_LEDGER.csv`, `AUDIT_REPORT.md`, `SOURCE_TRACE.md`가 재생성되고, 현재 기준 `57건 중 PASS 53건, CHECK 4건`이 유지되는지 확인해.
6. 남은 CHECK 4건이 실제 오류인지, 아니면 기준 선택/해석 문제인지 판단해:
   - 대구교대 충원자료 전공행수 11 vs 정적 박사전공수 8
   - 진주교대 충원자료 전공행수 6 vs 정적 박사전공수 8
   - 2026학년도 교육부 세부기준 반영 여부
   - 대구교대 설치연도 기준 통일 문제
7. Streamlit 6개 페이지가 `streamlit.testing.v1.AppTest`에서 예외 없이 실행되는지 확인해.
8. `use_container_width` deprecation 경고는 기능 오류가 아니므로, 이번 검수에서는 잔여 기술부채로만 분류해.

검증 명령:
```bash
python3 scripts/audit_report_facts.py
python3 -m compileall src dashboard scripts
python3 - <<'PY'
from src.data_loader import get_doctoral_enrollment
p = get_doctoral_enrollment()
s = p.groupby('대학교_약칭').agg(
    양성정원=('양성정원','first'),
    양성정원_25=('양성정원_25학년도','first'),
    양성정원_26=('양성정원_26학년도','first'),
    충원_25=('충원_25학년도','sum'),
    충원_26=('충원_26학년도','sum'),
)
s['충원율_25'] = (s['충원_25'] / s['양성정원_25'] * 100).round(1)
s['충원율_26'] = (s['충원_26'] / s['양성정원_26'] * 100).round(1)
print(s.to_string())
PY
python3 - <<'PY'
from streamlit.testing.v1 import AppTest
paths = [
    'dashboard/app.py',
    'dashboard/pages/01_현황개요.py',
    'dashboard/pages/02_전공비교.py',
    'dashboard/pages/03_학생통계.py',
    'dashboard/pages/04_경쟁률분석.py',
    'dashboard/pages/05_설치당위성.py',
]
for path in paths:
    at = AppTest.from_file(path)
    at.run(timeout=60)
    print(path, len(at.exception))
    for exc in at.exception:
        print(exc)
PY
```

검토 결과를 다음 형식으로 답해줘:
1. 결론: PASS / 수정 필요 / 추가 확인 필요 중 하나
2. 발견사항: 심각도 순서로 파일 경로와 구체적 이유 제시
3. 수치 검산 결과: 대구교대, 공주교대, 전주교대 핵심 수치 중심
4. Streamlit 검증 결과
5. 남은 의사결정 항목: 대구교대 설치연도 기준, 2026학년도 기준 반영 여부

주의:
- `.env`는 건드리지 마.
- 기존 untracked 보고서/스크립트 파일이 있어도 사용자 작업일 수 있으니 삭제하거나 되돌리지 마.
- 확실히 틀린 수치만 수정 대상으로 지적하고, 기준 선택 문제는 의사결정 항목으로 분리해.
```
