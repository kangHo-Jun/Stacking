# 대산 Ai V4 - UI 명세서 (2026-03-16 Update)

이 문서는 현재 구축된 대산 Ai 재단 최적화 앱(woodcutter_v4)의 UI 구조와 상호작용 로직을 정의합니다.

---

## 1. 레이아웃 구조 (Layout Architecture)

**3-패널 분할 레이아웃** + Sticky Header + Mobile Nav Tab

| 컴포넌트 | 클래스 | 포지션 | 설명 |
| :--- | :--- | :--- | :--- |
| **Header** | `.header` | `sticky top-0` / `z-index: 100` | 앱 타이틀 + 저장하기/새 프로젝트 버튼 |
| **MobileNav** | `.mobile-nav` | Flow (모바일 전용) | 입력/도면/결과 탭 전환 |
| **LeftPanel** | `.left-panel` | Flow (aside) | 판재·부품 입력 영역 (PC: 360px 고정) |
| **CenterPanel** | `.center-panel` | `flex-1` | 도면 캔버스 미리보기 영역 |
| **RightPanel** | `.right-panel` | Flow (aside) | 최적화 결과 및 통계 (PC: 320px 고정) |

### 레이아웃 크기 토큰

```css
--header-height: 64px;
--panel-left-width: 360px;
--panel-right-width: 320px;
```

---

## 2. 주요 컴포넌트 명세

### 2.1 Header

- **배경**: `--gradient-header` → `linear-gradient(135deg, #123628 0%, #1A4A35 100%)`
- **타이틀**: "대산 Ai" (앞에 `#48BB78` 원형 인디케이터 글로우 포함)
- **우측 버튼**: `저장하기` (secondary), `새 프로젝트` (primary)
- 헤더 내 버튼은 반투명 스타일 별도 오버라이드

### 2.2 모바일 내비게이션 (MobileNav)

- **표시 조건**: 모바일/태블릿 전용 (PC에서 숨김)
- **탭 구성**: `입력` / `도면` / `결과`
- 활성 탭의 패널만 표시 (`.active` 클래스 토글)

### 2.3 좌측 패널 (LeftPanel) — 입력

| 섹션 | 컨트롤 |
| :--- | :--- |
| **판재 정보** | 폭·높이·두께(mm) 숫자 입력, 나무결 방향 체크박스, 전단여부 + 여백(mm) |
| **부품 목록** | 폭·높이·수량 입력, 회전 가능 체크박스, 부품 추가 버튼, 부품 테이블, 전체 삭제 버튼 |
| **고급 설정** | 아코디언 — 톱날 두께(mm), 최적화 방식(가로 우선/자동) |
| **원가 설정** | 아코디언 — 두께별 절단 단가 자동 계산 표시 (12T↓: 1,000원 / 14.5~23T: 1,500원 / 24T↑: 2,000원) |
| **최적화 계산** | `calculate-btn` — 전체 너비 CTA 버튼 |

### 2.4 중앙 패널 (CenterPanel) — 도면

- **캔버스 컨트롤** (`#canvasControlsTop`): 계산 완료 후 표시
  - `미리보기` (secondary), `PDF 다운로드` (primary), `공유 ▾` (dropdown: 이메일/문자/복사)
- **캔버스 스크롤 컨테이너** (`#canvasScrollContainer`): 그룹별 대표 도면 동적 렌더링
- **빈 상태** (`#emptyState`): 계산 전 안내 메시지 표시

### 2.5 우측 패널 (RightPanel) — 결과

| 섹션 | 내용 |
| :--- | :--- |
| **최적화 결과** | 총 판재수, 재단 횟수, 총 재단비 |
| **부품 배치 현황** | `#labelGroupsList` — 라벨 그룹별 배치 상황 |
| **판재 선택** | `#boardNavSection` — 다중 판재 시 개별 도면 탐색 (기본 hidden) |

---

## 3. 상호작용 규칙 (Interactive Rules)

| 액션 | 결과 | 구현 세부사항 |
| :--- | :--- | :--- |
| **부품 없을 때 전체삭제** | 버튼 비활성화 | `disabled + opacity: 0.5` |
| **부품 추가/삭제 후** | 폭 입력 자동 포커스 | `setTimeout(() => partWidth.focus(), 100)` |
| **계산 전** | 캔버스 컨트롤 숨김 | `#canvasControlsTop { display: none }` |
| **계산 완료 후** | 빈 상태 숨기고 도면/결과 표시 | JS로 `display` 토글 |
| **공유 버튼** | 드롭다운 메뉴 토글 | `.share-dropdown-menu` 표시/숨김 |
| **아코디언** | 클릭 시 펼침/접힘 | `.accordion.open` 클래스 토글, 아이콘 회전 |

---

## 4. 디자인 시스템 (Design System)

### 4.1 브랜드 컬러

| 역할 | 값 | 용도 |
| :--- | :--- | :--- |
| Primary | `#48BB78` | CTA 버튼, 인디케이터, 강조 |
| Primary Dark | `#123628` | 헤더 배경, 다크 계열 |
| Primary Hover | `#38A169` | 버튼 호버 상태 |
| Background | `#F1F5F0` | 앱 기본 배경 |
| Surface | `#FFFFFF` | 카드·패널 배경 |
| Danger | `#EF4444` | 삭제 버튼 |

### 4.2 Glassmorphism 토큰

```css
--glass-bg: rgba(255, 255, 255, 0.72);
--glass-bg-heavy: rgba(255, 255, 255, 0.88);
--glass-border: rgba(255, 255, 255, 0.45);
--glass-blur: 16px;
```

Secondary 버튼·일부 컴포넌트에 `backdrop-filter: blur(8px)` 적용

### 4.3 그라디언트

| 변수 | 값 |
| :--- | :--- |
| `--gradient-primary` | `135deg, #48BB78 → #2D7A4F → #123628` |
| `--gradient-header` | `135deg, #123628 → #1A4A35` |
| `--gradient-cta` | `135deg, #48BB78 → #38A169` |

### 4.4 폰트

- **기본**: Noto Sans KR (Google Fonts), 14px base
- **Weight**: 400 / 500 / 600 / 700

### 4.5 그림자 & 트랜지션

```css
--shadow-glow: 0 0 20px rgba(72, 187, 120, 0.25);   /* 버튼 호버 글로우 */
--transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
```

---

## 5. 스타일시트 구조

| 파일 | 역할 |
| :--- | :--- |
| `css/responsive-style.css` | **현재 사용 중** — 통합 반응형 디자인 시스템 (PC/Tablet/Mobile) |
| `css/pc-style.css` | 레거시 — `index.html`에서 미로드, 구 디자인 토큰 보관용 |

---

## 6. JS 모듈 구조

로드 순서:

```
state.js → validator.js → costCalculator.js → labelingEngine.js
→ settingsManager.js → packer.js → renderer.js → pdfGenerator.js
→ main-unified.js
```

---

*Last Updated: 2026-03-16*
