#!/usr/bin/env bash
# D06 C27: watch immutable ROS launch native Gazebo child exit before group SIGINT.
# Observer only. No signal, Gazebo, ROS, GPU, config or safety policy changes.
set -Eeuo pipefail
[[ $# == 3 && "$1" == --wait && "$2" == /* && "$3" =~ ^[1-9][0-9]*$ &&
   "$3" -le 30 ]] || {
  echo 'G07_GAZEBO_NATIVE_EXIT_GUARD_USAGE=--wait ABSOLUTE_LAUNCH_LOG SEC_1_TO_30' >&2
  exit 2
}
log="$2"; sec="$3"
deadline=$((SECONDS+sec))
while ((SECONDS<=deadline));do
  if [[ -f "$log" ]];then
    # Never confuse a launch manager marker, service ACK or NAV2 ACK
    # with a successful Gazebo *native child* exit.
    if grep -Eq '^\[ERROR\] +\[gz-[0-9]+\]: process has died .*exit code -11' "$log";then
      echo 'G07_GAZEBO_SERVER_NATIVE_SIGSEGV_BEFORE_GROUP_SIGINT_HOLD' >&2
      exit 3
    fi
    if grep -Eq '^\[ERROR\] +\[gz-[0-9]+\]: process has died ' "$log";then
      echo 'G07_GAZEBO_SERVER_NATIVE_NONCLEAN_BEFORE_GROUP_SIGINT_HOLD' >&2
      exit 3
    fi
    if grep -Eq '^\[INFO\] +\[gz-[0-9]+\]: process has finished cleanly' "$log";then
      echo 'G07_GAZEBO_SERVER_NATIVE_EXIT0_BEFORE_GROUP_SIGINT'
      exit 0
    fi
  fi
  sleep .2
done
echo 'G07_GAZEBO_SERVER_NATIVE_EXIT0_TIMEOUT_HOLD' >&2
exit 3
