# PsO Dashboard Converter

과거 데이터 엑셀과 이번 차수 SPSS 설문 데이터(`.sav`)를 읽어 지표를 계산하고 다음 결과물을 만드는 Windows 프로그램입니다.

- HTML 대시보드(전체 차수 포함)
- **엑셀 — 이번 차수가 더해진 과거 데이터. 다음 차수 변환에 그대로 사용**
- CSV 계산 결과
- PDF 보고서
- PowerPoint 발표자료(`.pptx`)

이 문서는 **코딩을 전혀 모르는 사용자**를 기준으로 작성했습니다. 위에서부터 순서대로 따라 하면 됩니다.

> 모든 명령은 `main.py`가 보이는 `e2e_converter` 폴더에서 실행해야 합니다.

---

## 1. 처음 설치하기: Git clone부터 초기 환경 설정까지

이 장은 처음 한 번만 진행하면 됩니다.

### 1-1. 필요한 프로그램 설치

#### Git 설치

Git은 프로젝트 파일을 내려받는 프로그램입니다.

1. [Git for Windows](https://git-scm.com/download/win)에 접속합니다.
2. 64비트 설치 파일을 내려받아 실행합니다.
3. 특별한 사내 규정이 없다면 설치 화면의 기본값을 그대로 사용합니다.
4. 설치가 끝나면 시작 메뉴에서 `Git Bash`를 실행합니다.
5. 다음 명령을 입력합니다.

```bash
git --version
```

`git version 2.x.x`와 비슷한 문구가 나오면 정상입니다.

#### Python 설치

Python은 이 프로그램을 실행하고 EXE로 만드는 데 필요합니다. **64비트 Python 3.12 또는 3.13을 권장합니다.**

1. [Python Windows 다운로드](https://www.python.org/downloads/windows/)에 접속합니다.
2. 64비트 Windows Installer를 내려받아 실행합니다.
3. 설치 화면에서 **`Add python.exe to PATH`를 반드시 체크**합니다.
4. `Install Now`를 눌러 설치합니다.
5. 열려 있던 Git Bash를 닫고 다시 엽니다.
6. 다음 명령을 입력합니다.

```bash
python --version
```

`Python 3.x.x`가 나오면 정상입니다. 명령을 찾을 수 없다는 메시지가 나오면 PC를 재시작하거나 Python을 `Add python.exe to PATH` 옵션과 함께 다시 설치합니다.

> Python 3.14에서도 실행될 수 있지만, 사용하는 패키지의 호환성을 고려해 3.12 또는 3.13을 권장합니다.

#### Visual Studio Code 설치(선택 사항)

설정 파일을 편집하기 편한 프로그램입니다. 메모장을 사용해도 되므로 필수는 아닙니다.

1. [Visual Studio Code](https://code.visualstudio.com/download)를 설치합니다.
2. 설치 중 `Add to PATH`와 `Open with Code`를 선택합니다.
3. VS Code를 실행하고 `File > Open Folder`에서 프로젝트 폴더를 엽니다.

### 1-2. 프로젝트 내려받기: git clone

1. GitHub에서 프로젝트 페이지를 엽니다.
2. 초록색 `Code` 버튼을 누릅니다.
3. `HTTPS` 주소를 복사합니다.
4. 프로젝트를 저장할 위치에서 Git Bash를 엽니다.

바탕화면에 내려받는 예시는 다음과 같습니다.

```bash
cd /c/Users/사용자이름/Desktop
git clone <복사한 GitHub 주소>
cd e2e_converter
```

예시:

```bash
cd /c/Users/hong/Desktop
git clone https://github.com/company/e2e_converter.git
cd e2e_converter
```

비공개 저장소라면 GitHub 로그인을 요구할 수 있습니다.

현재 위치가 맞는지 확인하려면 다음 명령을 입력합니다.

```bash
ls
```

목록에 `main.py`, `config`, `src`, `scripts`가 보이면 정상입니다.

### 1-3. 가상환경 만들기

가상환경은 이 프로젝트만 사용하는 별도의 Python 공간입니다. 다른 프로그램의 Python 설정에 영향을 주지 않습니다.

Git Bash에서 다음 명령을 차례대로 실행합니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
```

명령줄 앞에 `(.venv)`가 붙으면 가상환경이 활성화된 것입니다.

PowerShell을 사용한다면 활성화 명령은 다음과 같습니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

PowerShell에서 스크립트를 실행할 수 없다는 오류가 발생하면 Git Bash를 사용하는 것이 가장 간단합니다.

### 1-4. 필요한 패키지 설치

웹 프로그램만 실행하려면 다음 명령을 사용합니다.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

EXE 빌드와 테스트까지 하려면 개발용 패키지를 설치합니다. `dev.txt`는 기본 패키지도 함께 설치합니다.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
```

### 1-5. 입력 파일 준비

`db` 폴더에 **반드시 있어야 하는 파일은 기준 대시보드 HTML 하나**입니다(현재 기본값: `PsO_dashboard_v4.html`).

```text
e2e_converter/
├── db/
│   └── PsO_dashboard_v4.html   # 필수: 새 차수를 추가할 기준 HTML
├── config/
├── main.py
└── ...
```

**SAV와 과거 데이터 엑셀은 `db` 폴더에 넣지 않아도 됩니다.** 웹 화면에서 두 파일을 직접 업로드하며, 파일이 PC 어디에 있든 상관없습니다.

| 사용 방식 | 필요한 입력 | `db` 폴더에 넣어야 하나? |
|---|---|---|
| 웹 화면(EXE 실행, `python main.py web`) | 과거 데이터 엑셀 + SAV | 아니요. 화면에서 업로드 |
| `python main.py calc` | 과거 데이터 엑셀 + SAV | 예. `settings.json`의 `history_filename`·`sav_filename`으로 찾음 |
| `python main.py sav-info` | SAV | 예. `db` 폴더를 검색 |

> 웹 화면에서는 **과거 데이터 엑셀이 반드시 필요합니다.** 자세한 내용은 [3-2. 과거 데이터 엑셀과 SAV 변환](#3-2-과거-데이터-엑셀과-sav-변환)을 참고합니다.

아래 두 명령을 사용할 때만 `db` 폴더에 입력 파일을 넣고, `config/settings.json`의 파일명을 실제 파일명과 맞춥니다. 자세한 내용은 [4. config 설명](#4-config-설명)을 참고합니다.

```text
e2e_converter/
└── db/
    ├── 설문데이터.SAV              # calc / sav-info 명령을 쓸 때만 필요
    ├── 과거데이터.xlsx             # calc 명령을 쓸 때만 필요
    └── PsO_dashboard_v4.html
```

### 1-6. 다음에 다시 사용할 때

가상환경과 패키지를 매번 새로 만들 필요는 없습니다. 프로젝트 폴더에서 가상환경만 다시 활성화합니다.

Git Bash:

```bash
cd /c/Users/사용자이름/Desktop/e2e_converter
source .venv/Scripts/activate
```

PowerShell:

```powershell
cd C:\Users\사용자이름\Desktop\e2e_converter
.venv\Scripts\Activate.ps1
```

---

## 2. EXE 파일 만들기

EXE는 Python이 설치되지 않은 PC에서도 실행할 수 있는 배포용 파일입니다.

### 2-1. 빌드 전 확인

다음 조건을 확인합니다.

- 프로젝트 폴더에 `.venv`가 있음
- `requirements/dev.txt` 설치가 완료됨
- `config/VERSION`에 버전이 `1.2.0`처럼 `숫자.숫자.숫자` 형식으로 작성됨
- `config/settings.json`의 `dashboard_template` 파일이 실제로 존재함

개발용 패키지를 아직 설치하지 않았다면 다음 명령을 실행합니다.

```bash
source .venv/Scripts/activate
python -m pip install -r requirements/dev.txt
```

### 2-2. EXE 빌드 실행

Windows 탐색기에서 `scripts/build_exe.bat`을 더블클릭하거나, 프로젝트 폴더의 PowerShell에서 다음 명령을 실행합니다.

```powershell
.\scripts\build_exe.bat
```

Git Bash에서는 다음처럼 실행합니다.

```bash
./scripts/build_exe.bat
```

빌드에는 수십 초에서 수 분이 걸릴 수 있습니다. 다음 문구가 나오면 성공입니다.

```text
[SUCCESS] release\PsO_Dashboard_Converter_v1.2.0.exe
```

생성된 파일은 `release` 폴더에 있습니다.

```text
release/PsO_Dashboard_Converter_v<버전>.exe
```

EXE 파일명에 들어가는 버전은 `config/VERSION` 값으로 결정됩니다.

### 2-3. EXE 실행

1. `release` 폴더에서 EXE를 더블클릭합니다.
2. 검은색 창을 닫지 않고 기다립니다.
3. 웹 브라우저가 자동으로 열립니다.
4. 자동으로 열리지 않으면 브라우저 주소창에 `http://127.0.0.1:8765`를 입력합니다.
5. 사용이 끝나면 검은색 창을 닫습니다.

Windows가 알 수 없는 게시자 경고를 표시하면 사내에서 전달받은 정상 파일인지 확인한 후 `추가 정보 > 실행`을 선택합니다.

### 2-4. EXE 빌드 오류가 발생할 때

`Unable to find ...html` 오류가 나오면 `config/settings.json`의 `dashboard_template` 경로와 실제 HTML 파일 위치가 일치하는지 확인합니다.

예시:

```json
"dashboard_template": "db/PsO_dashboard_v4.html"
```

---

## 3. 웹으로 실행하고 사용하는 방법

### 3-1. 소스 코드로 웹 실행

가상환경이 활성화된 프로젝트 폴더에서 실행합니다.

```bash
python main.py web
```

또는 Windows 탐색기에서 다음 파일을 더블클릭합니다.

```text
scripts/run_converter.bat
```

브라우저가 자동으로 열리지 않으면 다음 주소로 접속합니다.

```text
http://127.0.0.1:8765
```

### 3-2. 과거 데이터 엑셀과 SAV 변환

이 프로그램은 **과거 데이터 엑셀**과 **이번 차수 SAV** 두 파일을 받아서 동작합니다.

- 지난 차수까지의 지표 값은 **엑셀이 정본**입니다. 대시보드에는 값을 저장해 두지 않습니다.
- SAV는 **이번 차수 하나만** 계산합니다.
- 결과로 나오는 엑셀에는 이번 차수가 더해져 있으며, **다음 달에 이 엑셀을 그대로 다시 올리면 됩니다.**

```text
과거 데이터 엑셀(지난 차수까지)  +  이번 차수 SAV
                  ↓
   HTML 대시보드(전체 차수)  +  엑셀(이번 차수 추가됨)
                  ↓
        다음 달에 이 엑셀을 다시 입력으로 사용
```

#### 변환 순서

1. 위쪽 점선 영역에 **과거 데이터 엑셀(`.xlsx`)** 을 올립니다.
   - 올리는 즉시 엑셀에 든 차수를 읽어 `17개 차수 (25년 1차 ~ 26년 5차)`처럼 보여줍니다.
   - 보고 차수와 실사 기간도 이 엑셀에 맞춰 자동으로 채워집니다.
2. 아래쪽 점선 영역에 **이번 차수 SAV(`.sav`)** 를 올립니다.
3. 보고 차수를 확인합니다. 엑셀에 아직 없는 **바로 다음 차수**가 자동으로 들어갑니다(예: 엑셀이 26년 5차까지면 `26년 6차`). 필요하면 연도·차수 숫자를 직접 고칠 수 있습니다.
4. `조사 설계` 항목을 확인하고 필요하면 수정합니다.
5. `대시보드 생성` 버튼을 누릅니다. **두 파일이 모두 올라와야 버튼이 활성화됩니다.**
6. 계산이 끝날 때까지 기다립니다.
7. 필요한 파일의 다운로드 버튼을 누릅니다. **엑셀은 반드시 함께 내려받아 다음 차수에 사용하세요.**

두 파일 모두 PC 어디에 있어도 되며 `db` 폴더에 미리 넣을 필요가 없습니다.

확장자가 맞지 않는 파일을 올리면 해당 영역이 빨갛게 바뀌며 `xlsx 형식의 파일을 업로드하세요`처럼 그 자리에서 알려 줍니다. 잘못 올려도 이전에 고른 파일은 그대로 유지됩니다.

#### 조사 설계 입력

대시보드의 `조사 설계` 장표에 들어갈 값을 생성 전에 직접 입력할 수 있습니다.

| 항목 | 입력 방법 | 기본값 |
|---|---|---|
| 조사 대상 | 여러 줄 입력. 한 줄이 항목 하나 | 기준 HTML의 현재 값 |
| 표본 크기 | 텍스트 | 기준 HTML의 현재 값 |
| 조사 지역 | 텍스트 | 기준 HTML의 현재 값 |
| 자료 수집 방법 | 텍스트 | 기준 HTML의 현재 값 |
| 실사 기간 | 달력에서 시작일과 종료일 선택 | 시작일은 **엑셀의 첫 차수가 시작한 달 1일**, 종료일은 **오늘** |

실사 기간은 `2025년 1월 1일 ~ 2026년 7월 26일`처럼 시작일과 종료일 모두 연도를 붙여 표시됩니다. 종료일을 시작일보다 앞선 날짜로 지정할 수는 없습니다(달력에서 아예 선택되지 않습니다).

#### 다운로드

| 결과 | 설명 |
|---|---|
| HTML | 브라우저에서 확인하는 대시보드(전체 차수 포함) |
| **엑셀** | **이번 차수가 추가된 과거 데이터. 다음 차수 변환에 그대로 사용** |
| CSV | 이번 차수의 배너별 지표 계산 결과 |
| PDF | 인쇄 및 공유용 보고서 |
| PPTX | 표와 차트를 PowerPoint에서 편집할 수 있는 발표자료 |

다운로드 버튼을 누르면 **저장 위치와 파일 이름을 지정하는 창**이 열립니다. 파일 이름에는 보고 차수가 자동으로 들어갑니다(예: `PsO_metrics_26년6차.csv`).

> Chrome과 Edge에서는 폴더를 직접 고르는 저장 창이 열립니다. Firefox나 Safari에서는 파일 이름만 입력받고 브라우저의 기본 다운로드 폴더에 저장됩니다.

PDF와 PPTX는 저장 위치를 고른 뒤에 만들기 시작하며 최대 30초쯤 걸립니다. 만드는 동안 안내 상자가 파랗게 깜빡이므로, 그 표시가 사라질 때까지 창을 닫지 말고 기다립니다. PDF/PPTX 생성에는 Windows의 Microsoft Edge가 필요합니다.

### 3-3. HTML 대시보드 사용

HTML을 열면 왼쪽 메뉴에서 조사 설계, 건선 환자, 브랜드 처방, MSL Detailing, Small group 등의 장표로 이동할 수 있습니다.

- 배너가 있는 장표에서는 `전체`, `수도권`, `지방`, `T1`, `T2`, `T3`을 선택할 수 있습니다.
- Wave 선택 메뉴에서 표시할 조사 차수를 바꿀 수 있습니다.
- Wave 오른쪽의 `% 표시`를 켜면 표와 그래프의 비율 값에 `%`가 붙습니다. 환자 수처럼 비율이 아닌 값에는 붙지 않으며, 설정은 장표마다 따로 적용됩니다.
- 왼쪽 메뉴는 본문과 따로 스크롤됩니다. 본문을 내려도 메뉴는 화면에 그대로 남습니다.
- 각 장표 위의 `장표 이미지 저장` 버튼을 누르면 현재 보이는 표 또는 그래프가 PNG로 저장됩니다. 저장 위치와 파일 이름을 지정하는 창이 열립니다.
- 이미지에는 현재 선택한 배너와 Wave가 반영됩니다.

### 3-4. 웹 프로그램 종료

웹페이지 탭만 닫으면 서버는 계속 실행될 수 있습니다. 프로그램을 완전히 종료하려면 처음 실행할 때 열린 검은색 콘솔 창을 닫거나 `Ctrl+C`를 누릅니다.

### 3-5. 웹 화면이 열리지 않을 때

검은색 창에 나오는 메시지를 먼저 확인합니다.

| 메시지 | 뜻과 해결 |
|---|---|
| `🚀 PsO 변환기 v1.2.0 실행: http://127.0.0.1:8765/` | 정상 실행 중입니다. 브라우저만 안 열린 것이니 그 주소를 주소창에 직접 입력합니다 |
| `⚠️ 브라우저를 자동으로 열지 못했습니다` | 안내에 적힌 주소를 주소창에 직접 입력합니다 |
| `💥 이미 변환기가 실행 중입니다` | 이전에 열어 둔 검은색 창을 모두 닫고 다시 실행합니다 |
| `ModuleNotFoundError` | 가상환경 활성화 후 `python -m pip install -r requirements/base.txt`를 실행합니다 |

그 밖에 확인할 것:

- Windows 방화벽 안내가 나오면 로컬 실행을 허용합니다.
- 8765 포트를 다른 프로그램이 사용 중이면 해당 프로그램을 종료합니다.

> **다른 PC에서 `git pull` 후 실행이 안 될 때**
> `.venv`(가상환경)와 `release`(EXE)는 git으로 전달되지 않습니다. PC마다 [1-3](#1-3-가상환경-만들기)·[1-4](#1-4-필요한-패키지-설치)를 따라 가상환경과 패키지를 새로 준비해야 하고, EXE가 필요하면 [2. EXE 파일 만들기](#2-exe-파일-만들기)로 직접 빌드합니다.
> 과거 데이터 엑셀도 git에 포함되지 않으므로 따로 전달받아야 합니다.

업로드한 SAV 파일은 이 PC 안에서만 처리되며 외부 서버로 전송되지 않습니다.

---

## 4. config 설명

`config` 폴더에는 입력 파일, 출력 파일, 보고 차수와 계산 방법을 지정하는 설정이 들어 있습니다.

### 4-1. config 폴더 파일

| 파일 | 역할 |
|---|---|
| `config/settings.json` | 입력·출력 경로, 차수, 배너와 HTML 템플릿 설정 |
| `config/metric_spec.csv` | SAV 변수와 지표 계산 방법 정의 |
| `config/VERSION` | 화면과 EXE 파일명에 사용할 프로그램 버전 |
| `config/__init__.py` | Python용 내부 파일. 수정할 필요 없음 |

### 4-2. settings.json

현재 형식은 다음과 같습니다.

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
    "dashboard_template": "db/PsO_dashboard_v4.html",
    "dashboard_output": "results/PsO_dashboard_26년6차.html"
}
```

각 항목의 의미는 다음과 같습니다.

| 항목 | 설명 |
|---|---|
| `spec_path` | 지표 계산 규칙이 들어 있는 CSV 경로. 일반 사용자는 변경하지 않음 |
| `sav_dir` | SAV 파일이 있는 폴더. `calc`·`sav-info` 명령에서만 사용 |
| `sav_filename` | 일괄 계산에서 읽을 SAV 파일명. 철자와 띄어쓰기가 실제 파일명과 같아야 함. `calc` 명령에서만 사용 |
| `history_filename` | 일괄 계산에서 읽을 **과거 데이터 엑셀 파일명**. `sav_dir` 폴더 안에 있어야 함. `calc` 명령에서만 사용 |
| `output_dir` | 일괄 계산 결과를 저장할 폴더 |
| `output_filename` | 결과 CSV 파일명 |
| `history_output` | 이번 차수가 더해진 **엑셀을 저장할 경로**. 다음 차수 입력으로 사용 |
| `result_column` | 추가할 보고 차수. `26년 6차`와 같은 `NN년 N차` 형식이며 차수는 1~12 |
| `dashboard_banners` | 응답자를 전체·지역·Tier별로 나누는 기준 |
| `dashboard_template` | 대시보드의 화면 구성(레이아웃·스크립트)을 담은 기준 HTML 경로. EXE 빌드 시에도 이 값을 사용함. 웹 변환에서는 이 파일의 지표 값을 쓰지 않고 엑셀 값으로 새로 채움 |
| `dashboard_output` | 새 차수가 추가된 HTML을 저장할 경로 |
| `overview` | 대시보드 `조사 설계` 장표에 넣을 값 묶음. 아래 4-4 참고 |

웹 화면에서는 두 파일을 직접 업로드하므로 `sav_dir`·`sav_filename`·`history_filename`·`history_output`을 **전혀 사용하지 않습니다**. 이 값들이 없는 파일을 가리켜도 웹 변환은 정상 동작합니다. 반면 `spec_path`, `dashboard_banners`, `dashboard_template`은 웹 변환에도 사용되므로 올바르게 지정되어 있어야 합니다.

### 4-3. 새 조사 차수로 변경할 때

`python main.py calc`로 일괄 계산할 때는 보통 다음 값을 함께 변경합니다.

```json
"sav_filename": "새로운파일.SAV",
"history_filename": "PsO_history_26년6차.xlsx",
"output_filename": "results_26년7차.csv",
"history_output": "results/PsO_history_26년7차.xlsx",
"result_column": "26년 7차",
"dashboard_output": "results/PsO_dashboard_26년7차.html"
```

`history_filename`에는 **지난 차수에서 만들어진 엑셀**을 넣습니다. 위 예시처럼 26년 7차를 계산한다면, 26년 6차 계산 결과로 나온 `PsO_history_26년6차.xlsx`를 `db` 폴더에 옮겨 두고 그 이름을 적습니다.

주의 사항:

- JSON의 문자열은 큰따옴표(`"`)로 감쌉니다.
- 각 항목 뒤의 쉼표를 실수로 지우지 않습니다.
- Windows 경로 대신 `db/파일명.html`처럼 프로젝트 기준 상대경로를 사용합니다.
- 엑셀에 같은 차수가 이미 있으면 중복 차수 오류가 발생합니다.
- `result_column`이 엑셀의 마지막 차수보다 앞서면 오류가 발생합니다.

### 4-4. overview (조사 설계)

`python main.py calc`로 만들 때 대시보드 `조사 설계` 장표에 들어갈 값입니다. 웹 화면에서 입력하는 항목과 같습니다.

```json
"overview": {
    "target": [
        "400베드 이상의 종합병원에 근무하는 피부과 전문의",
        "전문의 경력 5년 이상인 자",
        "한 달에 50명 이상의 건선 환자를 진료 하는 자"
    ],
    "sample": "N = 35",
    "region": "전국",
    "method": "한국리서치 닥터 패널을 활용한 온라인 조사",
    "fieldwork_start": "2025-01-01",
    "fieldwork_end": "2026-05-12"
}
```

| 항목 | 설명 |
|---|---|
| `target` | 조사 대상. 여러 줄이면 대괄호 안에 한 줄씩 나열 |
| `sample` | 표본 크기 |
| `region` | 조사 지역 |
| `method` | 자료 수집 방법 |
| `fieldwork_start` · `fieldwork_end` | 실사 시작일·종료일. `YYYY-MM-DD` 형식 |

실사 기간은 `2025년 1월 1일 ~ 2026년 5월 12일`처럼 자동으로 바뀝니다. 종료일이 시작일보다 앞서거나 형식이 틀리면 오류로 알려 줍니다.

> `overview` 항목을 아예 빼면 기준 HTML에 적힌 값을 그대로 사용합니다.
> 웹 화면에서는 이 설정을 쓰지 않고 화면에서 입력한 값을 사용합니다.

### 4-5. dashboard_banners

배너는 같은 지표를 어떤 응답자 그룹으로 나눠 계산할지 정합니다.

```json
{"name": "수도권", "column": "Area", "values": [1]}
```

위 설정은 SAV의 `Area` 값이 `1`인 응답자를 수도권으로 계산한다는 의미입니다.

현재 프로그램과 HTML은 다음 순서를 사용하므로 이름과 순서를 임의로 바꾸지 않는 것이 안전합니다.

```text
전체 → 수도권 → 지방 → T1 → T2 → T3
```

### 4-6. metric_spec.csv

`metric_spec.csv`에는 각 지표에 사용할 SAV 변수와 계산 방식이 들어 있습니다.

| 열 | 설명 |
|---|---|
| `구분` | 보고서의 상위 분류 |
| `항목` | 지표 그룹 |
| `문항` | 지표 이름 |
| `SAV 변수` | 계산에 사용할 SAV 변수 또는 산술식 |
| `계산` | `Sum`, `Mean`, `Count`, 계산식 등 |
| `배너조건` | 기준 배너 조건 |

이 파일의 행 순서와 수식은 대시보드 데이터 위치와 연결되므로 담당자 외에는 수정하지 않는 것을 권장합니다. 수정 전에는 반드시 복사본을 보관합니다.

### 4-7. VERSION

`config/VERSION`에는 다음처럼 한 줄만 작성합니다.

```text
1.2.0
```

버전을 변경한 뒤 EXE를 다시 빌드하면 새 버전이 EXE 파일명과 웹 화면에 반영됩니다.

---

## 5. 기타 실행 파일과 유틸리티

이 장의 명령은 가상환경이 활성화된 프로젝트 폴더에서 실행합니다.

### 5-1. main.py 명령

| 명령 | 역할 |
|---|---|
| `python main.py web` | 웹 변환 화면 실행. SAV를 화면에서 업로드하므로 `db` 폴더에 SAV가 없어도 됨 |
| `python main.py calc --banner` | `settings.json`의 엑셀과 SAV로 CSV·HTML·엑셀을 `results`에 저장. `db` 폴더에 두 파일 필요 |
| `python main.py sav-info` | `db` 폴더의 SAV 응답자 수, 변수 수와 앞부분 데이터 확인. `db` 폴더에 SAV 필요 |
| `python main.py -h` | 명령 도움말 표시 |

#### 웹 화면 없이 일괄 계산

```bash
python main.py calc --banner
```

웹 화면과 **같은 방식**으로 동작합니다. `settings.json`의 `history_filename`(과거 데이터 엑셀)과 `sav_filename`(이번 차수 SAV)을 읽어 다음 세 가지를 만듭니다.

| 결과 | 저장 위치를 정하는 설정 |
|---|---|
| HTML 대시보드(전체 차수) | `dashboard_output` |
| **엑셀(이번 차수 추가)** | `history_output` |
| CSV 계산 결과 | `output_dir` + `output_filename` |

두 파일 모두 `sav_dir`(기본값 `db`) 폴더에 있어야 합니다. PDF와 PPTX가 필요하면 웹 화면을 사용합니다.

#### SAV 파일 정보 확인

```bash
python main.py sav-info
```

SAV가 정상적으로 열리는지, 응답자와 변수 개수가 맞는지 빠르게 확인할 때 사용합니다.

### 5-2. scripts 폴더

| 파일 | 실행 방법 | 역할 |
|---|---|---|
| `scripts/run_converter.bat` | 더블클릭 | Windows에서 웹 프로그램 실행 |
| `scripts/build_exe.bat` | 더블클릭 또는 `.\scripts\build_exe.bat` | 배포용 EXE 생성 |
| `scripts/PsO_Dashboard_Converter.spec` | 직접 실행하지 않음 | PyInstaller가 읽는 EXE 구성 파일 |
| `scripts/run_dev.sh` | `./scripts/run_dev.sh` | macOS/Linux 개발 환경에서 웹 실행 |

### 5-3. 직접 실행 가능한 내부 모듈

일반 사용자는 `main.py` 명령을 사용하는 것이 안전합니다. 아래 명령은 점검 또는 관리 작업에 사용합니다.

| 명령 | 역할 |
|---|---|
| `python -m src.utils.read_sav` | `db` 폴더의 SAV 파일 정보 출력 |
| `python -m src.metrics.calc_metrics` | 설정에 따라 지표를 계산하고 CSV 저장 |
| `python -m src.dashboard.build_dashboard` | 설정에 따라 새 HTML 대시보드 생성 |
| `python -m src.utils.export_spec` | 지정된 Excel Summary 시트를 `metric_spec.csv`로 다시 내보냄 |

`export_spec`은 특별히 주의해야 합니다. 코드 안에 지정된 Excel 파일이 있어야 하며, 실행하면 기존 `config/metric_spec.csv`를 덮어씁니다. 담당자의 지시가 없으면 실행하지 마세요.

### 5-4. 주요 내부 파일의 역할

| 파일 | 역할 |
|---|---|
| `src/metrics/calc_metrics.py` | 지표 계산 핵심 로직 |
| `src/dashboard/web_app.py` | 업로드와 다운로드를 제공하는 로컬 웹 서버 |
| `src/dashboard/build_dashboard.py` | 기존 HTML에 새 조사 차수 추가 |
| `src/dashboard/generate_pdf.py` | PDF 보고서 생성 |
| `src/dashboard/generate_pptx.py` | 편집 가능한 PowerPoint 표·차트 생성 |
| `src/dashboard/browser_capture.py` | Microsoft Edge로 HTML 표와 차트 정보 추출 |
| `src/utils/banner.py` | 전체·지역·Tier 배너 필터 적용 |
| `src/utils/logger.py` | 콘솔에 진행 상황과 오류 출력 |

### 5-5. 테스트 실행

코드나 HTML을 수정했다면 테스트를 실행합니다.

```bash
python -m pytest tests -q
```

`passed`가 표시되고 `failed`가 없으면 테스트가 통과한 것입니다.

---

## 6. 자주 발생하는 문제

### SAV 파일을 찾을 수 없습니다

이 오류는 `python main.py calc` 또는 `python main.py sav-info`에서만 발생합니다. 웹 화면에서는 SAV를 직접 업로드하므로 이 오류가 나지 않습니다.

- `db` 폴더에 SAV 파일이 있는지 확인합니다.
- `settings.json`의 `sav_filename`과 실제 파일명이 정확히 같은지 확인합니다.
- 괄호, 띄어쓰기, `.sav` 확장자까지 확인합니다.

### 이미 존재하는 차수입니다 (엑셀)

올린 엑셀에 같은 차수가 이미 들어 있습니다. 보고 차수를 확인하거나, 그 차수가 아직 없는 엑셀을 사용합니다.

### 새 차수가 엑셀의 마지막 차수보다 앞섭니다

`26년 6차`를 입력해야 하는데 `25년 6차`처럼 잘못 입력한 경우입니다. 보고 차수를 다시 확인합니다.

### 엑셀의 지표 순서가 metric_spec.csv와 다릅니다

다른 버전의 엑셀을 올렸을 때 나옵니다. 지표 행 순서가 어긋난 채로 계산하면 값이 잘못 들어가므로 프로그램이 미리 막습니다. 담당자에게 받은 최신 엑셀을 사용합니다.

### 과거 데이터 엑셀을 선택해 주세요

엑셀 없이 변환할 수 없습니다. 지난 차수 변환에서 내려받은 엑셀을 올립니다. 처음 사용하는 경우 담당자에게 기준 엑셀을 받습니다.

### 보고 차수 형식 오류

다음과 같은 형식을 사용해야 합니다.

```text
26년 6차
```

차수는 1부터 12까지만 사용할 수 있습니다.

### 이미 존재하는 차수 오류

기준 HTML에 같은 차수가 이미 들어 있습니다. `result_column`을 확인하거나 중복되지 않은 기준 HTML을 사용합니다.

### PDF 또는 PPTX가 생성되지 않습니다

- Microsoft Edge가 설치되어 있는지 확인합니다.
- 열려 있는 Edge와 프로그램을 모두 닫은 뒤 다시 시도합니다.
- EXE의 검은색 콘솔 창에 표시된 오류를 확인합니다.

### PowerPoint에서 복구 메시지가 나옵니다

최신 버전의 EXE로 다시 PPTX를 생성합니다. 이전 버전으로 만든 PPTX를 재사용하지 않습니다.

### 가상환경을 찾을 수 없습니다

프로젝트 폴더에서 다음 명령으로 다시 만듭니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements/dev.txt
```

### 웹페이지를 닫았는데 다시 실행되지 않습니다

이전에 실행한 검은색 콘솔 창이 남아 있는지 확인합니다. 남아 있다면 닫은 후 다시 실행합니다.

---

## 7. 폴더 구조

```text
e2e_converter/
├── main.py                   # 기본 실행 파일
├── config/
│   ├── settings.json         # 입력·출력 및 배너 설정
│   ├── metric_spec.csv       # 지표 계산 규칙
│   └── VERSION               # 프로그램 버전
├── db/                       # 기준 HTML을 넣는 폴더 (SAV는 calc/sav-info 명령을 쓸 때만 필요)
├── results/                  # 일괄 계산 및 확인용 결과
├── release/                  # 빌드된 EXE
├── requirements/             # Python 패키지 목록
├── scripts/                  # 웹 실행 및 EXE 빌드 스크립트
├── src/                      # 프로그램 코드
├── tests/                    # 자동 테스트
└── docs/                     # 개발자용 상세 문서
```

## 8. 변경 이력

### 1.2.0

**과거 데이터를 엑셀로 관리하도록 바꿨습니다 (가장 큰 변화)**

- 이제 변환에 **과거 데이터 엑셀과 SAV 두 파일**이 필요합니다. 엑셀이 없으면 변환할 수 없습니다.
- 지난 차수 값은 **엑셀이 정본**이 되고, 대시보드 HTML에는 값을 저장하지 않습니다.
- 결과로 **이번 차수가 추가된 엑셀**을 함께 내려받아 다음 달 입력으로 씁니다.
- 이전 방식(기준 HTML에 차수를 계속 덧붙이는 방식)에서는 기준 HTML을 매번 교체하지 않으면 과거 차수가 사라졌는데, 그 문제가 없어졌습니다.
- `python main.py calc`도 같은 방식으로 동작합니다. `settings.json`에 `history_filename`·`history_output`을 추가해 엑셀을 읽고 갱신된 엑셀을 남깁니다.

**입력 화면**

- 보고 차수를 숫자로 고릅니다. 엑셀에 없는 **바로 다음 차수**가 자동으로 채워집니다(26년 12차 다음은 27년 1차).
- 실사 기간을 달력으로 고릅니다. 시작일은 **엑셀의 첫 차수 기준**, 종료일은 **오늘**이 기본값입니다.
- `조사 설계` 장표의 내용(조사 대상·표본 크기·조사 지역·자료 수집 방법·실사 기간)을 생성 전에 직접 입력할 수 있습니다.
- 확장자가 틀린 파일을 올리면 그 자리에서 바로 알려 줍니다.

**저장**

- 모든 내려받기에서 **저장 위치와 파일 이름을 지정하는 창**이 열립니다(장표 이미지 저장 포함).
- PDF·PPTX도 저장 위치를 고를 수 있게 고쳤습니다. 이전에는 만드는 데 시간이 걸리는 동안 권한이 만료돼 기본 다운로드 폴더로 떨어졌습니다.
- 만드는 동안 안내 상자가 깜빡여 진행 중임을 알 수 있습니다.

**대시보드 화면**

- Wave 오른쪽에 `% 표시` 토글이 생겼습니다. 비율 값에만 `%`가 붙고 장표마다 따로 적용됩니다.
- 왼쪽 메뉴가 본문과 따로 스크롤됩니다.
- 표의 값과 그래프 범례, 합계 행의 숫자가 세로 가운데로 정렬됩니다.
- 그래프에서 조각이 얇아 숫자가 넘칠 때, **맨 위 조각만** 막대 위로 빼서 표시합니다. 값은 하나도 감추지 않습니다.
- 조사 설계 장표의 `장표 이미지 저장` 버튼이 상단 바에 가려지던 문제를 고쳤습니다.

**PDF · PPTX**

- 표가 긴 장표(브랜드별 처방 비율 등)에서 표와 아래 각주가 겹치던 문제를 고쳤습니다.
- 표 글자 크기를 실제 필요한 높이에 맞춰 정하도록 바꿔, 표가 잘리거나 넘치지 않습니다.

### 1.1.1

- 장표 이미지 저장, PDF·PPTX 생성 기능

---

## 9. 개발자용 추가 문서

- [아키텍처](docs/ARCHITECTURE.md)
- [대시보드 인수인계 문서](docs/DASHBOARD_HANDOVER.md)
- [개발 계획](docs/PLAN.md)

현재 프로그램 버전은 [config/VERSION](config/VERSION)에서 확인할 수 있습니다.
