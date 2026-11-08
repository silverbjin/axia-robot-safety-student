# D03 Windows 10/11 WSL2 Ubuntu 24.04 설치

필수 실습은 Python 3.12와 pytest만 필요합니다. ROS 2 Jazzy와 Gazebo Harmonic은 선택 설치입니다.

## 관리자 PowerShell

Student D03 브랜치(https://github.com/silverbjin/axia-robot-safety-student/tree/D03)를 Code → Download ZIP으로 내려받아 압축을 푸세요. 압축해제한 저장소 폴더에서 관리자 PowerShell을 엽니다.

~~~powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup\d03\scripts\install_wsl_ubuntu2404.ps1
wsl -l -v
~~~

예상: Ubuntu-24.04 / VERSION 2. 재부팅 요청이 있으면 재부팅 후 다시 확인합니다. wsl --unregister는 사용자의 기존 데이터를 삭제하므로 실행하지 마세요.

## Ubuntu 24.04 터미널

~~~bash
cat /etc/os-release | grep PRETTY_NAME
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
bash block_A/day03/scripts/run_lab.sh preflight
bash block_A/day03/scripts/run_lab.sh red
~~~

예상: preflight 성공, 초기 22 failed / 8 passed / EXPECTED_RED_CONFIRMED. TODO가 미완성이므로 RED는 정상입니다.

## 선택: ROS와 Gazebo 설치

Ubuntu 24.04 x86_64에서만 다음 스크립트를 확인한 후 실행합니다(sudo/apt 설정을 변경함).

~~~bash
bash setup/d03/scripts/install_ubuntu2404_jazzy_harmonic.sh
source /opt/ros/jazzy/setup.bash
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus
gz sim --versions
~~~

이 명령은 설치·CLI 확인이며 실제 Gazebo 구동이나 P1 안전 인수시험을 대신하지 않습니다.
