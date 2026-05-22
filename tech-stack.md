# AlgoTrader Pro - 기술 스택 명세서

**버전**: 1.0
**작성일**: 2026-05-14

---

## Frontend

### Core
| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18.2+ | UI 프레임워크 |
| **TypeScript** | 5.0+ | 타입 안전성 |
| **Vite** | 4.3+ | 빌드 도구 |

### 상태 관리
| 기술 | 버전 | 용도 |
|------|------|------|
| **Zustand** | 4.3+ | 전역 상태 관리 |
| **TanStack Query** | 4.29+ | 서버 상태 관리, 캐싱 |

### UI/UX
| 기술 | 버전 | 용도 |
|------|------|------|
| **Tailwind CSS** | 3.3+ | CSS 프레임워크 |
| **shadcn/ui** | latest | UI 컴포넌트 |
| **Radix UI** | latest | Headless UI (shadcn 기반) |
| **Lucide React** | latest | 아이콘 |
| **TradingView Lightweight Charts** | 4.0+ | 차트 (가격, 손익) |
| **Recharts** | 2.6+ | 통계 차트 |

### 통신
| 기술 | 버전 | 용도 |
|------|------|------|
| **Axios** | 1.4+ | HTTP 클라이언트 |
| **Socket.io-client** | 4.6+ | WebSocket (실시간 데이터) |

### 폼 및 검증
| 기술 | 버전 | 용도 |
|------|------|------|
| **React Hook Form** | 7.44+ | 폼 관리 |
| **Zod** | 3.21+ | 스키마 검증 |

### 기타
| 기술 | 버전 | 용도 |
|------|------|------|
| **date-fns** | 2.30+ | 날짜 포맷팅 |
| **react-router-dom** | 6.11+ | 라우팅 |

---

## Backend - User API

### Core
| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 프로그래밍 언어 |
| **FastAPI** | 0.100+ | 웹 프레임워크 |
| **Uvicorn** | 0.22+ | ASGI 서버 |

### ORM 및 데이터베이스
| 기술 | 버전 | 용도 |
|------|------|------|
| **SQLAlchemy** | 2.0+ | ORM |
| **Alembic** | 1.11+ | 데이터베이스 마이그레이션 |
| **asyncpg** | 0.28+ | PostgreSQL 비동기 드라이버 |
| **redis** | 4.5+ | Redis 클라이언트 |

### 인증 및 보안
| 기술 | 버전 | 용도 |
|------|------|------|
| **python-jose** | 3.3+ | JWT 처리 |
| **passlib** | 1.7+ | 비밀번호 해싱 |
| **bcrypt** | 4.0+ | 해싱 알고리즘 |
| **cryptography** | 41.0+ | 암호화 |

### AWS SDK
| 기술 | 버전 | 용도 |
|------|------|------|
| **boto3** | 1.26+ | AWS SDK |
| **aioboto3** | 11.2+ | Async AWS SDK |

### 검증 및 직렬화
| 기술 | 버전 | 용도 |
|------|------|------|
| **Pydantic** | 2.0+ | 데이터 검증 |

### 테스팅
| 기술 | 버전 | 용도 |
|------|------|------|
| **pytest** | 7.3+ | 테스트 프레임워크 |
| **pytest-asyncio** | 0.21+ | 비동기 테스트 |
| **httpx** | 0.24+ | HTTP 테스트 클라이언트 |
| **pytest-cov** | 4.1+ | 코드 커버리지 |

### 코드 품질
| 기술 | 버전 | 용도 |
|------|------|------|
| **black** | 23.3+ | 코드 포매터 |
| **flake8** | 6.0+ | 린터 |
| **mypy** | 1.3+ | 타입 체커 |
| **isort** | 5.12+ | Import 정렬 |

---

## Backend - Market Data Collector

### Core
| 기술 | 버전 | 용도 |
|------|------|------|
| **Go** | 1.21+ | 프로그래밍 언어 (고성능) |

### WebSocket 클라이언트
| 기술 | 버전 | 용도 |
|------|------|------|
| **gorilla/websocket** | 1.5+ | WebSocket 클라이언트 |
| **nhooyr.io/websocket** | 1.8+ | WebSocket (대체) |

### 데이터베이스
| 기술 | 버전 | 용도 |
|------|------|------|
| **pgx** | 5.3+ | PostgreSQL 드라이버 |
| **go-redis/redis** | 9.0+ | Redis 클라이언트 |

### 증권사 API
| 기술 | 버전 | 용도 |
|------|------|------|
| **한국투자증권 KIS API** | - | 한국 주식 실시간 데이터 |
| **이베스트 Xing API** | - | 한국 주식 (대체) |
| **Interactive Brokers API** | latest | 미국 주식 |
| **Alpaca API** | v2 | 미국 주식 (대체) |

### 기타
| 기술 | 버전 | 용도 |
|------|------|------|
| **zap** | 1.24+ | 구조화 로깅 |
| **viper** | 1.16+ | 설정 관리 |

---

## Backend - Strategy Engine

### Core
| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 프로그래밍 언어 |

### 데이터 분석
| 기술 | 버전 | 용도 |
|------|------|------|
| **NumPy** | 1.24+ | 수치 계산 |
| **Pandas** | 2.0+ | 데이터 분석 |
| **TA-Lib** | 0.4.26+ | 기술적 지표 |
| **pandas-ta** | 0.3+ | 기술적 분석 (추가) |

### 백테스팅
| 기술 | 버전 | 용도 |
|------|------|------|
| **Backtrader** | 1.9+ | 백테스팅 엔진 |
| **vectorbt** | 0.25+ | 벡터화 백테스팅 (빠름) |

### 머신러닝 (Phase 2)
| 기술 | 버전 | 용도 |
|------|------|------|
| **scikit-learn** | 1.2+ | ML 라이브러리 |
| **TensorFlow** | 2.12+ | 딥러닝 (선택) |
| **PyTorch** | 2.0+ | 딥러닝 (선택) |

---

## Database

### Relational Database
| 기술 | 버전 | 용도 |
|------|------|------|
| **PostgreSQL** | 15.x | 메인 데이터베이스 |
| **TimescaleDB** | 2.11+ | 시계열 데이터 (PostgreSQL 확장) |

### In-Memory Database
| 기술 | 버전 | 용도 |
|------|------|------|
| **Redis** | 7.0+ | 캐시, Pub/Sub, 세션 |

---

## Message Queue & Streaming

| 기술 | 용도 |
|------|------|
| **AWS SQS** | 메시지 큐 (주문, 백테스팅) |
| **AWS SNS** | Pub/Sub (알림, 이벤트) |

---

## Infrastructure

### Container
| 기술 | 버전 | 용도 |
|------|------|------|
| **Docker** | 24.0+ | 컨테이너화 |
| **Docker Compose** | 2.18+ | 로컬 개발 환경 |

### Orchestration
| 기술 | 용도 |
|------|------|
| **AWS ECS Fargate** | 컨테이너 오케스트레이션 (서버리스) |

### Infrastructure as Code
| 기술 | 버전 | 용도 |
|------|------|------|
| **Terraform** | 1.5+ | 인프라 프로비저닝 |

### CI/CD
| 기술 | 용도 |
|------|------|
| **GitHub Actions** | CI/CD 파이프라인 |

---

## AWS Services

| 서비스 | 용도 |
|--------|------|
| **ECS Fargate** | 컨테이너 실행 |
| **RDS PostgreSQL** | 관리형 데이터베이스 |
| **ElastiCache Redis** | 관리형 Redis |
| **S3** | 객체 스토리지 (로그, 백업) |
| **CloudFront** | CDN (정적 자산) |
| **Route 53** | DNS |
| **ALB** | Application Load Balancer |
| **Cognito** | 사용자 인증 |
| **Secrets Manager** | 시크릿 관리 (API 키, DB 비밀번호) |
| **CloudWatch** | 모니터링, 로그, 알람 |
| **SNS** | 알림 |
| **SQS** | 메시지 큐 |
| **Lambda** | 서버리스 함수 (백테스팅) |
| **WAF** | Web Application Firewall |
| **ACM** | SSL/TLS 인증서 |

---

## Monitoring & Logging

| 기술 | 용도 |
|------|------|
| **CloudWatch Logs** | 중앙 로그 수집 |
| **CloudWatch Metrics** | 메트릭 수집 |
| **CloudWatch Alarms** | 알람 |
| **AWS X-Ray** | 분산 추적 (선택) |

---

## Security

| 기술 | 용도 |
|------|------|
| **AWS WAF** | 웹 방화벽 |
| **AWS Secrets Manager** | 시크릿 관리 |
| **AWS KMS** | 암호화 키 관리 |
| **AWS Shield** | DDoS 방어 (Standard) |

---

## Development Tools

### Version Control
| 기술 | 용도 |
|------|------|
| **Git** | 버전 관리 |
| **GitHub** | 코드 호스팅, CI/CD |

### API Documentation
| 기술 | 용도 |
|------|------|
| **Swagger UI** | API 문서 (FastAPI 자동 생성) |
| **Redoc** | API 문서 (대체) |

### 로컬 개발
| 기술 | 용도 |
|------|------|
| **Docker Compose** | 로컬 서비스 실행 |
| **Make** | 태스크 자동화 |

---

## 패키지 매니저

| 언어 | 패키지 매니저 |
|------|-------------|
| **Python** | pip, Poetry (선택) |
| **Go** | Go Modules |
| **Node.js** | pnpm (성능), npm (대체) |

---

## 전체 의존성 파일 예제

### Backend (Python) - `requirements.txt`
```
fastapi==0.100.0
uvicorn[standard]==0.22.0
sqlalchemy==2.0.16
alembic==1.11.1
asyncpg==0.28.0
redis==4.5.5
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
boto3==1.26.150
pydantic==2.0.2
pandas==2.0.2
numpy==1.24.3
ta-lib==0.4.26
pandas-ta==0.3.14
backtrader==1.9.78.123
pytest==7.3.1
pytest-asyncio==0.21.0
httpx==0.24.1
black==23.3.0
flake8==6.0.0
mypy==1.3.0
```

### Frontend (Node.js) - `package.json`
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.11.2",
    "zustand": "^4.3.8",
    "@tanstack/react-query": "^4.29.7",
    "axios": "^1.4.0",
    "socket.io-client": "^4.6.2",
    "react-hook-form": "^7.44.3",
    "zod": "^3.21.4",
    "date-fns": "^2.30.0",
    "lightweight-charts": "^4.0.1",
    "recharts": "^2.6.2",
    "lucide-react": "^0.244.0"
  },
  "devDependencies": {
    "typescript": "^5.0.4",
    "vite": "^4.3.9",
    "@types/react": "^18.2.7",
    "tailwindcss": "^3.3.2",
    "eslint": "^8.42.0",
    "prettier": "^2.8.8"
  }
}
```

---

**문서 종료**
