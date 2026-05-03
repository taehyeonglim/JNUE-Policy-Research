# GitHub Pages 배포 안내

이 저장소는 Streamlit 서버 대신 정적 GitHub Pages로 전주교대 교육전문대학원 정책연구 분석 결과를 제공한다.

## 로컬 생성

```bash
python3 scripts/generate_pages_site.py
```

생성 결과:

- `docs/index.html`
- `docs/.nojekyll`

## 로컬 확인

```bash
python3 -m http.server 4173 --directory docs
```

브라우저에서 다음 주소를 연다.

```text
http://127.0.0.1:4173/
```

## 자동 배포 구조

`.github/workflows/pages.yml`은 main 브랜치 push 시 다음 작업을 수행한다.

1. Python 3.12 설치
2. `requirements.txt` 의존성 설치
3. `scripts/generate_pages_site.py` 실행
4. `docs/.nojekyll` 보장
5. `docs/` 전체를 `gh-pages` 브랜치 루트로 발행

이 방식은 GitHub Pages의 artifact 배포 설정에 의존하지 않고, 정적 파일을 `gh-pages` 브랜치에 직접 게시한다.

## 저장소 Pages 활성화

GitHub Pages 사이트는 저장소 설정에서 한 번 활성화해야 한다. 저장소 관리자 화면에서 다음과 같이 설정한다.

1. Settings → Pages
2. Build and deployment → Source: `Deploy from a branch`
3. Branch: `gh-pages`
4. Folder: `/ (root)`
5. Save

배포 후 예상 URL:

```text
https://taehyeonglim.github.io/JNUE-Policy-Research/
```

## 현재 확인된 상태

- GitHub Actions 빌드와 `gh-pages` 브랜치 발행은 성공한다.
- `gh-pages/index.html`에는 정적 대시보드가 생성되어 있다.
- 공개 URL이 404이면 저장소 Pages 기능이 아직 활성화되지 않은 상태다.
