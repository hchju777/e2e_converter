# Python 의존성 관리

## 설치 방법

### 프로덕션 (기본)
```bash
pip install -r requirements/base.txt
```

### 개발 (개발자용)
```bash
pip install -r requirements/dev.txt
```

`dev.txt`는 `base.txt`를 포함하므로 base를 별도 설치할 필요 없음.

## 파일 설명

| 파일 | 설명 |
|------|------|
| `base.txt` | 프로덕션 필수 패키지 |
| `dev.txt` | 개발/빌드 추가 패키지 |

### base.txt 포함 패키지
- `pandas` — 데이터 처리
- `pyreadstat` — SPSS SAV 파일 읽기
- `openpyxl` — Excel 처리

### dev.txt 추가 패키지
- `pyinstaller` — Windows EXE 빌드
- `pytest` — 테스트 프레임워크
- `black` — 코드 포매팅
- `flake8` — 코드 검사

## 가상환경 설정

```bash
# 가상환경 생성
python -m venv .venv

# 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 활성화 (Windows CMD / Git Bash)
source .venv/Scripts/activate

# 프로덕션 패키지 설치
pip install -r requirements/base.txt

# 개발 패키지 설치 (선택)
pip install -r requirements/dev.txt
```

## 패키지 업그레이드

```bash
pip install --upgrade -r requirements/base.txt
```

## 새 패키지 추가

1. 설치: `pip install 패키지명`
2. 저장: `pip freeze > requirements/base.txt` (프로덕션) 또는 dev.txt (개발)
3. Git 커밋
