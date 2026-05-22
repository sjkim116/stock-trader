# AlgoTrader Pro

**멀티마켓 자동 트레이딩 SaaS 플랫폼**

한국 및 미국 주식시장을 대상으로 하는 프로덕션 레벨의 알고리즘 트레이딩 플랫폼입니다.

---

## 프로젝트 개요

- **타겟 시장**: 한국 주식 (KOSPI/KOSDAQ) + 미국 주식 (NYSE/NASDAQ)
- **전략 유형**: 기술적 분석 기반 (이동평균, RSI, 볼린저 밴드 등)
- **서비스 규모**: 중규모 (100-1,000명 동시 사용자)
- **배포 환경**: AWS (ECS Fargate, RDS, ElastiCache 등)
- **개발 기간**: 6개월 (2026.05 ~ 2026.11)

---

## 주요 기능

### 사용자 기능
- ✅ 회원가입 / 로그인 (AWS Cognito)
- ✅ 증권사 계좌 연동 (KIS, Xing, IB, Alpaca)
- ✅ 거래 전략 선택 및 파라미터 설정
- ✅ 백테스팅 (과거 데이터 기반 전략 검증)
- ✅ 모의 거래 (Paper Trading)
- ✅ 실시간 자동 거래
- ✅ 포지션 및 손익 모니터링
- ✅ 거래 이력 조회
- ✅ 알림 설정 (이메일, 텔레그램)

### 시스템 기능
- ⚡ 실시간 시장 데이터 수집 (WebSocket)
- 🤖 전략 엔진 (Python + NumPy + Pandas)
- 📊 백테스팅 엔진 (Backtrader)
- 🛡️ 리스크 관리 (손절/익절, 일일 한도)
- 📈 웹 대시보드 (React + TypeScript)
- 🔒 AWS 기반 안전한 인프라
- 📊 모니터링 및 로깅 (CloudWatch)

---

## 기술 스택

### Frontend
- **React** 18 + **TypeScript** + **Vite**
- **Zustand** (상태 관리), **TanStack Query** (서버 상태)
- **Tailwind CSS** + **shadcn/ui**
- **TradingView Lightweight Charts** (차트)

### Backend
- **Python** 3.11 + **FastAPI** (User API, Strategy Engine, Order Execution, Risk Manager)
- **Go** 1.21 (Market Data Collector - 고성능)
- **SQLAlchemy** (ORM), **Alembic** (마이그레이션)

### Database
- **PostgreSQL** 15 + **TimescaleDB** (시계열 데이터)
- **Redis** 7 (캐시, Pub/Sub)

### Infrastructure
- **AWS ECS Fargate** (컨테이너 오케스트레이션)
- **AWS RDS**, **ElastiCache**, **S3**, **CloudFront**, **ALB**, **Route 53**
- **Terraform** (Infrastructure as Code)
- **GitHub Actions** (CI/CD)

### Monitoring
- **CloudWatch** (Logs, Metrics, Alarms)
- **SNS** (알림)

---

## 프로젝트 구조

```
stock-trader/
├── architecture/                # 아키텍처 설계 문서
│   ├── system-architecture.md
│   └── aws-infrastructure.md
├── backend/                     # 백엔드 서비스
│   ├── user-api/                # FastAPI - 사용자 API
│   ├── market-data-collector/   # Go - 실시간 데이터 수집
│   ├── strategy-engine/         # Python - 전략 실행 엔진
│   ├── order-execution/         # Python - 주문 실행
│   └── risk-manager/            # Python - 리스크 관리
├── frontend/                    # React 웹 대시보드
├── database/                    # 데이터베이스 스키마
│   └── schema.sql
├── infrastructure/              # Terraform IaC
│   └── terraform/
│       ├── modules/
│       └── environments/
├── scripts/                     # 유틸리티 스크립트
├── tests/                       # 테스트 코드
├── docs/                        # 추가 문서
├── .github/workflows/           # GitHub Actions CI/CD
├── docker-compose.yml           # 로컬 개발 환경
├── requirements-questionnaire-filled.md  # 요구사항 문진표
├── requirements-specification.md         # 요구사항 명세서
├── tech-stack.md                # 기술 스택 명세
├── roadmap.md                   # 6개월 개발 로드맵
└── README.md                    # 이 파일
```

---

## 빠른 시작 (로컬 개발)

### 사전 요구사항
- **Docker** 24.0+
- **Docker Compose** 2.18+
- **Node.js** 18+ (프론트엔드)
- **Python** 3.11+ (백엔드)
- **Go** 1.21+ (Market Data Collector)
- **PostgreSQL** 15+ (또는 Docker)

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/stock-trader.git
cd stock-trader
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 환경 변수 설정
```

### 3. Docker Compose로 로컬 서비스 실행

```bash
docker-compose up -d
```

이 명령어는 다음 서비스들을 시작합니다:
- PostgreSQL (Port: 5432)
- Redis (Port: 6379)
- User API (Port: 8000)
- Frontend (Port: 3000)

### 4. 데이터베이스 마이그레이션

```bash
cd backend/user-api
alembic upgrade head
```

### 5. 프론트엔드 개발 서버 시작

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000` 접속

---

## 배포

### AWS 인프라 프로비저닝 (Terraform)

```bash
cd infrastructure/terraform/environments/production
terraform init
terraform plan
terraform apply
```

상세한 배포 가이드는 [architecture/aws-infrastructure.md](architecture/aws-infrastructure.md) 참조

### CI/CD 파이프라인

GitHub Actions를 통한 자동 배포:
- `main` 브랜치 푸시 → Production 환경 배포
- `develop` 브랜치 푸시 → Staging 환경 배포

워크플로우: [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

---

## 문서

### 핵심 문서
1. [요구사항 문진표 (작성 완료)](requirements-questionnaire-filled.md)
2. [요구사항 명세서](requirements-specification.md)
3. [시스템 아키텍처](architecture/system-architecture.md)
4. [AWS 인프라 설계](architecture/aws-infrastructure.md)
5. [기술 스택](tech-stack.md)
6. [데이터베이스 스키마](database/schema.sql)
7. [6개월 개발 로드맵](roadmap.md)

### API 문서
- FastAPI Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

---

## 개발 가이드

### 브랜치 전략
- `main`: 프로덕션 배포 브랜치
- `develop`: 개발 통합 브랜치
- `feature/*`: 기능 개발 브랜치
- `hotfix/*`: 긴급 수정 브랜치

### 커밋 메시지 컨벤션
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 리팩토링
test: 테스트 코드 추가/수정
chore: 빌드, 설정 파일 수정
```

### 코드 품질
- **Python**: Black (포매터), Flake8 (린터), MyPy (타입 체커)
- **TypeScript**: Prettier (포매터), ESLint (린터)
- **Pre-commit hooks** 사용

---

## 테스트

### Backend (Python)
```bash
cd backend/user-api
pytest
pytest --cov=app tests/  # 커버리지 포함
```

### Frontend (TypeScript)
```bash
cd frontend
npm run test
npm run test:coverage
```

### E2E 테스트
```bash
npm run test:e2e
```

---

## 라이선스

Copyright (c) 2026 AlgoTrader Pro Team. All rights reserved.

This is proprietary software. Unauthorized copying, distribution, or use is strictly prohibited.

---

## 연락처

- **프로젝트 매니저**: pm@algotrader.pro
- **기술 지원**: support@algotrader.pro
- **웹사이트**: https://algotrader.pro

---

## 기여자

- [Your Name] - Project Lead & Backend Developer
- [Developer 2] - Backend Developer
- [Developer 3] - Frontend Developer
- [Developer 4] - DevOps Engineer
- [Developer 5] - Quantitative Analyst

---

## 변경 이력

### v0.1.0 (2026-05-14)
- 초기 프로젝트 설정
- 요구사항 문서 및 아키텍처 설계 완료
- 프로젝트 구조 생성

---

**Built with ❤️ by AlgoTrader Pro Team**
