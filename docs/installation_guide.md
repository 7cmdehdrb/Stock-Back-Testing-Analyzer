# 주식 백테스팅 분석기 설치 및 실행 가이드

이 문서에서는 **Stock-Back-Testing-Analyzer** 프로젝트를 로컬 환경에 설치하고 실행하는 방법을 안내합니다.

## 1. 사전 요구 사항 (Prerequisites)

*   **Python 3.10 ~ 3.12 권장**: (※ Python 3.13 환경에서는 `pandas` 등 일부 라이브러리의 의존성 빌드 에러가 발생할 수 있습니다. 3.13 이상 사용 시 기존 `requirements.txt` 내 특정 버전 제약을 지우고 설치해야 합니다.)
*   **Git**: 소스 코드를 클론하기 위해 필요합니다.

## 2. 프로젝트 다운로드

프로젝트를 로컬 환경으로 클론하거나 다운로드합니다.

```bash
git clone <repository_url>
cd Stock-Back-Testing-Analyzer
```

## 3. 가상환경 설정 및 패키지 설치

파이썬 가상환경(venv)을 생성하여 격리된 환경에서 패키지를 관리하는 것을 권장합니다.

### Windows (PowerShell/CMD)

```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
.\venv\Scripts\activate

# 3. 필수 패키지 설치
pip install -r requirements.txt
```

> [!NOTE]
> Python 3.13 이상의 환경에서 패키지 설치 중 에러가 발생한다면, 버전이 명시되지 않은 패키지로 설치를 시도해주세요.
> `(Get-Content requirements.txt) -replace '==.*', '' | Set-Content requirements_py313.txt`
> `pip install -r requirements_py313.txt`

### Mac / Linux

```bash
# 1. 가상환경 생성
python3 -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 필수 패키지 설치
pip install -r requirements.txt
```

## 4. 환경 변수 (.env) 설정

프로젝트 최상위 디렉토리에 `.env` 파일을 생성하고 다음 필수 환경 변수들을 설정합니다.

```ini
# .env 파일 예시
SECRET_KEY=your_flask_secret_key_here
OPENAI_API_KEY=your_openai_api_key_here
DEBUG=True
```

*   `SECRET_KEY`: Flask 세션 및 폼 보안을 위한 임의의 문자열을 입력합니다.
*   `OPENAI_API_KEY`: AI 분석 기능을 위해 필요한 OpenAI API 키를 입력합니다.
*   `DEBUG`: 로컬 개발 시에는 `True`로 설정합니다. (운영 환경에서는 `False`)

## 5. 서버 실행

모든 설정이 완료되었다면 다음 명령어로 서버를 실행합니다.

```bash
python app.py
```

콘솔에 `* Running on http://127.0.0.1:5000` 문구가 나타나면 서버가 정상적으로 실행된 것입니다.
브라우저를 열고 `http://127.0.0.1:5000` 에 접속하여 애플리케이션을 사용할 수 있습니다.

## 6. 추가 설정 (선택 사항)

### 관리자 페이지 접속
*   서버 실행 후 `http://127.0.0.1:5000/admin` 경로를 통해 Flask-Admin 대시보드에 접근할 수 있습니다. (데이터베이스의 캐시, 유저 정보 등을 직접 관리)

### 데이터베이스
*   기본적으로 SQLite (`stock_cache.db`)를 사용하여 별도의 DB 서버 구축 없이 바로 작동합니다. 앱 실행 및 데이터 저장 시 로컬에 파일 형태로 자동 관리됩니다.
