# AlgoTrader Pro - 요구사항 명세서 (Requirements Specification)

**버전**: 1.0
**작성일**: 2026-05-14
**프로젝트**: 멀티마켓 자동 트레이딩 SaaS 플랫폼
**상태**: Draft

---

## 목차

1. [소개](#1-소개)
2. [시스템 개요](#2-시스템-개요)
3. [기능 요구사항](#3-기능-요구사항)
4. [비기능 요구사항](#4-비기능-요구사항)
5. [사용자 유스케이스](#5-사용자-유스케이스)
6. [API 명세](#6-api-명세)
7. [데이터 요구사항](#7-데이터-요구사항)
8. [제약사항](#8-제약사항)

---

## 1. 소개

### 1.1 목적
본 문서는 **AlgoTrader Pro** 자동 트레이딩 SaaS 플랫폼의 상세 요구사항을 정의합니다. 이 문서는 개발팀, 퀀트 팀, 이해관계자 간의 공통 이해를 위한 기준 문서입니다.

### 1.2 범위
- **대상 시장**: 한국 주식시장 (KOSPI/KOSDAQ), 미국 주식시장 (NYSE/NASDAQ)
- **대상 사용자**: 개인 투자자, 퀀트 트레이더
- **서비스 규모**: 중규모 (100-1,000명 동시 사용자)
- **배포 환경**: AWS 클라우드

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| **전략 (Strategy)** | 주식 매매를 결정하는 알고리즘 규칙 세트 |
| **포지션 (Position)** | 현재 보유 중인 주식 |
| **백테스팅 (Backtesting)** | 과거 데이터로 전략 성과를 시뮬레이션 |
| **Paper Trading** | 실제 자금 없이 모의 거래 |
| **OHLCV** | Open, High, Low, Close, Volume (시가, 고가, 저가, 종가, 거래량) |
| **Slippage** | 주문가와 실제 체결가의 차이 |
| **PnL (Profit and Loss)** | 손익 |
| **SaaS** | Software as a Service |

---

## 2. 시스템 개요

### 2.1 시스템 목표
1. **안정성**: 99.9% 가용성, 자동 복구 기능
2. **성능**: 100ms 이하 주문 지연시간
3. **확장성**: 1,000명 동시 사용자 지원
4. **보안**: 금융 수준의 보안 및 규제 준수
5. **사용성**: 직관적인 웹 대시보드

### 2.2 고수준 아키텍처

```
┌─────────────────┐
│  Web Dashboard  │ (React + TypeScript)
└────────┬────────┘
         │ HTTPS/WSS
┌────────▼────────┐
│  API Gateway    │ (AWS API Gateway + ALB)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼───┐
│ Auth  │ │ User │
│Service│ │ API  │ (FastAPI)
└───────┘ └──┬───┘
             │
    ┌────────┼────────┐
    │        │        │
┌───▼──┐ ┌──▼───┐ ┌─▼────┐
│Market│ │Order │ │Risk  │
│Data  │ │Exec  │ │Mgmt  │
└───┬──┘ └──┬───┘ └──┬───┘
    │       │        │
┌───▼───────▼────────▼───┐
│   Message Queue (SQS)  │
└────────────────────────┘
         │
┌────────▼────────┐
│Strategy Engine  │ (Python)
└────────┬────────┘
         │
┌────────▼────────┐
│   Databases     │ (RDS, Redis, TimescaleDB)
└─────────────────┘
```

---

## 3. 기능 요구사항

### 3.1 사용자 관리

#### FR-001: 사용자 회원가입
- **우선순위**: P0 (필수)
- **설명**: 사용자는 이메일과 비밀번호로 회원가입할 수 있어야 함
- **요구사항**:
  - 이메일 인증 필수
  - 비밀번호 강도 검증 (최소 8자, 대소문자, 숫자, 특수문자 포함)
  - 이용약관 및 개인정보 처리방침 동의
  - 투자 리스크 고지 확인
- **성공 기준**: 회원가입 후 인증 이메일 발송, 인증 완료 시 로그인 가능

#### FR-002: 사용자 로그인/로그아웃
- **우선순위**: P0
- **설명**: JWT 토큰 기반 인증
- **요구사항**:
  - 이메일/비밀번호 로그인
  - 소셜 로그인 (Google, Kakao) - Phase 2
  - MFA (2단계 인증) - Phase 2
  - 토큰 만료 시간: Access Token 1시간, Refresh Token 30일

#### FR-003: 사용자 프로필 관리
- **우선순위**: P1
- **설명**: 사용자 정보 조회/수정
- **요구사항**:
  - 프로필 정보: 이름, 연락처, 알림 설정
  - 비밀번호 변경
  - 계정 삭제 (GDPR 준수)

### 3.2 계좌 관리

#### FR-010: 증권 계좌 연동
- **우선순위**: P0
- **설명**: 사용자는 증권사 API 키를 등록하여 계좌를 연동할 수 있어야 함
- **요구사항**:
  - 지원 증권사:
    - 한국: 한국투자증권 (KIS API), 이베스트투자증권 (Xing API)
    - 미국: Interactive Brokers (IB API), Alpaca Markets
  - API 키/시크릿 암호화 저장 (AWS Secrets Manager)
  - 연결 테스트 기능
  - 다중 계좌 지원 (사용자당 최대 5개)
- **성공 기준**: API 연결 성공, 계좌 잔고 조회 가능

#### FR-011: 계좌 잔고 조회
- **우선순위**: P0
- **설명**: 실시간 계좌 잔고 및 보유 종목 조회
- **요구사항**:
  - 현금 잔고
  - 보유 종목 목록 (종목명, 수량, 평균 단가, 현재가, 평가 손익)
  - 총 자산 평가액
  - 실시간 업데이트 (WebSocket)

### 3.3 전략 관리

#### FR-020: 전략 조회
- **우선순위**: P0
- **설명**: 사용자는 사용 가능한 거래 전략 목록을 조회할 수 있어야 함
- **요구사항**:
  - 전략 목록 (이름, 설명, 백테스팅 성과)
  - 전략 상세 정보 (파라미터, 적용 시장, 권장 자금)
  - 전략 카테고리 (추세 추종, 평균 회귀, 모멘텀 등)

#### FR-021: 전략 활성화/비활성화
- **우선순위**: P0
- **설명**: 사용자는 원하는 전략을 선택하여 활성화/비활성화할 수 있어야 함
- **요구사항**:
  - 전략별 on/off 토글
  - 활성화 시 즉시 실시간 거래 시작
  - 비활성화 시 기존 포지션 처리 옵션:
    - 즉시 청산
    - 보유 (자동 거래만 중단)
  - 동시 활성화 가능 전략 수 제한 (플랜별)

#### FR-022: 전략 파라미터 설정
- **우선순위**: P0
- **설명**: 사용자는 전략 파라미터를 조정할 수 있어야 함
- **요구사항**:
  - 공통 파라미터:
    - 투자 금액 (종목당)
    - 손절 비율 (-2% 기본값)
    - 익절 비율 (+3% 기본값)
    - 최대 동시 보유 종목 수
  - 전략별 고유 파라미터:
    - 이동평균 기간 (예: 5, 20, 60일)
    - RSI 임계값 (예: 30/70)
  - 파라미터 검증 (범위 체크)
  - 변경 이력 저장

#### FR-023: 백테스팅 실행
- **우선순위**: P1
- **설명**: 사용자는 전략을 과거 데이터로 백테스팅할 수 있어야 함
- **요구사항**:
  - 백테스팅 기간 선택 (시작일, 종료일)
  - 초기 자금 설정
  - 슬리피지, 수수료 반영
  - 백테스팅 결과:
    - 총 수익률, 연환산 수익률
    - 최대 낙폭 (MDD)
    - 샤프 비율, 소르티노 비율
    - 승률, 손익비
    - 거래 횟수, 평균 보유 기간
    - 손익 곡선 차트
  - 백테스팅 결과 저장/공유

### 3.4 거래 실행

#### FR-030: 자동 거래 실행
- **우선순위**: P0
- **설명**: 활성화된 전략에 따라 자동으로 매매 주문을 생성/실행
- **요구사항**:
  - 실시간 시장 데이터 기반 의사결정
  - 매수/매도 신호 생성
  - 자동 주문 생성 및 전송
  - 주문 유형:
    - 시장가 주문
    - 지정가 주문
    - 조건부 주문 (손절/익절)
  - 주문 체결 확인
  - 체결 실패 시 재시도 로직

#### FR-031: 수동 거래
- **우선순위**: P1
- **설명**: 사용자는 대시보드에서 수동으로 주문을 낼 수 있어야 함
- **요구사항**:
  - 종목 검색
  - 매수/매도 선택
  - 수량, 가격 입력
  - 주문 확인 팝업
  - 주문 취소 기능

#### FR-032: 포지션 관리
- **우선순위**: P0
- **설명**: 현재 보유 포지션 조회 및 관리
- **요구사항**:
  - 포지션 목록 (종목, 진입가, 수량, 현재가, 손익률, 평가액)
  - 실시간 손익 업데이트
  - 개별 포지션 수동 청산
  - 전체 포지션 일괄 청산 (긴급 상황)

### 3.5 리스크 관리

#### FR-040: 자동 손절/익절
- **우선순위**: P0
- **설명**: 설정된 손절/익절 비율에 도달 시 자동 청산
- **요구사항**:
  - 포지션별 손절/익절 비율 설정
  - 실시간 가격 모니터링
  - 손절/익절 조건 충족 시 즉시 시장가 청산
  - 청산 결과 알림

#### FR-041: 일일 손실 한도
- **우선순위**: P0
- **설명**: 일일 손실이 설정 한도에 도달하면 모든 거래 중단
- **요구사항**:
  - 일일 손실 한도 설정 (기본값: -3%)
  - 실현 손익 + 미실현 손익 합산
  - 한도 도달 시:
    - 모든 신규 주문 차단
    - 기존 포지션 유지 또는 청산 (사용자 선택)
    - 긴급 알림 발송
  - 다음 거래일 자동 리셋

#### FR-042: 포지션 크기 제한
- **우선순위**: P0
- **설명**: 종목별/전체 포지션 크기 제한
- **요구사항**:
  - 종목당 최대 투자 비율 (기본값: 20%)
  - 전체 투자 비율 (기본값: 90%, 10% 현금 보유)
  - 동시 보유 종목 수 제한 (플랜별)

### 3.6 모니터링 및 알림

#### FR-050: 실시간 대시보드
- **우선순위**: P0
- **설명**: 웹 기반 실시간 모니터링 대시보드
- **요구사항**:
  - 주요 지표:
    - 오늘의 손익 (금액, %)
    - 총 자산 평가액
    - 활성 포지션 수
    - 오늘의 거래 횟수
  - 손익 차트 (일/주/월)
  - 활성 전략 상태
  - 최근 거래 내역
  - 시스템 상태 (API 연결, 서버 상태)

#### FR-051: 알림 설정
- **우선순위**: P1
- **설명**: 사용자는 다양한 이벤트에 대한 알림을 설정할 수 있어야 함
- **요구사항**:
  - 알림 채널:
    - 이메일
    - 텔레그램 (봇 연동)
    - 웹 푸시
  - 알림 이벤트:
    - 주문 체결
    - 손절/익절 실행
    - 일일 손실 한도 도달
    - 전략 활성화/비활성화
    - 시스템 오류
  - 알림 on/off 개별 설정

#### FR-052: 거래 이력 조회
- **우선순위**: P1
- **설명**: 과거 거래 내역 조회 및 분석
- **요구사항**:
  - 거래 이력 테이블 (날짜, 종목, 매수/매도, 수량, 가격, 손익)
  - 필터링 (기간, 종목, 전략, 수익/손실)
  - 정렬 (날짜, 손익 등)
  - CSV/Excel 다운로드
  - 통계 요약 (총 거래 횟수, 승률, 평균 손익 등)

### 3.7 관리자 기능

#### FR-060: 사용자 관리
- **우선순위**: P1
- **설명**: 관리자는 사용자를 관리할 수 있어야 함
- **요구사항**:
  - 사용자 목록 조회
  - 사용자 상세 정보 조회
  - 사용자 계정 활성화/비활성화
  - 플랜 변경
  - 강제 전략 중단 (비정상 거래 감지 시)

#### FR-061: 시스템 모니터링
- **우선순위**: P0
- **설명**: 관리자는 전체 시스템 상태를 모니터링할 수 있어야 함
- **요구사항**:
  - 서버 상태 (CPU, 메모리, 네트워크)
  - 데이터베이스 상태
  - API 연결 상태
  - 에러 로그
  - 사용자 활동 통계

---

## 4. 비기능 요구사항

### 4.1 성능

#### NFR-001: 응답 시간
- API 응답 시간: 95th percentile < 200ms
- 주문 실행 지연: < 100ms (신호 생성 ~ 주문 전송)
- 대시보드 로딩 시간: < 2초

#### NFR-002: 처리량
- 시장 데이터 수신: 초당 10,000+ 메시지
- 동시 사용자: 1,000명
- 동시 활성 전략: 5,000개

#### NFR-003: 확장성
- 수평 확장 가능 (ECS Auto Scaling)
- 데이터베이스 읽기 복제본 지원
- 캐싱 레이어 (Redis)

### 4.2 가용성

#### NFR-010: 시스템 가용성
- 목표: 99.9% (월 43분 다운타임)
- Multi-AZ 배포
- 자동 장애 조치 (Failover)
- 헬스 체크 및 자동 재시작

#### NFR-011: 데이터 내구성
- 데이터베이스 자동 백업 (일 1회)
- 백업 보관 기간: 30일
- 거래 로그 S3 저장 (5년)

### 4.3 보안

#### NFR-020: 인증 및 권한
- JWT 기반 인증
- Role-based Access Control (RBAC)
- API Rate Limiting (사용자당 1000 req/min)

#### NFR-021: 데이터 암호화
- 전송 중 암호화: TLS 1.3
- 저장 데이터 암호화: AES-256
- API 키 암호화 저장

#### NFR-022: 규제 준수
- GDPR 준수 (데이터 삭제 권리)
- 개인정보보호법 준수
- 금융 거래 로그 보관 (5년)

### 4.4 모니터링 및 로깅

#### NFR-030: 로깅
- 구조화된 로그 (JSON)
- 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
- 중앙 로그 수집 (CloudWatch Logs)
- 로그 검색 및 분석 (CloudWatch Logs Insights)

#### NFR-031: 모니터링
- 시스템 메트릭 (CPU, 메모리, 네트워크)
- 애플리케이션 메트릭 (요청 수, 에러율, 지연시간)
- 비즈니스 메트릭 (거래 횟수, 손익)
- 알림 임계값 설정

### 4.5 유지보수성

#### NFR-040: 코드 품질
- 단위 테스트 커버리지 > 80%
- 코드 리뷰 필수
- 정적 분석 도구 (Pylint, MyPy)

#### NFR-041: 배포
- CI/CD 파이프라인 (GitHub Actions)
- 무중단 배포 (Blue-Green)
- 롤백 가능

---

## 5. 사용자 유스케이스

### UC-001: 신규 사용자 온보딩

**Actor**: 신규 사용자
**목적**: 회원가입 후 첫 거래 시작까지
**선행조건**: 없음

**흐름**:
1. 사용자가 웹사이트 접속
2. 회원가입 (이메일, 비밀번호)
3. 이메일 인증
4. 로그인
5. 플랜 선택 (Basic/Pro/Premium)
6. 결제 (Stripe)
7. 증권사 API 키 등록
8. 계좌 연동 확인
9. 전략 선택 및 파라미터 설정
10. 백테스팅 실행 (선택)
11. 전략 활성화
12. 자동 거래 시작

**후행조건**: 사용자 계정 활성화, 자동 거래 실행 중

---

### UC-002: 일일 거래 모니터링

**Actor**: 활성 사용자
**목적**: 오늘의 거래 활동 확인
**선행조건**: 로그인, 활성화된 전략 존재

**흐름**:
1. 대시보드 접속
2. 오늘의 손익 확인
3. 활성 포지션 조회
4. 최근 거래 내역 확인
5. 전략 성과 확인
6. 필요 시 전략 비활성화 또는 파라미터 조정

**후행조건**: 없음

---

### UC-003: 긴급 상황 대응

**Actor**: 사용자
**목적**: 급격한 손실 발생 시 대응
**선행조건**: 활성 포지션 존재, 손실 발생 중

**흐름**:
1. 손실 한도 도달 알림 수신
2. 대시보드 긴급 접속
3. 현재 상황 확인 (손익, 포지션)
4. 조치 선택:
   - Option A: 전체 포지션 일괄 청산
   - Option B: 개별 포지션 선택 청산
   - Option C: 전략만 비활성화 (포지션 유지)
5. 청산 확인
6. 전략 재검토 및 파라미터 조정

**후행조건**: 포지션 청산 완료 또는 전략 비활성화

---

## 6. API 명세

### 6.1 인증 API

#### POST /api/v1/auth/register
회원가입

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "홍길동",
  "agreed_to_terms": true
}
```

**Response** (201 Created):
```json
{
  "user_id": "usr_1234567890",
  "email": "user@example.com",
  "message": "인증 이메일이 발송되었습니다."
}
```

---

#### POST /api/v1/auth/login
로그인

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 6.2 계좌 API

#### POST /api/v1/accounts
증권 계좌 연동

**Request Header**:
```
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "broker": "kis", // kis, xing, ib, alpaca
  "account_number": "12345678",
  "api_key": "api_key_here",
  "api_secret": "api_secret_here",
  "market": "kr" // kr, us
}
```

**Response** (201 Created):
```json
{
  "account_id": "acc_1234567890",
  "broker": "kis",
  "account_number": "12345678",
  "market": "kr",
  "status": "connected",
  "created_at": "2026-05-14T10:00:00Z"
}
```

---

#### GET /api/v1/accounts/{account_id}/balance
계좌 잔고 조회

**Response** (200 OK):
```json
{
  "account_id": "acc_1234567890",
  "cash_balance": 5000000,
  "stock_value": 3000000,
  "total_value": 8000000,
  "currency": "KRW",
  "positions": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "quantity": 100,
      "avg_price": 70000,
      "current_price": 72000,
      "unrealized_pnl": 200000,
      "unrealized_pnl_percent": 2.86
    }
  ],
  "updated_at": "2026-05-14T15:30:00Z"
}
```

---

### 6.3 전략 API

#### GET /api/v1/strategies
전략 목록 조회

**Response** (200 OK):
```json
{
  "strategies": [
    {
      "strategy_id": "strat_ma_cross",
      "name": "이동평균 크로스",
      "description": "단기/장기 이동평균선 교차 전략",
      "category": "trend_following",
      "markets": ["kr", "us"],
      "backtesting_results": {
        "total_return": 45.2,
        "sharpe_ratio": 1.8,
        "max_drawdown": -12.3,
        "win_rate": 62.5
      },
      "parameters": [
        {
          "name": "short_period",
          "label": "단기 이동평균 기간",
          "type": "integer",
          "default": 5,
          "min": 3,
          "max": 20
        },
        {
          "name": "long_period",
          "label": "장기 이동평균 기간",
          "type": "integer",
          "default": 20,
          "min": 10,
          "max": 100
        }
      ]
    }
  ]
}
```

---

#### POST /api/v1/user-strategies
사용자 전략 활성화

**Request Body**:
```json
{
  "strategy_id": "strat_ma_cross",
  "account_id": "acc_1234567890",
  "parameters": {
    "short_period": 5,
    "long_period": 20,
    "investment_amount": 1000000,
    "stop_loss_percent": 2.0,
    "take_profit_percent": 3.0,
    "max_positions": 5
  },
  "enabled": true
}
```

**Response** (201 Created):
```json
{
  "user_strategy_id": "ustrat_1234567890",
  "strategy_id": "strat_ma_cross",
  "account_id": "acc_1234567890",
  "status": "active",
  "created_at": "2026-05-14T10:00:00Z"
}
```

---

### 6.4 주문 API

#### POST /api/v1/orders
수동 주문 생성

**Request Body**:
```json
{
  "account_id": "acc_1234567890",
  "symbol": "005930",
  "side": "buy", // buy, sell
  "order_type": "market", // market, limit
  "quantity": 10,
  "price": 72000 // limit order only
}
```

**Response** (201 Created):
```json
{
  "order_id": "ord_1234567890",
  "account_id": "acc_1234567890",
  "symbol": "005930",
  "side": "buy",
  "order_type": "market",
  "quantity": 10,
  "status": "pending",
  "created_at": "2026-05-14T15:30:00Z"
}
```

---

#### GET /api/v1/orders/{order_id}
주문 상태 조회

**Response** (200 OK):
```json
{
  "order_id": "ord_1234567890",
  "status": "filled", // pending, filled, partially_filled, cancelled, rejected
  "filled_quantity": 10,
  "filled_price": 72100,
  "filled_at": "2026-05-14T15:30:05Z"
}
```

---

### 6.5 포지션 API

#### GET /api/v1/positions
포지션 목록 조회

**Response** (200 OK):
```json
{
  "positions": [
    {
      "position_id": "pos_1234567890",
      "account_id": "acc_1234567890",
      "symbol": "005930",
      "name": "삼성전자",
      "quantity": 10,
      "avg_entry_price": 72100,
      "current_price": 73000,
      "unrealized_pnl": 9000,
      "unrealized_pnl_percent": 1.25,
      "stop_loss_price": 70657,
      "take_profit_price": 74283,
      "strategy_id": "strat_ma_cross",
      "opened_at": "2026-05-14T15:30:05Z"
    }
  ]
}
```

---

### 6.6 WebSocket API

#### WS /api/v1/ws/realtime
실시간 데이터 스트리밍

**Connection**:
```
wss://api.algotrader.pro/v1/ws/realtime?token={access_token}
```

**Subscribe Message**:
```json
{
  "action": "subscribe",
  "channels": ["account_balance", "positions", "orders", "pnl"]
}
```

**Position Update Event**:
```json
{
  "event": "position_update",
  "data": {
    "position_id": "pos_1234567890",
    "current_price": 73500,
    "unrealized_pnl": 14000,
    "unrealized_pnl_percent": 1.94
  },
  "timestamp": "2026-05-14T15:31:00Z"
}
```

---

## 7. 데이터 요구사항

### 7.1 데이터 모델

#### 사용자 (Users)
- user_id (PK)
- email (unique)
- password_hash
- name
- plan (basic, pro, premium)
- created_at
- updated_at

#### 계좌 (Accounts)
- account_id (PK)
- user_id (FK)
- broker
- account_number
- market
- api_key_encrypted
- status
- created_at

#### 전략 (Strategies)
- strategy_id (PK)
- name
- description
- category
- code_path
- parameters_schema (JSON)
- created_at

#### 사용자 전략 (UserStrategies)
- user_strategy_id (PK)
- user_id (FK)
- strategy_id (FK)
- account_id (FK)
- parameters (JSON)
- enabled
- created_at
- updated_at

#### 주문 (Orders)
- order_id (PK)
- account_id (FK)
- user_strategy_id (FK, nullable)
- symbol
- side (buy/sell)
- order_type
- quantity
- price
- status
- filled_quantity
- filled_price
- created_at
- updated_at

#### 포지션 (Positions)
- position_id (PK)
- account_id (FK)
- user_strategy_id (FK)
- symbol
- quantity
- avg_entry_price
- stop_loss_price
- take_profit_price
- opened_at
- closed_at

#### 시장 데이터 (MarketData) - TimescaleDB
- timestamp (PK)
- symbol (PK)
- market
- open
- high
- low
- close
- volume
- interval (1m, 5m, 1d 등)

### 7.2 데이터 보관 정책

| 데이터 유형 | 보관 기간 | 저장소 |
|------------|----------|--------|
| 실시간 시세 | 1일 | Redis |
| 분봉 데이터 | 1년 | TimescaleDB |
| 일봉 데이터 | 10년 | TimescaleDB |
| 거래 이력 | 5년 | RDS → S3 Glacier |
| 로그 | 30일 (hot), 5년 (cold) | CloudWatch → S3 |
| 백업 | 30일 | RDS Backups |

---

## 8. 제약사항

### 8.1 기술적 제약
1. **증권사 API 제한**
   - KIS API: 초당 20건
   - Xing API: 초당 10건
   - IB API: 초당 50건
   - Alpaca: 초당 200건

2. **AWS 리소스 제한**
   - ECS Task 수: 계정당 2,000개
   - RDS 연결 수: 최대 100 (db.t3.medium)

### 8.2 비즈니스 제약
1. **플랜별 제한**

| 기능 | Basic | Pro | Premium |
|------|-------|-----|---------|
| 동시 활성 전략 | 2개 | 5개 | 무제한 |
| 동시 보유 종목 | 5개 | 10개 | 20개 |
| 백테스팅 실행 | 월 10회 | 월 50회 | 무제한 |
| API 호출 | 1000/분 | 5000/분 | 10000/분 |

2. **거래 제한**
   - 최소 주문 금액: 1만원 (KR), $10 (US)
   - 최대 주문 금액: 계좌 잔고의 20%

### 8.3 규제 제약
1. 한국: 자동매매 프로그램 신고 필요 (금융위원회)
2. 투자 권유 금지 (정보 제공만 가능)
3. 투자 손실 책임 면책 명시

---

**문서 종료**

---

## 부록 A: 용어집

| 용어 | 설명 |
|------|------|
| ECS | Elastic Container Service (AWS) |
| RDS | Relational Database Service (AWS) |
| Multi-AZ | 다중 가용 영역 배포 |
| JWT | JSON Web Token |
| RBAC | Role-Based Access Control |

## 부록 B: 참조 문서

1. AWS Well-Architected Framework
2. OpenAPI 3.0 Specification
3. 금융위원회 자동매매 신고 가이드
4. GDPR Compliance Checklist
