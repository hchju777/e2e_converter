# PsO Dashboard Converter

SPSS `.SAV` 설문 데이터를 읽어 지표를 계산하고, HTML 대시보드·CSV·PDF·PPTX로 자동 변환해주는 프로그램입니다.

이 문서는 **프로그래밍을 몰라도** 따라 할 수 있도록 처음부터 끝까지 순서대로 설명합니다. 개발자용 상세 문서는 [docs/](docs/) 폴더에 따로 있습니다.

---

## 0. 나에게 맞는 방법 고르기

| 상황 | 추천 방법 |
|---|---|
| 그냥 결과만 뽑으면 된다, Python/Git 설치하기 싫다 | **방법 A: EXE 파일** (아래 1장) |
| `config` 값을 직접 바꾸거나, 코드를 수정/업데이트해야 한다 | **방법 B: 소스 코드로 실행** (아래 2장부터) |

둘 다 최종적으로 같은 프로그램을 실행하는 것이며, 결과물도 동일합니다.

---

## 1. 방법 A — EXE 파일만으로 실행하기 (가장 쉬움)

Python이나 Git을 설치할 필요가 없습니다.

1. `release` 폴더의 `PsO_Dashboard_Converter_v1.0.0.exe` 파일을 전달받습니다.
2. 파일을 더블클릭합니다. 검은색 콘솔 창이 뜨고, 잠시 후 자동으로 웹 브라우저가 열립니다.
   - 브라우저가 자동으로 열리지 않으면 주소창에 `http://127.0.0.1:8765` 를 직접 입력합니다.
3. 화면 안내에 따라 사용합니다. (사용법은 [5장 웹 화면 사용법](#5-웹-화면-사용법)과 동일합니다.)
4. 사용이 끝나면 콘솔 창을 닫으면 프로그램이 종료됩니다.

> Windows가 "알 수 없는 게시자" 경고를 띄우면 `추가 정보` → `실행`을 눌러 진행하면 됩니다. 사내 배포용 프로그램이라 정식 서명이 없어 나타나는 정상적인 경고입니다.

이 방법만 쓸 사람은 여기서 끝입니다. 아래 2장부터는 소스 코드로 직접 실행하거나 개발/수정하려는 경우에 필요합니다.

---

## 2. 방법 B — 소스 코드로 실행하기

### 2-1. 필요한 프로그램 설치

#### ① Git (그리고 Git Bash)

1. [Git for Windows](https://git-scm.com/install/windows)에서 64비트 설치 파일을 내려받아 실행합니다.
2. 특별한 사내 규정이 없다면 설치 중 기본값을 그대로 두고 진행합니다.
3. 설치가 끝나면 시작 메뉴에서 `Git Bash`를 실행해 아래 명령으로 확인합니다.

   ```bash
   git --version
   ```

   `git version ...` 문구가 나오면 정상입니다.

#### ② Python

Python 3.12 또는 3.13 (64비트)을 권장합니다.

1. [Python 공식 다운로드](https://www.python.org/downloads/windows/)에서 64비트 Windows Installer를 내려받습니다.
2. 설치 화면 맨 아래 **`Add python.exe to PATH`** 체크박스를 반드시 선택합니다. (이걸 빠뜨리면 이후 명령어가 전부 동작하지 않습니다.)
3. `Install Now`로 설치합니다.
4. 열려 있던 Git Bash 창을 모두 닫았다가 새로 열고 확인합니다.

   ```bash
   python --version
   ```

   `Python 3.x.x`가 나오면 정상입니다. "명령을 찾을 수 없다"고 나오면 PC를 재시작하거나, Python 설치를 `Add to PATH` 체크와 함께 다시 진행하세요.

#### ③ Visual Studio Code (선택, 권장)

명령어를 입력할 터미널과 파일을 볼 편집기가 필요합니다. 이미 편한 도구가 있다면 건너뛰어도 됩니다.

1. [VS Code 다운로드](https://code.visualstudio.com/download)에서 Windows용 `User Installer`를 설치합니다.
2. 설치 중 `Add to PATH`, `Open with Code`를 선택합니다.
3. VS Code를 실행하고 왼쪽 Extensions 아이콘에서 Microsoft의 `Python` 확장을 설치합니다.

### 2-2. 프로젝트 내려받기 (git clone)

원하는 위치(예: 바탕화면)에서 Git Bash를 열고 아래 명령을 실행합니다. `<저장소 주소>`는 GitHub 저장소 페이지의 초록색 `Code` 버튼 → `HTTPS`에서 복사한 주소로 바꿔주세요.

```bash
cd /c/Users/사용자이름/Desktop
git clone <저장소 주소>
cd e2e_converter
```

예시:

```bash
git clone https://github.com/company/e2e_converter.git
cd e2e_converter
```

비공개 저장소라면 GitHub 로그인 정보를 요구할 수 있습니다.

이후 VS Code로 폴더를 열면 편합니다.

```bash
code .
```

`code` 명령이 안 먹히면 VS Code를 직접 실행한 뒤 `File > Open Folder`에서 방금 내려받은 `e2e_converter` 폴더를 선택합니다.

### 2-3. 가상환경 만들기와 패키지 설치

"가상환경"은 이 프로젝트 전용 Python 실행 공간입니다. 시스템 Python을 건드리지 않고 필요한 패키지만 이 폴더 안에 설치해두는 것이라고 생각하면 됩니다. 프로젝트 폴더(`e2e_converter`) 안에서 실행해야 합니다.

VS Code에서 `Terminal > New Terminal`로 터미널을 엽니다. 기본이 PowerShell인 경우:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

Git Bash를 쓴다면 활성화 명령만 다릅니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

터미널 맨 앞에 `(.venv)`가 붙으면 가상환경이 켜진 것입니다. 이후 모든 명령은 이 상태에서 실행합니다.

> PowerShell에서 "이 시스템에서 스크립트를 실행할 수 없습니다"라는 오류가 나오면, PowerShell 대신 Git Bash를 쓰는 것이 가장 간단합니다.

**직접 이 프로그램을 수정하거나(코드 변경), EXE로 다시 빌드하거나, 테스트를 돌려볼 사람**은 개발용 패키지도 추가로 설치합니다.

```powershell
python -m pip install -r requirements/dev.txt
```

`requirements/dev.txt`에는 `requirements/base.txt`의 모든 내용에 더해 `pyinstaller`(EXE 빌드), `pytest`(테스트), `black`/`flake8`(코드 검사)가 포함됩니다.

### 2-4. 입력 파일 준비하기

`db` 폴더와 `results` 폴더는 용량이 크고 민감한 실데이터가 들어가기 때문에 Git 저장소에 포함되어 있지 않습니다. `git clone` 직후에는 두 폴더가 비어 있으므로 아래 파일을 직접 채워 넣어야 합니다.

1. 프로젝트 폴더 안에 `db` 폴더가 없다면 새로 만듭니다.
2. 계산할 `.SAV` 설문 원본 파일을 `db` 폴더에 복사합니다.
3. 대시보드(HTML)를 만들려면, 과거 차수가 누적된 기준 파일 `PsO_dashboard_v4 (2).html`도 `db` 폴더에 함께 둡니다.
4. `config/settings.json`을 열어 `sav_filename` 값을 방금 넣은 SAV 파일명과 **철자·띄어쓰기·괄호까지 정확히** 똑같이 맞춥니다. (자세한 설명은 바로 다음 3장)

---

## 3. config 폴더 — 무엇을 설정하는 곳인가요

`config` 폴더는 "이 프로그램이 어떤 파일을 읽고, 어떤 이름으로 저장할지"를 정하는 설정 모음입니다. 코드를 건드리지 않고도 이 폴더의 값만 바꾸면 동작이 달라집니다.

| 파일 | 역할 |
|---|---|
| `config/settings.json` | 입력/출력 경로, 파일명, 이번 차수 이름, 배너(그룹) 구성을 정의하는 핵심 설정 파일 |
| `config/metric_spec.csv` | 계산할 지표 329개의 목록과 계산식(SPSS 변수 수식) |
| `config/VERSION` | 프로그램 버전 번호 (예: `1.0.0`). EXE 파일명과 화면에 표시되는 버전에 사용됨 |
| `config/__init__.py` | Python이 이 폴더를 모듈로 인식하게 하는 빈 파일. 직접 열어볼 필요 없음 |

### config/settings.json 자세히 보기

`main.py calc` 명령과 `python -m src.metrics.calc_metrics` 실행 시 이 파일을 읽습니다. (웹 화면 방법은 업로드한 SAV 파일을 그때그때 쓰므로 `sav_filename` 값을 참고하지 않습니다.)

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

| 항목 | 의미 |
|---|---|
| `spec_path` | 지표 정의 CSV(`metric_spec.csv`) 위치. 보통 수정할 필요 없음 |
| `sav_dir` | `.SAV` 파일이 들어있는 폴더 |
| `sav_filename` | 이번에 계산할 SAV 파일명 (`sav_dir` 안에 있어야 함) |
| `output_dir` | 결과 CSV를 저장할 폴더. 없으면 실행할 때 자동 생성됨 |
| `output_filename` | 결과 CSV 파일명 |
| `result_column` | 이번 차수 이름. **`26년 6차`처럼 반드시 "NN년 N차" 형식**이어야 하며, 차수(N차)는 1~12만 허용됨 (내부적으로 1월~12월에 대응) |
| `dashboard_banners` | 대시보드를 나눠 볼 그룹(배너) 목록. `column`은 SAV의 변수명, `values`는 그 변수가 이 값을 가지면 해당 그룹에 포함된다는 뜻 |
| `dashboard_template` | 과거 차수 데이터가 이미 들어있는 기준 대시보드 HTML |
| `dashboard_output` | 새 차수를 추가한 결과 HTML을 저장할 경로 |

**새 차수(회차)가 생길 때마다 보통 `sav_filename`, `output_filename`, `result_column`, `dashboard_output`을 함께 바꿔주면 됩니다.** SAV 파일이 없거나 `result_column` 형식이 틀리면 계산이 시작되지 않고 오류 메시지로 원인을 알려줍니다.

### config/metric_spec.csv 자세히 보기

| 컬럼 | 예시 | 설명 |
|---|---|---|
| `구분` | 조사결과 | 대시보드 상 페이지 그룹 |
| `항목` | 환자규모 | 상위 분류명 |
| `문항` | PsO 환자 규모 | 화면에 표시되는 지표 이름 |
| `SAV 변수` | `Q1 + Q2` | 계산에 쓰일 SPSS 변수 수식 |
| `계산` | Sum | 계산 방식 (`Sum`/`Mean`/`Count`/계산식/`아래 값의 합계`) |
| `배너조건` | 전체 | 이 지표를 어느 배너 조건에 적용할지 |

이 파일은 원래 `db/UCB_...xlsx`의 Summary 시트에서 관리하던 것을, 원본 수식 오타 3건을 고쳐서 CSV로 옮겨 놓은 것입니다. 계산 프로그램은 더 이상 xlsx를 열지 않고 이 CSV만 읽습니다. **직접 수식을 조정해야 한다면 이 CSV를 열어 `SAV 변수` 칸을 수정하면 됩니다.**

> `src/utils/export_spec.py`는 xlsx → csv 최초 변환용 1회성 스크립트입니다. 다시 실행하면 CSV에 직접 손으로 수정해둔 내용이 xlsx 원본 기준으로 덮어써지니, 이미 CSV를 손으로 고쳤다면 재실행하지 마세요.

---

## 4. 실행 파일 총정리 — 무엇을 하고, 어떻게 실행하나요

이 프로젝트를 실행하는 방법은 크게 3층으로 나뉩니다: **① 매일 쓰는 명령/배치파일 → ② main.py가 호출하는 내부 스크립트 → ③ 개발/배포용 스크립트.** 대부분은 ①만 사용하면 됩니다.

### ① 매일 쓰는 실행 방법

모두 가상환경이 켜진 상태(`(.venv)` 표시)에서 프로젝트 루트 폴더(`e2e_converter`, `main.py`가 보이는 위치)에서 실행합니다.

| 명령 | 하는 일 |
|---|---|
| `python main.py web` | **가장 많이 쓰는 명령.** 브라우저 기반 변환 화면을 엽니다. SAV 파일을 업로드하면 HTML/CSV/PDF/PPTX를 만들어 다운로드할 수 있습니다. (5장 참고) |
| `python main.py calc --banner` | `config/settings.json`에 지정된 SAV 파일을 읽어 지표를 계산하고, CSV 결과와 HTML 대시보드를 `results/` 폴더에 바로 저장합니다. 업로드 화면 없이 한 번에 끝내고 싶을 때 씁니다 |
| `python main.py sav-info` | `db` 폴더의 SAV 파일들을 열어 응답자 수, 변수 개수, 앞부분 데이터를 화면에 보여줍니다. 파일이 제대로 읽히는지만 빠르게 확인할 때 씁니다 |
| `python main.py -h` | 사용 가능한 명령 목록을 보여줍니다 |

더블클릭만으로 실행하고 싶다면:

| 파일 | 하는 일 |
|---|---|
| `scripts/run_converter.bat` | 더블클릭하면 `python main.py web`과 동일하게 웹 변환 화면을 엽니다. 터미널을 직접 열기 싫을 때 사용 |

### ② main.py가 내부적으로 사용하는 스크립트 (직접 실행할 일은 거의 없음)

| 파일 | 하는 일 |
|---|---|
| `src/utils/read_sav.py` | `.SAV` 파일을 읽어 표(DataFrame) 형태로 변환하는 공용 함수. `sav-info` 명령이 이걸 사용 |
| `src/metrics/calc_metrics.py` | `metric_spec.csv`의 수식대로 실제 지표를 계산하는 핵심 로직. `calc`, `web` 명령이 공통으로 사용 |
| `src/dashboard/build_dashboard.py` | 계산된 값을 기존 HTML 대시보드의 새 차수 자리에 끼워 넣는 로직 |
| `src/dashboard/generate_pdf.py` / `generate_pptx.py` | 계산 결과로 PDF 보고서 / PPTX 발표자료를 만드는 로직 (웹 화면에서만 사용) |
| `src/dashboard/web_app.py` | 웹 변환 화면(브라우저 UI + 서버)의 실제 구현체. `python main.py web`이 이 파일을 실행 |
| `src/utils/banner.py` | `dashboard_banners` 설정대로 응답자를 그룹(전체/수도권/T1 등)으로 나누는 로직 |
| `src/utils/logger.py` | 화면과 `logs/converter.log` 파일에 진행 상황을 기록하는 공용 로그 도구 |
| `src/utils/export_spec.py` | (3장 마지막 참고) xlsx → `metric_spec.csv` 최초 변환용 1회성 스크립트 |

### ③ 개발자용 스크립트

| 파일 | 하는 일 |
|---|---|
| `scripts/build_exe.bat` | 소스 코드를 하나의 `.exe` 파일로 묶어 `release/` 폴더에 만듭니다. Python이 없는 동료에게 배포할 때 사용. 사전에 `requirements/dev.txt`가 설치되어 있어야 합니다 |
| `scripts/PsO_Dashboard_Converter.spec` | 위 EXE 빌드 시 PyInstaller가 참고하는 설정 파일. 직접 실행하는 파일이 아니라 `build_exe.bat`이 내부적으로 사용 |
| `scripts/run_dev.sh` | Mac/Linux 개발자를 위한 실행 스크립트 (`python main.py web`을 실행). Windows에서는 필요 없음 |

**EXE 다시 만들기:**

```powershell
python -m pip install -r requirements/dev.txt
.\scripts\build_exe.bat
```

완료되면 `release/PsO_Dashboard_Converter_v<버전>.exe`가 생성/갱신됩니다. 버전 번호는 `config/VERSION`을 따릅니다.

**테스트 실행 (코드를 수정한 뒤 정상 동작하는지 확인):**

```powershell
python -m pip install -r requirements/dev.txt
pytest tests/ -v
```

---

## 5. 웹 화면 사용법

`python main.py web` 또는 `scripts/run_converter.bat` 또는 EXE 파일로 서버를 켠 상태에서 브라우저에 `http://127.0.0.1:8765` 로 접속합니다 (보통 자동으로 열립니다).

1. **SAV 파일 올리기** — 점선 박스에 `.sav` 파일을 끌어다 놓거나 클릭해서 선택합니다. (최대 100MB)
2. **보고 차수 입력** — 예: `26년 6차`. 반드시 `NN년 N차` 형식이어야 하고, N차는 1~12 사이여야 합니다. 형식이 틀리면 오류 메시지가 뜹니다.
3. **`🚀 대시보드 생성` 버튼 클릭** — 6개 배너(전체/수도권/지방/T1/T2/T3)를 계산하는 동안 잠시 기다립니다.
4. **완료 후 다운로드** — HTML 대시보드, CSV 결과, PDF 보고서, PPTX 발표자료 4가지를 각각 내려받을 수 있습니다.
5. 0으로 나눈 값 등 계산 경고가 있으면 화면 하단에 노란 박스로 목록이 표시됩니다. (오류는 아니며, 데이터에 해당 값이 없어 결과가 비어있다는 안내입니다.)

파일은 실행 중인 이 PC 안에서만 처리되며 외부로 전송되지 않습니다.

> 이미 다른 프로그램이 8765 포트를 쓰고 있으면 화면이 이상하게 동작할 수 있습니다. 이전에 열어둔 콘솔 창이나 EXE가 남아있지 않은지 확인하고, 있다면 닫은 뒤 다시 실행하세요.

---

## 6. 결과 파일은 어디에 저장되나요

| 방법 | 저장 위치 |
|---|---|
| 웹 화면 (`main.py web`, EXE) | 다운로드 버튼을 눌러야 저장됨 (임시 폴더에 있다가 다운로드 시 지정한 위치로 저장) |
| `python main.py calc --banner` | `config/settings.json`의 `output_dir`(기본 `results/`)에 CSV·HTML이 자동 저장됨 |

또한 모든 실행 기록은 `logs/converter.log`에 남습니다. 결과가 이상하면 먼저 이 로그 파일을 확인하세요.

---

## 7. 자주 발생하는 문제

**"SAV 파일을 찾을 수 없습니다" / 계산이 시작되지 않음**
- `config/settings.json`의 `sav_filename`이 `db` 폴더 안 실제 파일명과 대소문자·띄어쓰기·괄호까지 정확히 일치하는지 확인하세요.

**`result_column`(보고 차수) 형식 오류**
- `26년 6차`처럼 `NN년 N차` 형식이어야 합니다. 차수는 1~12만 가능합니다.

**이미 존재하는 차수라는 오류**
- 대시보드에 이미 같은 차수가 들어있으면 중복 추가를 막기 위해 저장하지 않습니다. 다른 차수 이름을 쓰거나 기준 HTML(`dashboard_template`)을 갱신하세요.

**웹 화면이 브라우저에서 안 열림**
- 방화벽이 막고 있는지 확인하세요.
- 이전에 켜둔 콘솔 창/EXE가 남아 8765 포트를 계속 쓰고 있을 수 있습니다. 모두 닫고 하나만 다시 실행하세요.

**가상환경 활성화가 안 됨 (PowerShell)**
- "이 시스템에서 스크립트 실행이 비활성화되어 있습니다" 오류가 나오면 Git Bash로 `source .venv/Scripts/activate`를 사용하세요.

**계산 결과 값이 이상함**
- `logs/converter.log`를 확인합니다.
- `results/` 폴더 CSV의 `오류`, `경고` 컬럼을 확인합니다.
- `config/metric_spec.csv`의 해당 지표 `SAV 변수` 수식을 확인합니다.

---

## 8. 다음에 다시 실행할 때

한번 설치한 뒤에는 `git clone`이나 패키지 설치를 반복할 필요가 없습니다. VS Code(또는 Git Bash)에서 `e2e_converter` 폴더를 열고, 가상환경만 다시 켠 뒤 원하는 명령을 실행하면 됩니다.

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python main.py web
```

Git Bash:

```bash
source .venv/Scripts/activate
python main.py web
```

모든 명령은 `main.py`가 보이는 프로젝트 루트 폴더에서 실행해야 합니다.

---

## 9. 폴더 구조 한눈에 보기

```
e2e_converter/
├── main.py                 # 실행 시작점 (web / calc / sav-info)
├── config/                 # 설정 파일 (3장 참고)
│   ├── settings.json
│   ├── metric_spec.csv
│   └── VERSION
├── src/                    # 프로그램 코드
│   ├── metrics/            # 지표 계산 로직
│   ├── dashboard/          # 대시보드/PDF/PPTX/웹 화면 생성 로직
│   └── utils/              # SAV 읽기, 배너 분류, 로그 등 공용 함수
├── scripts/                # 배치 파일 (더블클릭 실행, EXE 빌드)
├── db/                     # 입력 SAV/원본 파일 (직접 채워 넣어야 함, Git 미포함)
├── results/                # 계산 결과 CSV/HTML (자동 생성, Git 미포함)
├── release/                # 빌드된 EXE 파일 (Git 미포함)
├── logs/                   # 실행 로그 (자동 생성)
├── requirements/           # 설치할 패키지 목록
├── tests/                  # 자동 테스트
└── docs/                   # 개발자용 상세 문서
```

## 10. 더 알아보기

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 프로젝트 아키텍처, 모듈 구조, 데이터 흐름
- [docs/DASHBOARD_HANDOVER.md](docs/DASHBOARD_HANDOVER.md) — 대시보드 기술 사양 및 개발 가이드
- [docs/PLAN.md](docs/PLAN.md) — SAV 지표 계산 구현 계획

## 라이선스 및 지원

이 프로젝트는 내부 용도로 개발되었습니다. 문의는 프로젝트 관리자에게 연락해주세요.

---

**버전:** `config/VERSION` 참고 (현재 1.0.0)
