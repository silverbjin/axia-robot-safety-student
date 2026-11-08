# Windows 10/11 → WSL2 → Ubuntu 24.04 → ROS 2 Jazzy → Gazebo Harmonic

목표: **D03 P1 MVP 기반 ROS Diagnostics·Safe Mode 교육용 개발 환경** 설치. 호스트 OS가 Windows라고 해서 ROS 2 Jazzy/ Gazebo Harmonic을 Windows에 직접 설치하는 것이 아닙니다. Linux용 환경을 WSL2에 만듭니다.

## 준비 조건

- 64비트 Windows 11 또는 Windows 10 **버전 2004 / 빌드 19041 이상** (`Win+R → winver`). 최신 보안 업데이트 권장.
- BIOS/UEFI 가상화 활성화; CPU SLAT 지원. 관리자 PowerShell 사용 가능.
- 교육용 권장: RAM 16GB 이상, 저장공간 여유 25~40GB 이상 (패키지에 따라 달라짐). 숫자는 설치 여유를 위한 권장치, 공식 최소값이 아닙니다.
- 새 교육용 WSL 환경은 **Ubuntu-24.04**라는 별도 배포판을 설치하며 기존 Ubuntu-22.04, Humble, 기존 WSL 배포판은 제거하지 않습니다.

## STEP 1 — Windows PowerShell (관리자) 새 창

1. ZIP 압축해제 (예: `C:\Users\<WindowsUser>\Downloads\AXIA_D03_ENV_SETUP_20261107`).
2. 시작 메뉴 → PowerShell → **관리자 권한으로 실행**.
3. 현재 폴더로 이동한 후 아래 명령을 실행:

```powershell
cd "$HOME\Downloads\AXIA_D03_ENV_SETUP_20261107"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\install_wsl_ubuntu2404.ps1
```

`-Scope Process`는 이 PowerShell 창에만 적용됩니다. 스크립트 내용을 확인한 뒤 실행하세요. 정책 변경이 금지된 기관 PC라면 관리자에게 문의합니다.

예상 메시지: `[STEP 1] Checking WSL`, `[STEP 3] Installing Ubuntu-24.04`, `wsl --list --verbose`의 `Ubuntu-24.04` 및 `VERSION 2`. Windows 재시작이 요구되면 재부팅 후 위 명령을 다시 실행합니다. 설치가 끝나면 **Ubuntu-24.04**를 시작해 Linux 사용자 ID와 비밀번호를 직접 설정합니다. 사용자는 `sudo` 비밀번호를 입력할 때 화면에 글자가 보이지 않아도 정상입니다.

**중요:** `wsl --unregister`는 사용자의 기존 데이터까지 삭제하므로 이 교육 절차에서 사용하지 않습니다. Ubuntu-24.04가 기존에 있으면 스크립트는 삭제·초기화하지 않습니다.

## STEP 2 — PowerShell (일반 권한 가능)에서 버전 확인

```powershell
wsl --version
wsl --list --verbose
wsl --distribution Ubuntu-24.04
```

마지막 명령을 실행하면 터미널 프롬프트가 `user@PC:~$` 형식으로 변합니다. **이후 명령은 Ubuntu Bash에서 실행**합니다. `wsl --list --verbose`에서 Ubuntu-24.04의 VERSION이 1이면 다음으로 변경하되 변환 중에는 해당 배포판을 종료해야 합니다:

```powershell
wsl --set-version Ubuntu-24.04 2
```

## STEP 3 — Ubuntu 24.04 Bash 터미널

Windows 다운로드 폴더의 설치 패키지를 Ubuntu HOME으로 복사합니다. `$USER`는 Linux 사용자이며 Windows 사용자명과 다를 수 있습니다.

```bash
# 아래 <WindowsUser>를 자신의 Windows 계정 폴더명으로 변경
cp -a "/mnt/c/Users/<WindowsUser>/Downloads/AXIA_D03_ENV_SETUP_20261107" "$HOME/"
cd "$HOME/AXIA_D03_ENV_SETUP_20261107"
cat /etc/os-release | grep PRETTY_NAME
uname -m
bash scripts/install_ubuntu2404_jazzy_harmonic.sh
```

기대: Ubuntu 24.04, x86_64, 마지막 `[PASS] INSTALLATION_CLI_READY`. 이 스크립트는 필요한 apt 패키지 설치와 `.bashrc`에 `/opt/ros/jazzy/setup.bash` 한 줄 추가를 수행합니다. 이미 설치된 ROS apt 소스는 재설치하지 않습니다. **ROS/Gazebo runtime 통합검증 완료 메시지는 아닙니다.**

## STEP 4 — Ubuntu 24.04 Bash 새 터미널 (검증용)

```bash
source /opt/ros/jazzy/setup.bash
bash ~/AXIA_D03_ENV_SETUP_20261107/scripts/verify_environment.sh
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus
gz sim --versions
```

기대: `[PASS] ENV_CLI_READY`, `DiagnosticStatus`에 `OK=0/WARN=1/ERROR=2/STALE=3`, Gazebo Sim `8.x`. 패키지 실행·GUI 검증이 아니라 설치 검증입니다.

**GUI 선택 시연**: 첫 수업에서 Gazebo GUI는 필수가 아닙니다. WSLg에서 표시 오류나 렌더 충돌이 있으면 CLI 수업을 우선하고, 담당 강사에게 로그를 제출합니다. 실제 Gazebo world·Nav2 Goal·fault injection 시연은 P1 운영 게이트와 강사 사전 승인 이후로 분리합니다.

## STEP 5 — D03 학생 실습 (별도 Terminal, 순수 Python)

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/axia_d03_ws && cd ~/axia_d03_ws
# 배포 승인 이후 학생 repo 복제. 현재 실습 브랜치는 Draft PR preview.
git clone --branch feat/block-a-d01-d03-todo-20261106 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git student
cd student
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
```

예상 초기 RED: `10 failed, 1 passed`, `exit=1`. 이것은 고장난 설치가 아니라 아직 완료하지 않은 TODO의 의도적 실패입니다. 전체 요구사항에 맞게 코드를 구현하고 재실행하여 GREEN을 목표로 합니다.

현재 학생 저장소의 실습은 **합성 Python 진단 상태 후보 판정**입니다. P1 Diagnostics Adapter는 개편 기획에 포함됐지만 코드와 테스트는 추가 구현·배포 전이므로 아직 실행할 수 없습니다.

## 종료/재진입

실습 종료 후 새 Ubuntu 터미널이 필요하지 않으면 `exit`. Windows에서 WSL 전체 종료는 `wsl --shutdown`이지만 다른 WSL 배포판까지 중단되므로 수업 중 무분별하게 실행하지 않습니다. 다음날 Ubuntu-24.04를 열면 `.bashrc`가 ROS Jazzy를 자동 source합니다.

## Windows 10 참고

WSL2 설치 가능 여부와 **현재 Docker Desktop이 공식 지원하는 Windows 10 에디션·빌드**는 다릅니다. WSL2 네이티브 실습이 가능하더라도 Docker Desktop 최신 버전이 Windows 10을 지원하지 않을 수 있으니 Docker 경로는 별도로 확인하세요.