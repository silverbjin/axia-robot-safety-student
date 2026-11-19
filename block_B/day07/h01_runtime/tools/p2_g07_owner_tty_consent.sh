#!/usr/bin/env bash
# HFbmAW8N: read EXACTLY ONE human Goal consent from the controlling terminal.
# Source this in the existing Owner runner. CI may pass 1s into this function
# only through a disposable PTY test; production always calls with 180s.
# Do not echo/copy the supplied answer into the persisted native log.
axia_owner_tty_consent() {
  local limit="${1:-}" answer='' code=0 began=${SECONDS}
  if [[ ! "$limit" =~ ^[0-9]+$ ]] || (( limit < 1 || limit > 180 ));then
    echo 'OWNER_GOAL_CONSENT_BAD_TIMEOUT' >&2
    return 2
  fi
  if [[ ! -t 0 || ! -r /dev/tty || ! -w /dev/tty ]];then
    echo 'OWNER_GOAL_CONSENT_TTY_UNAVAILABLE' >&2
    return 2
  fi

  # Durable evidence to redirected native_runner.log, and a prominent prompt
  # to /dev/tty (not stdout, which Owner correctly archives privately).
  printf 'OWNER_GOAL_CONSENT_PENDING timeout_sec=%s goal_sent=false\n' "$limit"
  printf '\a\n=============================================================\n' > /dev/tty || {
    echo 'OWNER_GOAL_CONSENT_TTY_UNAVAILABLE' >&2;return 2;
  }
  printf ' AXIA G07: SIMULATION ONLY — MANUAL GOAL CONSENT REQUIRED\n' > /dev/tty
  printf ' Focus this WSL2 TERMINAL now (not the Gazebo/RViz window).\n' > /dev/tty
  printf ' Type YES-P2-G07-GOAL and press Enter within %s seconds.\n' "$limit" > /dev/tty
  printf ' No Goal will be sent if consent is missing or incorrect.\n' > /dev/tty
  printf '=============================================================\n' > /dev/tty

  if IFS= read -r -t "$limit" answer < /dev/tty;then
    if [[ "$answer" == 'YES-P2-G07-GOAL' ]];then
      printf 'OWNER_GOAL_CONSENT_ACCEPTED elapsed_sec=%s\n' "$((SECONDS-began))"
      unset answer
      return 0
    fi
    echo 'OWNER_GOAL_CONSENT_DENIED' >&2
    unset answer
    return 2
  else
    code=$?
    unset answer
    if (( code > 128 ));then
      printf 'OWNER_GOAL_CONSENT_TIMEOUT elapsed_sec=%s\n' "$((SECONDS-began))" >&2
    else
      printf 'OWNER_GOAL_CONSENT_EOF_OR_TTY_ERROR read_rc=%s\n' "$code" >&2
    fi
    return 2
  fi
}
