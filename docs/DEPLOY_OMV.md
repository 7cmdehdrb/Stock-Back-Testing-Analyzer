# OMV Docker Compose 배포 가이드

> OMV(OpenMediaVault) + Docker Compose 환경에서 포트폴리오 성과 분석기를 배포하는 방법입니다.
> `/appdata` 폴더 안에서 git clone하여 사용하는 방식을 기준으로 합니다.

---

## 1. 사전 준비

OMV에 아래 조건이 충족되어야 합니다.

- Docker 및 Docker Compose 설치 (`openmediavault-compose` 플러그인 또는 직접 설치)
- `/appdata` 공유 폴더가 존재하고 접근 가능한 상태
- 서버에 SSH 접속 가능

---

## 2. 코드 받기 (git clone)

```bash
# /appdata 로 이동
cd /appdata

# 레포지토리 클론
git clone <your-repo-url> Stock-Back-Testing-Analyzer

# 클론된 폴더로 이동
cd Stock-Back-Testing-Analyzer
```

---

## 3. 환경변수 설정

```bash
# .env.example 을 복사
cp .env.example .env

# .env 편집
nano .env
```

`.env` 파일에서 **`SECRET_KEY`** 를 반드시 변경하세요.

```bash
# 랜덤 키 생성 방법
python3 -c "import secrets; print(secrets.token_hex(32))"
# → 출력된 값을 .env 의 SECRET_KEY 에 붙여넣기
```

최소한 아래 항목은 채워야 합니다.

```dotenv
SECRET_KEY=생성한_랜덤_키_여기에_입력
HOST_PORT=8000
TZ=Asia/Seoul
```

---

## 4. DB 데이터 폴더 생성

컨테이너는 `./data` 폴더를 `/data`로 마운트합니다.
실제 경로: `/appdata/Stock-Back-Testing-Analyzer/data/`

```bash
mkdir -p data
```

---

## 5. 실행

```bash
# 이미지 빌드 + 컨테이너 시작 (백그라운드)
docker compose up -d --build

# 로그 확인
docker compose logs -f stock-analyzer

# 상태 확인
docker compose ps
```

---

## 6. 접속

브라우저에서 접속:

```
http://<OMV-서버-IP>:8000
```

---

## 7. 업데이트

새 버전 반영 시:

```bash
cd /appdata/Stock-Back-Testing-Analyzer

# 최신 코드 받기
git pull

# 이미지 재빌드 후 재시작 (data/ 폴더의 DB는 유지됨)
docker compose up -d --build
```

---

## 8. 데이터 위치 및 백업

SQLite DB는 아래 경로에 직접 저장됩니다:

```
/appdata/Stock-Back-Testing-Analyzer/data/stock_cache.db
```

컨테이너와 무관하게 호스트 파일시스템에 있으므로,
OMV의 공유 폴더 백업 기능이나 `rsync` 등으로 직접 백업할 수 있습니다.

```bash
# 수동 백업 예시
cp /appdata/Stock-Back-Testing-Analyzer/data/stock_cache.db \
   /appdata/backups/stock_cache_$(date +%Y%m%d).db
```

---

## 9. 관리 명령어

```bash
# 컨테이너 중지
docker compose down

# 컨테이너 재시작 (코드 변경 없이)
docker compose restart

# 최근 100줄 로그
docker compose logs --tail=100 stock-analyzer
```

