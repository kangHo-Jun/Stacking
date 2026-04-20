# 건축자재 적재 최적화 시스템 — UI 문서

## 1. 레이아웃 구조

### 1.1 3패널 구조
`main.html`은 아래 3패널 구조를 사용한다.

| 영역 | 구성 |
|------|------|
| Left | 자재 입력 / 수량 입력 / 자재 추가 / 입력 목록 / 차량 드롭다운 / 실행 버튼 |
| Center | 2.5D / 3D 탭, 평면도 / 측면도 / 버블맵, Three.js 3D |
| Right | 배차 결과 / 위험도 / 현장 매뉴얼 / 적재 순서 |

### 1.2 패널 너비
CSS 변수 기준:

| 항목 | 값 |
|------|----|
| Left Panel | `280px` |
| Center Panel | `minmax(0, 1fr)` |
| Right Panel | `260px` |
| 패널 간 간격 | `16px` |
| 전체 패딩 | `16px` |

### 1.3 Header 높이 및 구성

| 항목 | 값 |
|------|----|
| 높이 | `48px` |
| 위치 | `sticky top: 0` |
| 좌측 | 인디케이터 점 + `대산 적재 AI` |
| 우측 | `이력 조회`, `PDF 출력` 버튼 |

### 1.4 모바일 대응 방식
- `@media (max-width: 980px)`에서 3패널을 1패널 표시 방식으로 전환한다.
- `.mobile-nav` 하단 탭 3개를 사용한다.

| 탭 | 대상 패널 |
|----|-----------|
| 입력 | Left Panel |
| 시각화 | Center Panel |
| 결과 | Right Panel |

## 2. 디자인 토큰

### 2.1 브랜드 컬러

| 변수 | 값 |
|------|----|
| `--primary` | `#48BB78` |
| `--primary-dark` | `#123628` |
| `--primary-hover` | `#38A169` |
| `--danger` | `#ef4444` |
| `--danger-soft` | `#fff3f1` |
| `--warning` | `#f59e0b` |
| `--ink` | `#183026` |
| `--muted` | `#64756d` |
| `--line` | `rgba(18, 54, 40, 0.12)` |

### 2.2 배경색

| 항목 | 값 |
|------|----|
| 기본 배경 | `#F1F5F0` |
| Surface | `#FFFFFF` |
| 3D 배경 | `#1a1a2e` |

### 2.3 폰트

| 항목 | 값 |
|------|----|
| 폰트 | `Noto Sans KR` |
| 로드 방식 | Google Fonts |

폰트 사이즈 기준표:

| 용도 | 크기 |
|------|------|
| 섹션 타이틀 | `11px` 또는 현재 코드상 `1.3rem` 사용 영역 병행 |
| 본문 | `11px ~ 12px` |
| 강조 수치 | `13px` |
| 차량명 (최대) | `14px` |
| 버블 % | `22px` |

주의:
- 요청 기준표와 달리 현재 버블맵의 `%`는 [visualizer.py](/Users/zart/Library/Mobile%20Documents/com~apple~CloudDocs/프로젝트/적재시스템/project/src/visualizer.py)에서 `22px`로 렌더링된다.

### 2.4 보더 / 라디우스

| 항목 | 값 |
|------|----|
| 패널 라디우스 | `28px` |
| 내부 카드 라디우스 | `22px` |
| 버튼 라디우스 | `18px` |
| 뱃지 라디우스 | `999px` |
| Glass Border | `rgba(255, 255, 255, 0.45)` |

### 2.5 그라디언트

| 항목 | 값 |
|------|----|
| Header | `linear-gradient(135deg, #123628 0%, #1A4A35 100%)` |
| CTA | `linear-gradient(135deg, #48BB78, #38A169)` |

## 3. 컴포넌트 명세

### 3.1 Header
- 배경 gradient 값
  - `linear-gradient(135deg, #123628 0%, #1A4A35 100%)`
- 타이틀 구성
  - `brand-dot` 원형 인디케이터
  - 텍스트 `대산 적재 AI`
- 우측 버튼 구성
  - `이력 조회` 링크
  - `PDF 출력` 버튼

### 3.2 좌측 패널

| 구성 | 설명 |
|------|------|
| 자재 드롭다운 | `#materialSelect` |
| 수량 입력 | `#quantityInput`, placeholder `수량 입력` |
| 자재 추가 버튼 | `#addOrderButton` |
| 입력된 자재 목록 | `#orderList`, 자재명 말줄임표 처리 |
| 차량 드롭다운 | `#vehicleSelect` |
| 실행 버튼 | `#runButton`, gradient CTA |

추가 사항:
- 자재 카드 제목 `.order-title`은 `white-space: nowrap`, `overflow: hidden`, `text-overflow: ellipsis`를 사용한다.
- 삭제 버튼은 `X` 한 글자다.

### 3.3 중앙 패널 — 시각화

#### 3.3.1 2.5D / 3D 탭 전환 구조
- `.view-tabs` 버튼 2개
  - `2.5D 보기`
  - `3D 보기`
- JS가 `data-view="2d"`, `data-view="3d"`를 기준으로 `#twoDStack`, `#threeShell` 표시를 전환한다.

#### 3.3.2 평면도 SVG 구성
- 생성 함수: `_build_floor_plan_svg()`
- 구성 요소

| 항목 | 구현 |
|------|------|
| 팔레트 1층 | `#1d4ed8` |
| 팔레트 2층 | `#60a5fa` |
| 낱장 | `#16a34a`, 점선 |
| 순서번호 | 박스 중앙 흰색 텍스트 |
| 방향 레이블 | `전방`, `후방` |
| 범례 | `1층`, `2층`, `낱장` |

#### 3.3.3 측면도 SVG 구성
- 생성 함수: `_build_side_view_svg()`
- 구성 요소

| 항목 | 구현 |
|------|------|
| 1층 | 아래 |
| 2층 | 위 |
| 바닥선 | 하단 굵은 선 |
| 층 레이블 | 좌측 `2층`, `1층` |
| 낱장 | 점선 초록 |
| 팔레트 | 실선 파랑 |

#### 3.3.4 버블맵 SVG 구성
- 생성 함수: `_build_weight_map_svg()`
- 구성 요소

| 항목 | 구현 |
|------|------|
| 4분면 | `앞-왼쪽`, `앞-오른쪽`, `뒤-왼쪽`, `뒤-오른쪽` |
| 버블 크기 | `sqrt(weight/total) * 55`, 최소 `15` |
| 색상 | `#1d4ed8`, `#3b82f6`, `#93c5fd`, `#dbeafe` 단계 |
| 상단 문구 | `← 운전석(전방)` |
| 하단 문구 | `후방 →` |
| 편차 표시 | `전후편차`, `좌우편차` 텍스트 |
| 위험도 | 우측 하단 배지 |

#### 3.3.5 3D 뷰 구성

| 항목 | 값 |
|------|----|
| Three.js CDN | `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` |
| OrbitControls CDN | `https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js` |
| 1층 색상 | `#1d4ed8`, `opacity 1.0` |
| 2층 색상 | `#93c5fd`, `opacity 0.85` |
| 낱장 색상 | `#34d399`, `opacity 0.7` |
| 바닥 그리드 | `GridHelper`, `#e2e8f0` |
| 층 레이블 | `Sprite`, `1층`, `2층` |
| 카메라 초기 위치 | `(15, 12, 15)` |
| 카메라 타깃 | `(4, 2, 1.5)` |
| AmbientLight | `0xffffff, 0.6` |
| DirectionalLight | `0xffffff, 0.8`, `position(10,20,10)` |
| OrbitControls | `enableDamping = true` |

### 3.4 우측 패널

#### 배차 결과 카드

| 구성 | 설명 |
|------|------|
| 차량별 한 행 | 차량명 + 팔레트수 뱃지 + 중량 |
| 합계 행 | 전체 중량 |
| 총 운임 행 | 전체 운임 |

숫자 처리:
- `fmtInt()` 사용
- 소수점 표시 없음
- 천단위 콤마 적용

#### 위험도 섹션

| 구성 | 설명 |
|------|------|
| 최종 판정 배지 | `#riskBadge` |
| 항목별 배지 | `#riskList` |
| 항목 수 | 현재 위험도 엔진 기준 7개 |

#### 현장 매뉴얼 박스
- `#manualBox`
- 흰 배경 고정
- 좌측 `5px` 컬러 보더만 변경

#### 적재 순서 목록
- `#sequenceList`
- 항목 구성
  - 번호
  - 자재명
  - 차량/단위/수량 메타정보
  - 중량

## 4. 위험도 색상 체계

현재 `main.html` 구현 기준:

| 레벨 | 배지 배경 | 배지 텍스트 | 매뉴얼 테두리 |
|------|-----------|-------------|---------------|
| Safe | `#48BB78` | 흰색 | `#48BB78` |
| Caution | `#EAB308` | 흰색 | `#EAB308` |
| Danger | `#EF4444` | 흰색 | `#F97316` |
| Critical | `#EF4444` | 흰색 | `#EF4444` |

주의:
- 사용자가 제시한 파스텔 배경표와 다르게, 현재 실제 구현은 채도가 있는 단색 배경 뱃지를 사용한다.

## 5. 반응형 대응

| 구간 | 기준 | 동작 |
|------|------|------|
| PC | `1180px 초과` | 3패널 고정 |
| 태블릿/축소 PC | `1180px 이하` | `280px / flex / 260px` 유지 |
| 모바일 | `980px 이하` | 1패널 표시 + 하단 탭 |

모바일 동작:
- `.left-panel`, `.center-card`, `.right-panel` 중 하나만 `.mobile-active`
- `.mobile-nav` 버튼으로 패널 전환

## 6. 인터랙션

| 인터랙션 | 방식 |
|----------|------|
| 2.5D / 3D 탭 전환 | `.view-tabs` 버튼 클릭 시 `#twoDStack` / `#threeShell` 표시 전환 |
| 자재 추가 | `#addOrderButton` 클릭 |
| 자재 삭제 | 목록 카드의 `X` 버튼 클릭 |
| 최적 배차 실행 | `fetch('/run')`로 JSON 수신 후 JS 렌더링 |
| 3D 회전 / 줌 | OrbitControls |
| PDF 다운로드 | `history_id` 존재 시 `/pdf/<id>` 이동 |
| 이력 조회 | Header `이력 조회` 링크 |

## 7. 사용 금지 표현

현재 `main.html` 기준으로 금지/제거된 항목:

| 항목 | 상태 |
|------|------|
| `VISUALIZATION` | 제거 |
| `RESULT` | 제거 |
| `VEHICLE` | 제거 |
| 소수점 표시 | `fmtInt()`로 제거 |
| 출고일시 표시 | 우측 패널에서 제거 |

주의:
- 내부 JS 변수명이나 CSS 클래스명은 영어가 남아 있다.
- 화면 사용자 노출 텍스트 기준으로 영어 섹션명은 제거된 상태다.
