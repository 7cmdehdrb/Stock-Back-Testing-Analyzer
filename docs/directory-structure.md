# 디렉토리 구조 설명

이 문서는 저장소의 주요 파일과 디렉토리가 어떤 역할을 하는지 설명합니다.

## 최상위 구조

```text
Stock-Back-Testing-Analyzer/
├── app.py
├── wsgi.py
├── requirements.txt
├── Dockerfile
├── README.md
├── docs/
├── templates/
├── sample_portfolio/
├── temp/
├── stock_cache.db
├── img.png
├── PYTHONANYWHERE_DEPLOY.md
└── SIGNUP_GUIDE.md
```

## 주요 파일

### `app.py`

프로젝트의 핵심 Flask 애플리케이션입니다. 다음 역할을 대부분 담당합니다.

- Flask 앱과 SQLAlchemy 초기화
- 데이터베이스 모델 정의
- Flask-Admin 관리자 화면 설정
- 주가/환율 데이터 캐싱
- CSV 파싱과 포트폴리오 분석
- 수익률 및 위험 지표 계산
- 로그인, 회원가입, 이메일 인증 API
- 포트폴리오 저장/조회/삭제 API
- 랭킹, 마이페이지, 포트폴리오 상세 페이지 라우팅
- AI 분석 API

현재는 많은 기능이 단일 파일에 모여 있으므로, 향후 유지보수성을 높이려면 인증, 데이터 수집, 분석 계산, API 라우트, 관리자 설정을 모듈로 분리하는 것을 고려할 수 있습니다.

### `wsgi.py`

WSGI 서버 또는 PythonAnywhere 같은 호스팅 환경에서 Flask 앱을 로드하기 위한 진입점입니다.

### `requirements.txt`

Python 의존성 목록입니다. Flask, pandas, yfinance, SQLAlchemy, OpenAI 클라이언트 등 실행에 필요한 패키지가 포함됩니다.

### `Dockerfile`

컨테이너 환경에서 애플리케이션을 실행하기 위한 이미지 빌드 설정입니다.

### `README.md`

사용자 관점의 프로젝트 소개, 빠른 시작, CSV 준비 방법, 주요 기능, 문서 링크를 제공합니다. 기술적인 세부 설명은 `docs/` 아래 문서로 분리되어 있습니다.

### `stock_cache.db`

SQLite 데이터베이스 파일입니다. 주가 캐시, 환율 캐시, 사용자, 저장 포트폴리오, 이메일 인증 정보가 저장됩니다.

> 운영 환경에서는 이 파일을 민감 데이터로 취급하고 백업 및 접근 권한을 관리해야 합니다.

### `img.png`

README에서 사용하는 애플리케이션 화면 예시 이미지입니다.

## `docs/`

프로젝트 설명 문서를 모아 둔 디렉토리입니다.

```text
docs/
├── project-overview.md
└── directory-structure.md
```

- `project-overview.md`: 전체 프로젝트 목적, 기능, 데이터 흐름, 기술 스택, 환경 변수, 운영 주의 사항을 설명합니다.
- `directory-structure.md`: 저장소 구조와 주요 파일/디렉토리의 역할을 설명합니다.

## `templates/`

Flask/Jinja2 HTML 템플릿 디렉토리입니다.

```text
templates/
├── base.html
├── index.html
├── login.html
├── signup.html
├── mypage.html
├── portfolio_view.html
├── ranking.html
├── ranking_old.html
├── exchange_rate.html
├── admin_login.html
└── admin/
    └── dashboard.html
```

### 주요 템플릿 역할

| 파일 | 역할 |
| --- | --- |
| `base.html` | 공통 레이아웃과 네비게이션의 기반 템플릿 |
| `index.html` | CSV 업로드와 포트폴리오 분석을 수행하는 메인 화면 |
| `login.html` | 사용자 로그인 화면 |
| `signup.html` | 이메일 인증 기반 회원가입 화면 |
| `mypage.html` | 저장한 포트폴리오와 사용자 정보를 확인하는 화면 |
| `portfolio_view.html` | 저장된 포트폴리오 상세 보기 화면 |
| `ranking.html` | 저장 포트폴리오 랭킹 화면 |
| `exchange_rate.html` | 환율 관련 화면 |
| `admin_login.html` | 관리자 로그인 화면 |
| `admin/dashboard.html` | 관리자 대시보드 화면 |

## `sample_portfolio/`

벤치마크 또는 예시로 사용할 수 있는 샘플 포트폴리오 CSV 파일을 포함합니다.

```text
sample_portfolio/
├── BERKSHIRE_HATHAWAY.csv
├── BLACKROCK.csv
└── owner.csv
```

- `BERKSHIRE_HATHAWAY.csv`: 버크셔 해서웨이형 벤치마크 포트폴리오
- `BLACKROCK.csv`: 블랙록형 벤치마크 포트폴리오
- `owner.csv`: 예시 또는 운영 보조 데이터로 사용되는 CSV

## `temp/`

임시 또는 실험용 코드가 위치한 디렉토리입니다.

```text
temp/
└── app2.py
```

운영 코드와 혼동하지 않도록, 실제 서비스 진입점은 최상위 `app.py`를 기준으로 봐야 합니다.

## 배포 및 보조 문서

| 파일 | 설명 |
| --- | --- |
| `PYTHONANYWHERE_DEPLOY.md` | PythonAnywhere 배포 절차 안내 |
| `SIGNUP_GUIDE.md` | 회원가입 및 이메일 인증 기능 관련 안내 |
| `pythonanywhere.txt` | PythonAnywhere 설정 또는 메모성 파일 |
| `wsgi.txt` | WSGI 설정 참고 파일 |
| `build_log.txt` | 빌드/배포 과정에서 생성된 로그성 파일 |
| `extensions.list` | 환경 또는 확장 목록으로 보이는 보조 파일 |

## 런타임 데이터와 버전 관리 주의 사항

다음 파일은 실행 중 생성되거나 환경에 따라 달라질 수 있습니다.

- `stock_cache.db`
- 로그 파일
- 로컬 `.env`
- Python 캐시 디렉토리

민감 정보가 포함될 수 있는 파일은 공개 저장소에 커밋하지 않는 것이 좋습니다.
