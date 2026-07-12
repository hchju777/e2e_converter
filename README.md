# PsO Dashboard Converter

SPSS 설문 데이터(`.sav`)를 읽어 지표를 계산하고 다음 결과물을 만드는 Windows 프로그램입니다.

- HTML 대시보드
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

프로젝트의 `db` 폴더에 다음 파일을 넣습니다.

1. 계산할 SPSS `.sav` 파일
2. 기준 대시보드 HTML 파일(현재 기본값: `PsO_dashboard_v4.html`)

예시 구조:

```text
e2e_converter/
├── db/
│   ├── 설문데이터.SAV
│   └── PsO_dashboard_v4.html
├── config/
├── main.py
└── ...
```

그다음 `config/settings.json`의 파일명을 실제 파일명과 맞춥니다. 자세한 내용은 [4. config 설명](#4-config-설명)을 참고합니다.

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
- `config/VERSION`에 버전이 `1.1.1`처럼 `숫자.숫자.숫자` 형식으로 작성됨
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
[SUCCESS] release\PsO_Dashboard_Converter_v1.1.1.exe
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

### 3-2. SAV 파일 변환

1. 점선 업로드 영역을 클릭하거나 `.sav` 파일을 끌어다 놓습니다.
2. 보고 차수를 입력합니다. 예: `26년 6차`
3. `대시보드 생성` 버튼을 누릅니다.
4. 계산이 끝날 때까지 기다립니다.
5. 필요한 파일의 다운로드 버튼을 누릅니다.

다운로드할 수 있는 파일:

| 결과 | 설명 |
|---|---|
| HTML | 브라우저에서 확인하는 대시보드 |
| CSV | 배너별 지표 계산 결과 |
| PDF | 인쇄 및 공유용 보고서 |
| PPTX | 표와 차트를 PowerPoint에서 편집할 수 있는 발표자료 |

PDF/PPTX는 처음 다운로드할 때 생성되므로 시간이 조금 더 걸릴 수 있습니다. PDF/PPTX 생성에는 Windows의 Microsoft Edge가 필요합니다.

### 3-3. HTML 대시보드 사용

HTML을 열면 왼쪽 메뉴에서 조사 설계, 건선 환자, 브랜드 처방, MSL Detailing, Small group 등의 장표로 이동할 수 있습니다.

- 배너가 있는 장표에서는 `전체`, `수도권`, `지방`, `T1`, `T2`, `T3`을 선택할 수 있습니다.
- Wave 선택 메뉴에서 표시할 조사 차수를 바꿀 수 있습니다.
- 각 장표 위의 `장표 이미지 저장` 버튼을 누르면 현재 보이는 표 또는 그래프가 PNG로 저장됩니다.
- 이미지에는 현재 선택한 배너와 Wave가 반영됩니다.

### 3-4. 웹 프로그램 종료

웹페이지 탭만 닫으면 서버는 계속 실행될 수 있습니다. 프로그램을 완전히 종료하려면 처음 실행할 때 열린 검은색 콘솔 창을 닫거나 `Ctrl+C`를 누릅니다.

### 3-5. 웹 화면이 열리지 않을 때

- 이전에 실행한 EXE나 콘솔 창이 남아 있는지 확인하고 모두 닫습니다.
- 브라우저에서 `http://127.0.0.1:8765`를 직접 입력합니다.
- Windows 방화벽 안내가 나오면 로컬 실행을 허용합니다.
- 8765 포트를 다른 프로그램이 사용 중이면 해당 프로그램을 종료합니다.

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
| `sav_dir` | SAV 파일이 있는 폴더 |
| `sav_filename` | 일괄 계산에서 읽을 SAV 파일명. 철자와 띄어쓰기가 실제 파일명과 같아야 함 |
| `output_dir` | 일괄 계산 결과를 저장할 폴더 |
| `output_filename` | 결과 CSV 파일명 |
| `result_column` | 추가할 보고 차수. `26년 6차`와 같은 `NN년 N차` 형식이며 차수는 1~12 |
| `dashboard_banners` | 응답자를 전체·지역·Tier별로 나누는 기준 |
| `dashboard_template` | 새 차수를 추가할 기준 HTML 경로. EXE 빌드 시에도 이 값을 사용함 |
| `dashboard_output` | 새 차수가 추가된 HTML을 저장할 경로 |

웹 화면에서 SAV를 직접 업로드하는 경우 `sav_filename`은 사용하지 않습니다. 하지만 `spec_path`, `dashboard_banners`, `dashboard_template`은 웹 변환에도 사용됩니다.

### 4-3. 새 조사 차수로 변경할 때

보통 다음 네 값을 함께 변경합니다.

```json
"sav_filename": "새로운파일.SAV",
"output_filename": "results_26년7차.csv",
"result_column": "26년 7차",
"dashboard_output": "results/PsO_dashboard_26년7차.html"
```

주의 사항:

- JSON의 문자열은 큰따옴표(`"`)로 감쌉니다.
- 각 항목 뒤의 쉼표를 실수로 지우지 않습니다.
- Windows 경로 대신 `db/파일명.html`처럼 프로젝트 기준 상대경로를 사용합니다.
- 기준 HTML에 같은 차수가 이미 있으면 중복 차수 오류가 발생합니다.

### 4-4. dashboard_banners

배너는 같은 지표를 어떤 응답자 그룹으로 나눠 계산할지 정합니다.

```json
{"name": "수도권", "column": "Area", "values": [1]}
```

위 설정은 SAV의 `Area` 값이 `1`인 응답자를 수도권으로 계산한다는 의미입니다.

현재 프로그램과 HTML은 다음 순서를 사용하므로 이름과 순서를 임의로 바꾸지 않는 것이 안전합니다.

```text
전체 → 수도권 → 지방 → T1 → T2 → T3
```

### 4-5. metric_spec.csv

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

### 4-6. VERSION

`config/VERSION`에는 다음처럼 한 줄만 작성합니다.

```text
1.1.1
```

버전을 변경한 뒤 EXE를 다시 빌드하면 새 버전이 EXE 파일명과 웹 화면에 반영됩니다.

---

## 5. 기타 실행 파일과 유틸리티

이 장의 명령은 가상환경이 활성화된 프로젝트 폴더에서 실행합니다.

### 5-1. main.py 명령

| 명령 | 역할 |
|---|---|
| `python main.py web` | 웹 변환 화면 실행 |
| `python main.py calc --banner` | `settings.json`의 SAV를 계산해 CSV와 HTML을 `results`에 저장 |
| `python main.py sav-info` | `db` 폴더의 SAV 응답자 수, 변수 수와 앞부분 데이터 확인 |
| `python main.py -h` | 명령 도움말 표시 |

#### 웹 화면 없이 일괄 계산

```bash
python main.py calc --banner
```

이 명령은 `settings.json`의 `sav_filename`, `result_column`, 출력 파일명을 사용합니다. PDF와 PPTX 다운로드가 필요하면 웹 화면을 사용합니다.

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

- `db` 폴더에 SAV 파일이 있는지 확인합니다.
- `settings.json`의 `sav_filename`과 실제 파일명이 정확히 같은지 확인합니다.
- 괄호, 띄어쓰기, `.sav` 확장자까지 확인합니다.

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
├── db/                       # SAV와 기준 HTML을 넣는 폴더
├── results/                  # 일괄 계산 및 확인용 결과
├── release/                  # 빌드된 EXE
├── requirements/             # Python 패키지 목록
├── scripts/                  # 웹 실행 및 EXE 빌드 스크립트
├── src/                      # 프로그램 코드
├── tests/                    # 자동 테스트
└── docs/                     # 개발자용 상세 문서
```

## 8. 개발자용 추가 문서

- [아키텍처](docs/ARCHITECTURE.md)
- [대시보드 인수인계 문서](docs/DASHBOARD_HANDOVER.md)
- [개발 계획](docs/PLAN.md)

현재 프로그램 버전은 [config/VERSION](config/VERSION)에서 확인할 수 있습니다.
