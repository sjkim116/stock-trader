# 🚀 AlgoTrader Pro - 빠른 시작 가이드

**5분 안에 로컬 개발 환경 시작하기**

---

## 사전 요구사항

아래 소프트웨어가 설치되어 있어야 합니다:
- ✅ Docker Desktop 24.0+ ([다운로드](https://www.docker.com/products/docker-desktop))
- ✅ Git ([다운로드](https://git-scm.com/downloads))
- ⚠️ Node.js 18+ (Frontend 개발 시 필요)
- ⚠️ Python 3.11+ (Backend 로컬 개발 시 필요)

---

## Step 1: 프로젝트 클론

```bash
git clone <repository-url>
cd stock-trader
```

---

## Step 2: 환경 변수 설정

```bash
# .env 파일 생성 (예제 파일 복사)
cp .env.example .env

# Windows에서는:
# copy .env.example .env
```

**필수 환경 변수** (개발 환경은 기본값 사용 가능):
- `DATABASE_URL` - PostgreSQL 연결 문자열
- `REDIS_URL` - Redis 연결 문자열
- `SECRET_KEY` - JWT 시크릿 키

---

## Step 3: Docker Compose로 서비스 시작

```bash
docker-compose up -d
```

이 명령어는 다음 서비스들을 시작합니다:
- 🐘 **PostgreSQL** (Port 5432) - 데이터베이스
- 🔴 **Redis** (Port 6379) - 캐시
- 🚀 **User API** (Port 8000) - FastAPI 백엔드
- 🛠️ **PgAdmin** (Port 5050) - DB 관리 도구
- 📊 **Redis Commander** (Port 8081) - Redis 관리 도구

---

## Step 4: 서비스 확인

### 4.1 서비스 상태 확인
```bash
docker-compose ps
```

모든 서비스가 `Up` 상태여야 합니다.

### 4.2 User API 헬스체크
```bash
curl http://localhost:8000/health
```

또는 브라우저에서: http://localhost:8000

**응답 예시**:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-14T10:00:00",
  "service": "user-api",
  "environment": "development"
}
```

### 4.3 API 문서 확인
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Step 5: Frontend 실행 (선택)

Frontend를 개발하려면:

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

브라우저에서 http://localhost:3000 접속

---

## 🎯 다음 단계

### Backend 개발
```bash
cd backend/user-api

# 가상 환경 생성 (선택)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 로컬에서 직접 실행 (Docker 없이)
uvicorn app.main:app --reload
```

### Frontend 개발
```bash
cd frontend
npm run dev
```

### 데이터베이스 접속
**PgAdmin**:
1. http://localhost:5050 접속
2. 로그인: `admin@algotrader.local` / `admin`
3. 서버 추가:
   - Host: `postgres`
   - Port: `5432`
   - Database: `algotrader`
   - Username: `algotrader`
   - Password: `dev_password_change_me`

**Redis Commander**:
1. http://localhost:8081 접속
2. 바로 사용 가능 (인증 불필요)

---

## 🧪 테스트 실행

### Backend 테스트
```bash
cd backend/user-api
pytest tests/
```

### Frontend 테스트
```bash
cd frontend
npm run test
```

---

## 🛑 서비스 중지

```bash
# 모든 서비스 중지
docker-compose down

# 데이터까지 삭제
docker-compose down -v
```

---

## 📝 로그 확인

### 전체 로그
```bash
docker-compose logs -f
```

### 특정 서비스 로그
```bash
docker-compose logs -f user-api
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

## 🔍 문제 해결

### 포트 충돌
만약 포트가 이미 사용 중이라면:
1. `docker-compose.yml` 파일에서 포트 번호 변경
2. 또는 기존 프로세스 종료

```bash
# Windows에서 포트 사용 프로세스 확인
netstat -ano | findstr :8000

# Linux/Mac에서
lsof -i :8000
```

### 컨테이너 재시작
```bash
# 전체 재시작
docker-compose restart

# 특정 서비스만
docker-compose restart user-api
```

### 이미지 다시 빌드
```bash
docker-compose up --build
```

### 데이터베이스 초기화
```bash
docker-compose down -v
docker-compose up -d
```

---

## 📚 추가 문서

- [README.md](README.md) - 프로젝트 전체 개요
- [PHASE2_WEEK1_COMPLETE.md](PHASE2_WEEK1_COMPLETE.md) - Phase 2 Week 1 완료 보고서
- [architecture/system-architecture.md](architecture/system-architecture.md) - 시스템 아키텍처
- [roadmap.md](roadmap.md) - 개발 로드맵

---

## 💡 유용한 명령어

```bash
# Docker 컨테이너 쉘 접속
docker-compose exec user-api bash
docker-compose exec postgres psql -U algotrader -d algotrader

# 데이터베이스 스키마 적용
docker-compose exec postgres psql -U algotrader -d algotrader -f /docker-entrypoint-initdb.d/01-schema-oltp.sql
docker-compose exec postgres psql -U algotrader -d algotrader -f /docker-entrypoint-initdb.d/02-schema-timeseries.sql

# 코드 포맷팅 (Backend)
cd backend/user-api
black app/
isort app/

# 코드 포맷팅 (Frontend)
cd frontend
npm run format
```

---

## ❓ 도움이 필요하신가요?

- 📧 Email: dev-support@algotrader.local
- 📖 문서: [docs/](docs/)
- 🐛 이슈 리포트: GitHub Issues

---

**Happy Coding! 🎉**
