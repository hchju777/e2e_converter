# PsO H-Biologics Tracker Dashboard — 인수인계 문서

> 작성일: 2026-06-05  
> 버전: v4.0 / v4.1  
> 작성: Claude (Anthropic) + UCB 담당자

---

## 1. 프로젝트 개요

UCB PsO H-Biologics Tracker Apr. 2026 보고서(PDF/Excel)를 기반으로 제작한 **단일 HTML 인터랙티브 대시보드**입니다.

- **원본 파일**: `UCB_20260518_180044__복사본.xlsx` (Summary 시트), `PsO_HBiologics_Tracker_Apr_2026_Report_260518.pdf`
- **최종 산출물**: `PsO_dashboard_v4.html` (기본), `PsO_dashboard_v4_1.html` (엑셀 연동)

---

## 2. 파일 구성

| 파일 | 설명 |
|---|---|
| `PsO_dashboard_v4.html` | 열면 표지 → 대시보드 바로 진입. 하드코딩 데이터 사용. 사내 점검/공유용 |
| `PsO_dashboard_v4_1.html` | 열면 표지 → 엑셀 업로드 화면. 파일 드래그앤드롭으로 데이터 자동 갱신. 매월 업데이트용 |

### 두 파일의 차이점
`v4_1`은 `DOMContentLoaded` 이벤트에서 드롭존 자동 스킵 코드만 제거된 버전입니다.

```js
// v4: 드롭존 스킵하고 바로 대시보드 표시
dz.classList.add('hidden');
document.getElementById('reloadBar').classList.add('visible');
document.getElementById('loadedFileName').textContent = '📊 기본 데이터 (Apr. 2026)';
renderP5();

// v4_1: 위 코드 없음 → 드롭존 화면 표시
```

---

## 3. 기술 스택

```
단일 HTML 파일 (CSS + HTML + JS 인라인)
├── Chart.js 4.4.1          (CDN: cdnjs.cloudflare.com)
├── chartjs-plugin-datalabels 2.2.0  (CDN: jsdelivr.net)
└── xlsx 0.18.5             (CDN: jsdelivr.net) — 엑셀 파싱용
```

---

## 4. HTML 내부 구조

```
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta> / <title> / 외부 CDN 스크립트 3개 / <style>
</head>
<body>
  <!-- 표지 (#coverPage) -->
  <!-- 사이드바 (.sidebar) — 아코디언 3섹션 -->
  <!-- 메인 (.main) — 각 페이지 (.page-section) -->
  <script> ... </script>
</body>
```

> ⚠️ CSS는 반드시 `<head>` 안 `<style>` 태그에 있어야 합니다.  
> HTML 구조를 재조립할 때 `<style>` 위치가 `<body>` 앞에 있는지 반드시 확인하세요.  
> 문서 주석(`<!-- -->`)을 `<html>` 태그 앞에 두면 CSS가 깨집니다.

---

## 5. JS 코드 구조

```js
/* [1] 상수 & 공통 유틸 */
// PERIODS_ASC, PERIODS_DESC, LATEST_IDX
// fmt(), applyColClass(), buildPerRow(), getVisiblePeriods()
// buildWaveDropdown(), updateTriggerLabel(), updateToggleBtn(), updateRecentBtn()

/* [2] 데이터 */
// P5_RESP, P5_DATA
// P11_DATA, P11B_DATA
// P12_DATA, P12B_DATA
// P13_DATA
// BRAND_DATA, BRAND_BANNER_DATA, BRAND_TABLE_DATA
// SOV_DATA, SOV_BANNER_DATA, SOV_TABLE_DATA

/* [3] 렌더 함수 */
// renderP5(), renderP11(), renderP12(), renderP13()
// buildBrandPage(), renderBrandBanner(), renderBrandTable()
// renderSovPage(), renderSovBanner(), renderSovTable()
// renderP14()~renderP33b()

/* [4] 초기화 & 네비게이션 */
// 표지 클릭 이벤트, 아코디언, 네비게이션, 엑셀 파싱
```

---

## 6. 페이지 목록 (총 38개)

### 표지 & 개요
| ID | 페이지 | 설명 |
|---|---|---|
| `coverPage` | 표지 | PDF 1p 스타일. 클릭하여 진입 |
| `overview` | 조사 설계 | PDF 3p. 조사 대상/표본/지역/방법/기간 |

### 조사 결과 (24개)
| ID | 페이지 |
|---|---|
| `p5` | PsO 환자 규모 (Total/Area/Tier 필터 + Wave) |
| `p11` | 생물학적 제제 처방 비율 (차트 + T1/T2/T3 표) |
| `p12` | 건선 환자 타입별 구성 (차트 + Dynamic 비중 표) |
| `p13` | 건선 환자 타입별 구성 – Dynamic |
| `p14~p17` | 브랜드별 처방 비율 (Total/Dynamic/Naïve/Switching) |
| `p18~p23` | 브랜드별 처방 비율 배너별 표 (Total/수도권/지방/T1/T2/T3) |
| `p24~p25` | SoV 영업사원/MSL Detailing 차트 |
| `p26~p29` | SoV 영업사원/MSL by Area/Tier 표 |
| `p30~p33` | SoV Brand Activity/Online/Offline/Small group 차트 |

### by 배너 (12개)
| ID | 페이지 |
|---|---|
| `p11b`, `p12b` | 처방 비율/타입별 구성 (Total/Area/Tier 필터) |
| `p14b~p17b` | 브랜드별 처방 비율 (Total/Area/Tier 필터) |
| `p24b~p25b` | SoV Detailing (Total/Area/Tier 필터) |
| `p30b~p33b` | SoV Marketing (Total/Area/Tier 필터) |

---

## 7. 사이드바 구조

아코디언 방식 (클릭으로 접기/펼치기):
```
조사 개요 ▼
  03 조사 설계

조사 결과 ▼
  05 PsO 환자 규모
  11 생물학적 제제 처방 비율
  ...
  33 Small group meeting 점유율

by 배너 ▼
  11+ 생물학적 제제 처방 비율 (by 배너)
  ...
  33+ Small group meeting 점유율 (by 배너)
```

---

자세한 내용은 원문서를 참고하세요.
