# 프로젝트 아키텍처 (Architecture)

## 전체 개요

e2e_converter는 **3단계 파이프라인** 구조로 동작합니다:

```
데이터 입력 → 지표 계산 → 대시보드 생성
   (SAV)      (지표값)      (HTML)
```

---

## 1. 모듈 구조

### `src/`
프로젝트의 핵심 코드 디렉토리

```
src/
├── __init__.py              # 패키지 초기화 (버전, 주요 export)
│
├── metrics/                 # 지표 계산 모듈
│   ├── __init__.py
│   └── calc_metrics.py      # 지표 계산 엔진 (메인 로직)
│
├── dashboard/              # 대시보드 생성 모듈
│   ├── __init__.py
│   ├── build_dashboard.py  # 대시보드 생성
│   └── web_app.py          # 웹 애플리케이션 서버
│
└── utils/                  # 공용 유틸리티
    ├── __init__.py
    ├── banner.py           # 배너(필터) 조건 처리
    ├── export_spec.py      # 지표 스펙 내보내기
    ├── logger.py           # 로깅
    └── read_sav.py         # SPSS SAV 파일 읽기
```

### `config/`
설정 파일 디렉토리

```
config/
├── __init__.py             # 설정 로더
├── settings.json           # 실행 설정 (경로, 파라미터)
└── metric_spec.csv         # 지표 정의 스펙 (329개 지표)
```

### `scripts/`
배치 스크립트 및 유틸리티

```
scripts/
├── build_exe.bat           # Windows: EXE 빌드 스크립트
├── run_converter.bat       # Windows: 웹앱 실행
└── run_dev.sh              # Unix/Mac: 개발 실행
```

### `docs/`
프로젝트 문서

```
docs/
└── DASHBOARD_HANDOVER.md   # 대시보드 인수인계 문서
```

---

## 2. 데이터 흐름

### Step 1: 설정 로드
```python
# config/settings.json 로드
settings = load_settings("config/settings.json")
# ├─ spec_path: CSV 파일 경로
# ├─ sav_dir: SAV 파일 디렉토리
# ├─ output_dir: 결과 저장 위치
# └─ dashboard_banners: 배너 조건 목록
```

### Step 2: 데이터 입력
```python
# SAV 파일 읽기 (SPSS 형식)
sav_data = read_sav_files("db")
# → DataFrame: 응답자 × 변수

# 지표 스펙 로드 (CSV)
specs = load_spec("config/metric_spec.csv", banner="전체")
# → List[MetricSpec]: 329개 지표 정의
```

### Step 3: 지표 계산
```python
# 각 지표별로 계산
for spec in specs:
    if spec.calc_type == "SUM":
        result = sum(응답자별 SAV 표현식 결과)
    elif spec.calc_type == "Mean":
        result = mean(응답자별 SAV 표현식 결과)
    elif spec.calc_type == "Count":
        result = len(유효_응답자)
    elif spec.calc_type == "계산식":
        result = 다른_행_참조 및 산술식 계산
```

### Step 4: 배너별 필터링
```python
# 배너 조건 적용
for banner in dashboard_banners:
    filtered_data = filter_banner_data(sav_data, banner)
    results[banner.name] = calc_metrics(specs, filtered_data)
```

### Step 5: 대시보드 생성
```python
# 계산 결과를 HTML에 임베드
dashboard_html = build_dashboard(results)
# → results/PsO_dashboard_26년6차.html
```

### Step 6: 출력
```
results/
├── PsO_dashboard_26년6차.html  # 최종 대시보드 (HTML)
└── results_26년6차.csv         # 계산 결과 (CSV)
```

---

## 3. 핵심 클래스/함수

### `calc_metrics.py`

| 함수 | 설명 |
|------|------|
| `load_settings()` | JSON 설정 파일 로드 |
| `load_spec()` | CSV 지표 스펙 로드 및 필터링 |
| `normalize()` | 공백 정규화 |
| `calc_metrics()` | 전체 지표 계산 엔진 |
| `evaluate_expr()` | SAV 수식 평가 (안전한 계산) |

**MetricSpec 클래스**
```python
@dataclass
class MetricSpec:
    gubun: str          # 구분 (예: "조사 결과")
    item: str           # 항목 (예: "환자 규모")
    question: str       # 문항 (예: "PsO 환자 규모")
    sav_expr: str       # SAV 표현식 (예: "Q1 + Q2")
    calc_type: str      # 계산 타입 (SUM/Mean/Count/계산식)
    banner: str         # 배너 조건 (전체/수도권/T1 등)
```

### `build_dashboard.py`

| 함수 | 설명 |
|------|------|
| `load_template()` | 기존 HTML 템플릿 로드 |
| `inject_data()` | 계산 결과를 JS 데이터 변수로 변환 |
| `build_dashboard()` | 템플릿 + 데이터 병합해 최종 HTML 생성 |

### `banner.py`

| 함수 | 설명 |
|------|------|
| `validate_banner_configs()` | 배너 설정 검증 |
| `filter_banner_data()` | DataFrame을 배너 조건에 따라 필터링 |

### `read_sav.py`

| 함수 | 설명 |
|------|------|
| `read_sav_files()` | SAV 파일 읽기 (pyreadstat 사용) |

### `logger.py`

| 함수 | 설명 |
|------|------|
| `get_logger()` | 구성된 Logger 반환 |

### `export_spec.py`

| 함수 | 설명 |
|------|------|
| `export_spec_from_xlsx()` | xlsx → CSV 스펙 내보내기 |

---

## 4. 진입점 (Entry Points)

### CLI 진입점 (`main.py`)

```python
# 명령어별 실행
python main.py web                      # 웹앱 실행
python main.py calc --banner            # 지표 계산 + 대시보드
python main.py sav-info                 # SAV 파일 정보 조회
```

### 웹 애플리케이션 (`src/dashboard/web_app.py`)

로컬 HTTP 서버 (기본: http://127.0.0.1:8765)
- SAV 파일 업로드 → 즉시 계산 → 대시보드 생성
- 비개발자용 GUI

---

## 5. 설정 (config/)

### settings.json 구조

```json
{
    "spec_path": "config/metric_spec.csv",
    "sav_dir": "db",
    "sav_filename": "(0709)피부과(6차)_v2.0.SAV",
    "output_dir": "results",
    "output_filename": "results_26년6차.csv",
    "result_column": "26년 6차",
    "dashboard_banners": [
        {"name": "전체"},
        {"name": "수도권", "column": "Area", "values": [1]},
        {"name": "지방", "column": "Area", "values": [2, 3, 4, 5, 6]},
        {"name": "T1", "column": "UCB_Tier", "values": [1]},
        {"name": "T2", "column": "UCB_Tier", "values": [2]},
        {"name": "T3", "column": "UCB_Tier", "values": [3, 99]}
    ],
    "dashboard_template": "db/PsO_dashboard_v4 (2).html",
    "dashboard_output": "results/PsO_dashboard_26년6차.html"
}
```

---

## 6. 지표 스펙 (config/metric_spec.csv)

| 컬럼 | 예시 | 설명 |
|------|------|------|
| `구분` | "조사결과" | 페이지 그룹 |
| `항목` | "환자규모" | 상위 분류 |
| `문항` | "PsO 환자 규모" | 지표명 |
| `SAV 변수` | "Q1 + Q2" | SPSS 수식 |
| `계산` | "Sum" | 계산 타입 |
| `배너조건` | "전체" | 필터 조건 |

**계산 타입 (4가지)**
- `SUM`: 응답자별 계산 후 합산
- `Mean`: 평균값
- `Count`: 유효 응답자 수
- `계산식`: 다른 행 참조 + 산술식

---

## 7. 에러 처리 및 로깅

### Logger 구성 (`src/utils/logger.py`)

```python
logger = get_logger(__name__)
# ├─ 콘솔 출력 (DEBUG 이상)
# └─ 로그 파일 (logs/converter.log)
```

**로그 레벨**
- `DEBUG`: 개발용 상세 정보
- `INFO`: 주요 진행 상황
- `WARNING`: 경고 (데이터 부족 등)
- `ERROR`: 실행 오류
- `CRITICAL`: 시스템 오류

---

## 8. 테스트 구조 (`tests/`)

```
tests/
├── conftest.py              # pytest 설정
├── test_calc_metrics.py     # 지표 계산 테스트
├── test_dashboard.py        # 대시보드 생성 테스트
└── test_web_app.py          # 웹앱 테스트
```

실행:
```bash
pytest                       # 전체 테스트
pytest tests/test_calc_metrics.py -v  # 특정 테스트
```

---

## 9. 의존성 관리

### requirements.txt (프로덕션)
```
pandas
pyreadstat
openpyxl
```

### requirements-dev.txt (개발)
```
pytest
pyinstaller
black
flake8
```

---

## 10. 버전 관리

- **VERSION 파일**: 프로젝트 버전 정의 (기본: 1.0.0)
- **src/__init__.py**: `__version__` 변수로 import 가능

```python
from src import __version__
print(__version__)  # "1.0.0"
```

---

## 11. 향후 확장

- ✅ 배너 1개 (전체) 계산
- 🔄 배너 6개 (지역/직급별) 병렬 계산
- 🔄 동적 스펙 로드 (다양한 지표 정의 가능)
- 🔄 캐싱 (반복 계산 최적화)
- 🔄 API 서버화 (REST 엔드포인트 추가)
