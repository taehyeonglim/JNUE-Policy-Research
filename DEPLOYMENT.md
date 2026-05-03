# GitHub Pages 배포 안내

이 디렉터리는 전주교대 교육전문대학원 정책연구 분석 결과를 정적 사이트로 제공한다.

## 로컬 생성

```bash
python3 scripts/generate_pages_site.py
```

생성 결과:

- `docs/index.html`
- `docs/.nojekyll`
- `docs/assets/전주교대_교육전문대학원_설치_정책연구_초안.hwpx`

## 로컬 확인

```bash
python3 -m http.server 4173 --directory docs
```

브라우저에서 다음 주소를 연다.

```text
http://127.0.0.1:4173/
```

## GitHub Pages 배포

`.github/workflows/pages.yml`이 main 브랜치 push 시 자동으로 다음 작업을 수행한다.

1. Python 3.12 설치
2. `requirements.txt` 의존성 설치
3. `scripts/generate_pages_site.py` 실행
4. `docs/`를 GitHub Pages artifact로 업로드
5. GitHub Pages에 배포

저장소 Settings → Pages의 Build and deployment Source는 `GitHub Actions`로 설정한다.

배포 후 예상 URL:

```text
https://taehyeonglim.github.io/JNUE-Policy-Research/
```
