# AlgoTrader Pro - 시스템 아키텍처 설계

**버전**: 1.0
**작성일**: 2026-05-14
**작성자**: System Architect

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [아키텍처 원칙](#2-아키텍처-원칙)
3. [시스템 구성도](#3-시스템-구성도)
4. [컴포넌트 상세 설계](#4-컴포넌트-상세-설계)
5. [데이터 흐름](#5-데이터-흐름)
6. [확장성 및 성능](#6-확장성-및-성능)
7. [보안 아키텍처](#7-보안-아키텍처)
8. [장애 복구 및 고가용성](#8-장애-복구-및-고가용성)

---

## 1. 아키텍처 개요

### 1.1 아키텍처 스타일
- **마이크로서비스 아키텍처**: 각 기능을 독립적인 서비스로 분리
- **이벤트 드리븐 아키텍처**: 비동기 메시지 큐를 통한 서비스 간 통신
- **서버리스 요소 결합**: Lambda를 활용한 특정 기능 구현

### 1.2 주요 설계 목표
1. **확장성**: 사용자 증가에 따른 수평 확장
2. **안정성**: 99.9% 가용성, 자동 장애 복구
3. **성능**: 100ms 이하 주문 지연
4. **보안**: 금융 수준의 보안 및 암호화
5. **유지보수성**: 모듈화된 설계, CI/CD

---

## 2. 아키텍처 원칙

### 2.1 설계 원칙
1. **단일 책임 원칙**: 각 서비스는 하나의 명확한 책임
2. **느슨한 결합**: 서비스 간 의존성 최소화
3. **장애 격리**: 한 서비스의 장애가 전체 시스템에 영향 최소화
4. **관찰 가능성**: 모든 서비스는 로그, 메트릭, 트레이스 제공
5. **멱등성**: 동일 요청의 반복 실행 시 동일 결과 보장

### 2.2 기술 원칙
1. **클라우드 네이티브**: AWS 관리형 서비스 우선 사용
2. **컨테이너 기반**: 모든 서비스는 Docker 컨테이너로 배포
3. **Infrastructure as Code**: Terraform으로 인프라 관리
4. **자동화**: CI/CD 파이프라인, 자동 스케일링

---

## 3. 시스템 구성도

### 3.1 고수준 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │   CloudFront (CDN)      │
          │   + WAF                 │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   Route 53 (DNS)        │
          └────────────┬────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐         ┌──────────▼────────┐
│  Static Assets │         │   API Gateway      │
│  (S3 + CDN)    │         │   + ALB            │
└────────────────┘         └──────────┬─────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
            ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
            │ Auth Service │  │  User API   │  │  WebSocket  │
            │  (Cognito)   │  │  (FastAPI)  │  │   Service   │
            └──────────────┘  └──────┬──────┘  └──────┬──────┘
                                     │                │
                    ┌────────────────┴────────────────┘
                    │
        ┌───────────┴───────────┐
        │  Message Queue (SQS)  │
        │  Event Bus (SNS)      │
        └───────────┬───────────┘
                    │
    ┌───────────────┼───────────────┬──────────────┐
    │               │               │              │
┌───▼────┐   ┌──────▼──────┐  ┌────▼─────┐  ┌────▼─────┐
│ Market │   │   Strategy  │  │  Order   │  │   Risk   │
│  Data  │   │   Engine    │  │  Exec    │  │  Manager │
│Collector   │  (Python)   │  │(Python)  │  │(Python)  │
│  (Go)  │   └─────────────┘  └──────────┘  └──────────┘
└───┬────┘
    │
    │            ┌──────────────────────────────────┐
    └────────────►  Data Layer                      │
                 │  - RDS PostgreSQL (거래 데이터) │
                 │  - TimescaleDB (시계열 데이터)  │
                 │  - ElastiCache Redis (캐시)     │
                 │  - S3 (로그, 백업)              │
                 └──────────────────────────────────┘
```

### 3.2 배포 아키텍처 (AWS)

```
┌─────────────────── AWS Cloud ────────────────────────────┐
│                                                           │
│  ┌──────────── VPC (10.0.0.0/16) ──────────────┐        │
│  │                                               │        │
│  │  ┌─── Public Subnet (AZ-A) ───┐             │        │
│  │  │  - NAT Gateway              │             │        │
│  │  │  - Application Load Balancer│             │        │
│  │  └─────────────────────────────┘             │        │
│  │                                               │        │
│  │  ┌─── Private Subnet (AZ-A) ──┐             │        │
│  │  │  - ECS Fargate Tasks        │             │        │
│  │  │    * User API (x2)          │             │        │
│  │  │    * Market Data (x2)       │             │        │
│  │  │    * Strategy Engine (x3)   │             │        │
│  │  │    * Order Exec (x2)        │             │        │
│  │  │    * Risk Manager (x1)      │             │        │
│  │  └─────────────────────────────┘             │        │
│  │                                               │        │
│  │  ┌─── Private Subnet (AZ-B) ──┐             │        │
│  │  │  - ECS Fargate Tasks        │             │        │
│  │  │    (동일 구성, HA)          │             │        │
│  │  └─────────────────────────────┘             │        │
│  │                                               │        │
│  │  ┌─── Database Subnet (AZ-A/B) ┐            │        │
│  │  │  - RDS PostgreSQL (Multi-AZ)│            │        │
│  │  │  - ElastiCache Redis Cluster│            │        │
│  │  └─────────────────────────────┘             │        │
│  │                                               │        │
│  └───────────────────────────────────────────────┘        │
│                                                           │
│  ┌─── Managed Services ───┐                             │
│  │  - Cognito (Auth)       │                             │
│  │  - SQS (Message Queue)  │                             │
│  │  - SNS (Notifications)  │                             │
│  │  - CloudWatch (Monitor) │                             │
│  │  - Secrets Manager      │                             │
│  │  - S3 (Storage)         │                             │
│  └─────────────────────────┘                             │
└───────────────────────────────────────────────────────────┘
```

---

## 4. 컴포넌트 상세 설계

### 4.1 Frontend - Web Dashboard

**기술 스택**: React 18 + TypeScript + Vite
**상태 관리**: Zustand
**UI 라이브러리**: shadcn/ui + Tailwind CSS
**차트**: TradingView Lightweight Charts
**WebSocket**: Socket.io-client

**주요 페이지**:
- 대시보드 (실시간 손익, 포지션)
- 전략 관리 (조회, 활성화, 파라미터 설정)
- 거래 이력
- 백테스팅
- 계좌 설정
- 알림 설정

**배포**: S3 + CloudFront (CDN)

---

### 4.2 API Gateway Layer

#### API Gateway (AWS API Gateway)
- REST API 엔드포인트 관리
- Rate Limiting (사용자당 1000 req/min)
- API Key 관리
- 요청/응답 검증

#### Application Load Balancer (ALB)
- HTTPS 트래픽 라우팅
- 헬스 체크
- Sticky Session
- WebSocket 지원

---

### 4.3 Authentication Service

**기술**: AWS Cognito
**기능**:
- 사용자 회원가입/로그인
- JWT 토큰 발급 및 검증
- OAuth 2.0 (소셜 로그인 - Phase 2)
- MFA (2단계 인증 - Phase 2)

**사용자 풀 구성**:
- 이메일 인증 필수
- 비밀번호 정책: 최소 8자, 대소문자, 숫자, 특수문자
- 토큰 만료: Access 1시간, Refresh 30일

---

### 4.4 User API Service

**기술 스택**: Python 3.11 + FastAPI
**배포**: ECS Fargate (2 tasks, Auto Scaling)
**데이터베이스**: RDS PostgreSQL

**책임**:
- 사용자 프로필 관리
- 계좌 연동 관리
- 전략 CRUD
- 주문 조회
- 포지션 조회
- 백테스팅 요청

**API 엔드포인트**: `/api/v1/*` (요구사항 명세서 참조)

**구조**:
```
user-api/
├── app/
│   ├── main.py                 # FastAPI 앱
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── accounts.py
│   │   │   ├── strategies.py
│   │   │   ├── orders.py
│   │   │   └── positions.py
│   ├── core/
│   │   ├── config.py           # 환경 설정
│   │   ├── security.py         # JWT 검증
│   │   └── database.py         # DB 연결
│   ├── models/                 # SQLAlchemy 모델
│   ├── schemas/                # Pydantic 스키마
│   └── services/               # 비즈니스 로직
├── tests/
├── Dockerfile
└── requirements.txt
```

**환경 변수**:
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `REDIS_URL`: Redis 연결 문자열
- `AWS_REGION`: AWS 리전
- `COGNITO_USER_POOL_ID`: Cognito 사용자 풀 ID
- `SECRET_KEY`: JWT 시크릿 키 (Secrets Manager)

---

### 4.5 Market Data Collector Service

**기술 스택**: Go 1.21
**배포**: ECS Fargate (2 tasks)
**데이터베이스**: TimescaleDB (PostgreSQL 확장), Redis

**책임**:
- 증권사 API로부터 실시간 시세 수집
- WebSocket 연결 관리 (KIS, Xing, IB, Alpaca)
- 데이터 정규화 및 저장
- Rate Limiting 관리 (증권사 API 제한 준수)

**지원 데이터**:
- 실시간 호가 (10호가)
- 실시간 체결 (틱 데이터)
- 1분/5분/일봉 OHLCV

**데이터 플로우**:
1. 증권사 WebSocket → Go Collector
2. 데이터 정규화 (공통 포맷)
3. Redis (캐싱, TTL 60초)
4. TimescaleDB (영구 저장)
5. SNS Publish → Strategy Engine (실시간 알림)

**구조**:
```
market-data-collector/
├── cmd/
│   └── collector/
│       └── main.go
├── internal/
│   ├── broker/                 # 증권사별 어댑터
│   │   ├── kis/
│   │   ├── xing/
│   │   ├── ib/
│   │   └── alpaca/
│   ├── normalizer/             # 데이터 정규화
│   ├── storage/                # DB 저장
│   └── config/
├── pkg/
│   └── models/                 # 공통 데이터 모델
├── Dockerfile
└── go.mod
```

**성능 목표**:
- 초당 10,000+ 메시지 처리
- 메모리 사용량 < 512MB
- 지연 시간 < 10ms (수신 ~ 저장)

---

### 4.6 Strategy Engine Service

**기술 스택**: Python 3.11 + NumPy + Pandas + TA-Lib
**배포**: ECS Fargate (3 tasks, Auto Scaling)
**데이터베이스**: PostgreSQL, Redis

**책임**:
- 활성화된 전략 실행
- 기술적 지표 계산
- 매수/매도 신호 생성
- 신호 → Order Queue 전송

**전략 프레임워크**:
```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def on_tick(self, market_data: MarketData) -> Signal:
        """틱 데이터 수신 시 호출"""
        pass

    @abstractmethod
    def on_bar(self, ohlcv: OHLCV) -> Signal:
        """분봉 완성 시 호출"""
        pass

    def calculate_indicators(self, df: pd.DataFrame):
        """기술적 지표 계산"""
        pass
```

**구현된 전략** (MVP):
1. **이동평균 크로스오버**
   - 단기/장기 이동평균선 교차 매매
   - 파라미터: short_period, long_period

2. **RSI 역추세**
   - RSI 과매도/과매수 구간 진입 시 매매
   - 파라미터: rsi_period, oversold, overbought

3. **볼린저 밴드 돌파**
   - 볼린저 밴드 상/하단 돌파 시 매매
   - 파라미터: bb_period, bb_std

**실행 흐름**:
1. Redis Pub/Sub로 실시간 시세 수신
2. 활성화된 사용자 전략 목록 조회 (캐싱)
3. 각 전략에 대해 신호 생성
4. 신호 → SQS Order Queue 전송

**구조**:
```
strategy-engine/
├── app/
│   ├── main.py
│   ├── engine.py               # 전략 실행 엔진
│   ├── strategies/
│   │   ├── base.py
│   │   ├── ma_cross.py
│   │   ├── rsi_reversal.py
│   │   └── bollinger_breakout.py
│   ├── indicators/             # 기술적 지표
│   ├── signals.py              # 신호 정의
│   └── config.py
├── tests/
├── Dockerfile
└── requirements.txt
```

---

### 4.7 Order Execution Service

**기술 스택**: Python 3.11 + ccxt (통합 API 라이브러리)
**배포**: ECS Fargate (2 tasks)
**데이터베이스**: PostgreSQL

**책임**:
- SQS Order Queue에서 주문 요청 수신
- 증권사 API로 주문 전송
- 주문 체결 확인
- 체결 결과 저장
- 포지션 업데이트

**주문 처리 흐름**:
1. SQS 메시지 수신 (주문 요청)
2. 사용자 API 키 조회 (Secrets Manager)
3. 증권사 API 호출 (주문 전송)
4. 주문 ID 저장 (DB)
5. 체결 확인 폴링 (최대 60초)
6. 체결 결과 저장 및 포지션 업데이트
7. SNS 알림 발송 (사용자 알림)

**에러 처리**:
- API 호출 실패 → 재시도 (최대 3회, Exponential Backoff)
- 체결 실패 → 사용자 알림, 로그 기록
- 네트워크 오류 → Circuit Breaker 패턴

**구조**:
```
order-execution/
├── app/
│   ├── main.py
│   ├── executor.py             # 주문 실행 로직
│   ├── brokers/                # 증권사별 어댑터
│   │   ├── kis_adapter.py
│   │   ├── xing_adapter.py
│   │   ├── ib_adapter.py
│   │   └── alpaca_adapter.py
│   ├── models.py               # DB 모델
│   └── config.py
├── tests/
├── Dockerfile
└── requirements.txt
```

---

### 4.8 Risk Manager Service

**기술 스택**: Python 3.11
**배포**: ECS Fargate (1 task)
**데이터베이스**: PostgreSQL, Redis

**책임**:
- 포지션 실시간 모니터링
- 손절/익절 조건 체크
- 일일 손실 한도 체크
- 포지션 크기 제한 체크
- 리스크 이벤트 → Order Queue (청산 주문)

**모니터링 주기**: 1초

**체크 항목**:
1. **개별 포지션**:
   - 손절가 도달 → 즉시 청산
   - 익절가 도달 → 즉시 청산
   - 트레일링 스톱 업데이트

2. **계좌 전체**:
   - 일일 손실 > -3% → 모든 거래 중단
   - 투자 비율 > 90% → 신규 진입 차단
   - 동시 포지션 수 > 제한 → 신규 진입 차단

3. **시장 리스크**:
   - VIX > 40 → 경고 알림
   - 서킷 브레이커 → 모든 주문 취소

**구조**:
```
risk-manager/
├── app/
│   ├── main.py
│   ├── monitor.py              # 실시간 모니터링
│   ├── rules/                  # 리스크 규칙
│   │   ├── stop_loss.py
│   │   ├── take_profit.py
│   │   ├── daily_loss_limit.py
│   │   └── position_sizing.py
│   ├── actions.py              # 리스크 조치
│   └── config.py
├── tests/
├── Dockerfile
└── requirements.txt
```

---

### 4.9 WebSocket Service

**기술 스택**: Python 3.11 + FastAPI + WebSocket
**배포**: ECS Fargate (2 tasks, Sticky Session)
**데이터베이스**: Redis (Pub/Sub)

**책임**:
- 클라이언트 WebSocket 연결 관리
- 실시간 데이터 푸시 (포지션, 손익, 주문 체결 등)
- Redis Pub/Sub 구독

**데이터 스트림**:
- `account_balance`: 계좌 잔고 변경
- `positions`: 포지션 업데이트
- `orders`: 주문 상태 변경
- `pnl`: 손익 업데이트

**연결 플로우**:
1. 클라이언트 WebSocket 연결 요청 (`wss://api.../ws/realtime?token=...`)
2. JWT 토큰 검증
3. 사용자 ID 추출
4. Redis Pub/Sub 구독 (`user:{user_id}:*`)
5. 실시간 이벤트 → 클라이언트 푸시

---

### 4.10 Backtesting Engine

**기술 스택**: Python 3.11 + Backtrader
**배포**: AWS Lambda (on-demand)
**데이터베이스**: TimescaleDB (과거 데이터)

**책임**:
- 백테스팅 요청 처리 (SQS)
- 과거 데이터 조회
- 전략 시뮬레이션
- 성과 지표 계산
- 결과 저장 (S3 + DB)

**실행 흐름**:
1. 사용자가 백테스팅 요청 (User API)
2. SQS 메시지 전송
3. Lambda 트리거
4. 과거 데이터 조회 (TimescaleDB)
5. Backtrader 실행
6. 결과 계산 및 저장
7. SNS 알림 (완료 통지)

**성과 지표**:
- 총 수익률, CAGR, 샤프 비율, 최대 낙폭, 승률, 손익비

---

## 5. 데이터 흐름

### 5.1 실시간 거래 흐름

```
1. 시장 데이터 수집
┌──────────────┐
│ 증권사 API   │
│ (WebSocket)  │
└───────┬──────┘
        │ 실시간 시세
        ▼
┌──────────────┐
│ Market Data  │
│  Collector   │
└───┬──────┬───┘
    │      │
    │      └─────► TimescaleDB (영구 저장)
    │
    ▼
  Redis ────────────┐
 (Cache)            │
                    │
2. 전략 실행        │
                    ▼
            ┌───────────────┐
            │ Strategy      │
            │  Engine       │◄── PostgreSQL (사용자 전략)
            └───────┬───────┘
                    │ 매수/매도 신호
                    ▼
                  SQS
              (Order Queue)
                    │
3. 주문 실행        │
                    ▼
            ┌───────────────┐
            │ Order         │
            │ Execution     │
            └───────┬───────┘
                    │ 주문 전송
                    ▼
            ┌───────────────┐
            │ 증권사 API    │
            │ (주문)        │
            └───────┬───────┘
                    │ 체결 결과
                    ▼
            ┌───────────────┐
            │ PostgreSQL    │
            │ (Orders,      │
            │  Positions)   │
            └───────┬───────┘
                    │
4. 실시간 업데이트  │
                    ▼
              Redis Pub/Sub
                    │
                    ▼
            ┌───────────────┐
            │ WebSocket     │
            │  Service      │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Web Client   │
            └───────────────┘
```

### 5.2 백테스팅 흐름

```
User API ──► SQS ──► Lambda (Backtesting Engine)
                        │
                        ├──► TimescaleDB (과거 데이터)
                        │
                        ├──► S3 (결과 저장)
                        │
                        └──► PostgreSQL (결과 메타데이터)
                        │
                        └──► SNS ──► User (알림)
```

---

## 6. 확장성 및 성능

### 6.1 수평 확장 전략

| 컴포넌트 | 확장 방식 | 트리거 |
|---------|----------|--------|
| User API | ECS Auto Scaling | CPU > 70% 또는 요청 수 > 1000/min |
| Market Data Collector | 수동 스케일링 | 모니터링 종목 수 증가 시 |
| Strategy Engine | ECS Auto Scaling | 활성 전략 수 > 500개/task |
| Order Execution | ECS Auto Scaling | SQS 대기 메시지 > 100개 |
| WebSocket Service | ECS Auto Scaling | 연결 수 > 500/task |

### 6.2 캐싱 전략

**Redis 캐싱**:
- 실시간 시세 (TTL: 60초)
- 사용자 세션 (TTL: 1시간)
- 활성 전략 목록 (TTL: 5분)
- API 응답 (TTL: 30초)

**CloudFront 캐싱**:
- 정적 자산 (HTML, JS, CSS) - TTL: 1일
- 이미지, 폰트 - TTL: 7일

### 6.3 데이터베이스 최적화

**RDS PostgreSQL**:
- 인스턴스: db.r6g.xlarge (4 vCPU, 32GB RAM)
- Multi-AZ 배포
- 읽기 복제본 1개 (읽기 부하 분산)
- 커넥션 풀: 최대 100개

**TimescaleDB**:
- Hypertable 파티셔닝 (1일 단위)
- 데이터 압축 (7일 이후)
- 자동 데이터 삭제 (1년 이후)

**ElastiCache Redis**:
- 클러스터 모드: 3 샤드 x 2 복제본
- 인스턴스: cache.r6g.large (2 vCPU, 13GB RAM)

---

## 7. 보안 아키텍처

### 7.1 네트워크 보안

```
Internet
   │
   ├─► CloudFront + WAF (DDoS 방어, SQL Injection 차단)
   │
   ├─► Route 53
   │
   └─► ALB (HTTPS only, TLS 1.3)
       │
       └─► VPC
           ├─► Public Subnet (NAT Gateway)
           │
           └─► Private Subnet (ECS Tasks)
               │
               └─► Database Subnet (RDS, Redis)
                   - Security Group: Private Subnet에서만 접근 가능
```

**Security Group 규칙**:
- ALB SG: 0.0.0.0/0 → 443 (HTTPS)
- ECS SG: ALB SG → 8000 (FastAPI)
- RDS SG: ECS SG → 5432 (PostgreSQL)
- Redis SG: ECS SG → 6379

### 7.2 인증 및 권한

**인증 플로우**:
1. 사용자 로그인 → Cognito
2. Cognito → JWT 토큰 발급 (Access + Refresh)
3. 클라이언트 → API 요청 (Authorization: Bearer {token})
4. API Gateway → JWT 검증
5. User API → 요청 처리

**권한 (RBAC)**:
- `admin`: 모든 기능 접근
- `premium_user`: 무제한 전략, 백테스팅
- `pro_user`: 5개 전략, 월 50회 백테스팅
- `basic_user`: 2개 전략, 월 10회 백테스팅

### 7.3 데이터 암호화

**전송 중 암호화**:
- HTTPS/TLS 1.3 (모든 API 통신)
- WebSocket Secure (WSS)

**저장 데이터 암호화**:
- RDS: AES-256 암호화 활성화
- S3: Server-Side Encryption (SSE-S3)
- Secrets Manager: API 키, DB 비밀번호

### 7.4 API 보안

**Rate Limiting**:
- API Gateway: 사용자당 1000 req/min
- 플랜별 제한 (Basic: 1000, Pro: 5000, Premium: 10000)

**입력 검증**:
- Pydantic 스키마 검증
- SQL Injection 방지 (Prepared Statement)
- XSS 방지 (입력 Sanitization)

---

## 8. 장애 복구 및 고가용성

### 8.1 고가용성 설계

**Multi-AZ 배포**:
- ECS Tasks: 2개 이상 AZ에 분산
- RDS: Multi-AZ 자동 Failover
- Redis: 클러스터 모드 (복제본)

**헬스 체크**:
- ALB Target Health Check (30초 간격)
- ECS Task Health Check (10초 간격)
- RDS Automated Health Monitoring

**자동 복구**:
- ECS Task 실패 → 자동 재시작
- RDS 장애 → Multi-AZ Failover (< 2분)
- Redis 노드 장애 → 복제본 승격

### 8.2 장애 시나리오 및 대응

| 장애 시나리오 | 영향 | 대응 | RTO |
|-------------|------|-----|-----|
| ECS Task 장애 | 해당 서비스 일시 중단 | 자동 재시작 | < 1분 |
| RDS 주 DB 장애 | DB 쓰기 중단 | Multi-AZ Failover | < 2분 |
| Redis 장애 | 캐시 미스, 성능 저하 | 복제본 승격 | < 1분 |
| AZ 전체 장애 | 50% 용량 감소 | 남은 AZ로 트래픽 전환 | < 5분 |
| 증권사 API 장애 | 해당 시장 거래 중단 | Circuit Breaker, 사용자 알림 | N/A |

### 8.3 백업 및 복구

**데이터베이스 백업**:
- RDS 자동 백업: 일 1회 (03:00 UTC)
- 백업 보관: 30일
- 수동 스냅샷: 주요 배포 전

**로그 백업**:
- CloudWatch Logs → S3 (30일 후)
- S3 Glacier (1년 후)
- 보관 기간: 5년

**복구 절차**:
1. RDS 스냅샷에서 복원
2. DNS 전환 (Route 53)
3. 애플리케이션 재배포
4. 검증 및 서비스 재개

**RTO/RPO 목표**:
- RTO (목표 복구 시간): 1시간
- RPO (목표 복구 시점): 24시간 (일 백업)

---

## 부록

### A. 기술 스택 요약

| 계층 | 기술 |
|------|------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| API Gateway | AWS API Gateway, ALB |
| Backend | Python 3.11, FastAPI, Go 1.21 |
| Database | PostgreSQL 15, TimescaleDB, Redis 7 |
| Message Queue | AWS SQS, SNS |
| Container | Docker, ECS Fargate |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Monitoring | CloudWatch, CloudWatch Logs Insights |
| CDN | CloudFront |
| DNS | Route 53 |
| Auth | AWS Cognito |
| Secrets | AWS Secrets Manager |

### B. 리소스 예상 비용 (월)

| 서비스 | 스펙 | 월 비용 (USD) |
|--------|------|-------------|
| ECS Fargate | 10 tasks (2 vCPU, 4GB) | $800 |
| RDS PostgreSQL | db.r6g.xlarge (Multi-AZ) | $400 |
| ElastiCache Redis | 3샤드 x 2복제 (cache.r6g.large) | $500 |
| ALB | 1개 | $30 |
| NAT Gateway | 2개 (Multi-AZ) | $90 |
| CloudWatch | 로그, 메트릭 | $200 |
| S3 | 100GB (로그, 백업) | $30 |
| 기타 (API Gateway, SNS, SQS) | - | $150 |
| **총 예상 비용** | | **$2,200/월** |

실제 비용은 사용자 수, 거래량, 데이터 전송량에 따라 변동

---

**문서 종료**
