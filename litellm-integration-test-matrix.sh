#!/usr/bin/env bash
set -euo pipefail

# Claude Code settings.json + ENV interaction test matrix runner
# Usage:
#   ./test-matrix.sh p0           # Run P0 precedence tests
#   ./test-matrix.sh n1           # Run N1 matrix (direct to sdf-llm)
#   ./test-matrix.sh n2           # Run N2 matrix (SOCKS to llm.sdf)
#   ./test-matrix.sh S1 E1        # Run a single cell
#   ./test-matrix.sh S1           # Run one settings config against all E
#   ./test-matrix.sh all          # Run everything

SETTINGS_FILE="$HOME/.claude/settings.json"
TOKEN_FILE="$HOME/.claude/.token"
TIMEOUT_SECS=30
PROMPT="respond PASS only"
SDF_LLM="https://sdf-llm.slac.stanford.edu"
LLM_SDF="https://llm.sdf.slac.stanford.edu"

# --- Helpers ---

die() { echo "ERROR: $*" >&2; exit 1; }

get_token() {
  [[ -f "$TOKEN_FILE" ]] || die "Token file not found: $TOKEN_FILE"
  cat "$TOKEN_FILE"
}

# Write settings.json env block, preserving hooks and other keys
write_settings_env() {
  local env_json="$1"
  python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f: d = json.load(f)
d['env'] = json.loads(sys.argv[1])
with open('$SETTINGS_FILE', 'w') as f: json.dump(d, f, indent=2)
" "$env_json"
}

# Build env JSON for a given S config
settings_env_for() {
  local sid="$1"
  case "$sid" in
    S1)  echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S2)  echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S3)  echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_AUTH_TOKEN":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S4)  echo '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S5)  echo '{"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S6)  echo '{"ANTHROPIC_BASE_URL":"'"$LLM_SDF"'","ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    S7)  echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1","ANTHROPIC_MODEL":"claude-sonnet-4-20250514"}' ;;
    S8)  echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":""}' ;;
    S9)  echo '{}' ;;
    S10) echo '{"ANTHROPIC_BASE_URL":"'"$SDF_LLM"'","ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"'"$(get_token)"'","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}' ;;
    *)   die "Unknown settings config: $sid" ;;
  esac
}

# Describe S config
describe_s() {
  case "$1" in
    S1)  echo "S1 (full)" ;;
    S2)  echo "S2 (no AUTH_TOKEN)" ;;
    S3)  echo "S3 (no API_KEY)" ;;
    S4)  echo "S4 (no BASE_URL)" ;;
    S5)  echo "S5 (minimal)" ;;
    S6)  echo "S6 (full, llm.sdf)" ;;
    S7)  echo "S7 (full + model)" ;;
    S8)  echo "S8 (no DISABLE)" ;;
    S9)  echo "S9 (empty env)" ;;
    S10) echo "S10 (jwt in settings)" ;;
    *)   echo "$1" ;;
  esac
}

# Describe E config
describe_e() {
  case "$1" in
    E1) echo "E1 (key only)" ;;
    E2) echo "E2 (key + url)" ;;
    E3) echo "E3 (key + url + auth=\"\")" ;;
    E4) echo "E4 (auth_token=jwt + url)" ;;
    E5) echo "E5 (both tokens + url)" ;;
    E6) echo "E6 (key + url + model env)" ;;
    E7) echo "E7 (key + url + --model flag)" ;;
    E8) echo "E8 (key + url + debug)" ;;
    *)  echo "$1" ;;
  esac
}

# Build shell env array for a given E config
# Returns space-separated KEY=VALUE pairs
shell_env_for() {
  local eid="$1"
  local token
  token="$(get_token)"
  case "$eid" in
    E1) echo "ANTHROPIC_API_KEY=$token" ;;
    E2) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_BASE_URL=$SDF_LLM" ;;
    E3) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_BASE_URL=$SDF_LLM ANTHROPIC_AUTH_TOKEN=" ;;
    E4) echo "ANTHROPIC_AUTH_TOKEN=$token ANTHROPIC_BASE_URL=$SDF_LLM" ;;
    E5) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_AUTH_TOKEN=$token ANTHROPIC_BASE_URL=$SDF_LLM" ;;
    E6) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_BASE_URL=$SDF_LLM ANTHROPIC_MODEL=claude-sonnet-4-20250514" ;;
    E7) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_BASE_URL=$SDF_LLM" ;;
    E8) echo "ANTHROPIC_API_KEY=$token ANTHROPIC_BASE_URL=$SDF_LLM DEBUG=claude:* NODE_DEBUG=http,https" ;;
    *)  die "Unknown env config: $eid" ;;
  esac
}

# Run a single claude -p test with timeout
# Args: description, [--model MODEL], env_vars...
run_test() {
  local desc="$1"; shift
  local model_flag=()
  if [[ "${1:-}" == "--model" ]]; then
    model_flag=("--model" "$2")
    shift 2
  fi
  local env_args=("$@")

  local output exit_code
  output=$(perl -e "alarm $TIMEOUT_SECS; exec @ARGV" -- env \
    -u ALL_PROXY -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy \
    "${env_args[@]}" \
    claude -p "$PROMPT" ${model_flag[@]+"${model_flag[@]}"} 2>&1) && exit_code=$? || exit_code=$?

  local result
  if [[ $exit_code -eq 142 ]] || [[ $exit_code -eq 137 ]]; then
    result="⏱ TIMEOUT"
  elif [[ $exit_code -ne 0 ]]; then
    # Trim output to one line
    local first_line
    first_line=$(echo "$output" | head -1 | cut -c1-60)
    result="❌ exit=$exit_code: $first_line"
  elif echo "$output" | grep -qi "pass"; then
    result="✅ PASS"
  elif echo "$output" | grep -qi "not logged in"; then
    result="❌ Not logged in"
  else
    local first_line
    first_line=$(echo "$output" | head -1 | cut -c1-60)
    result="⚠️ exit=0: $first_line"
  fi

  printf "| %-25s | %s\n" "$desc" "$result"
}

# Run one S×E cell
run_cell() {
  local sid="$1" eid="$2"

  # Write settings
  write_settings_env "$(settings_env_for "$sid")"

  # Build env args array
  local env_string
  env_string="$(shell_env_for "$eid")"
  local -a env_args
  # shellcheck disable=SC2086
  read -ra env_args <<< $env_string

  # E7 uses --model flag instead of env var
  if [[ "$eid" == "E7" ]]; then
    run_test "$(describe_s "$sid") × $(describe_e "$eid")" --model claude-sonnet-4-20250514 "${env_args[@]}"
  else
    run_test "$(describe_s "$sid") × $(describe_e "$eid")" "${env_args[@]}"
  fi
}

# --- P0 Precedence Tests ---

run_p0() {
  local token
  token="$(get_token)"

  echo ""
  echo "## P0: ENV Precedence Tests"
  echo ""
  echo "NOTE: P0 tests do NOT set BASE_URL in settings.json to avoid the"
  echo "startup hang. BASE_URL is always provided via shell ENV override."
  echo ""
  echo "| Test                      | Result"
  echo "|---------------------------|-------"

  # P0a: settings API_KEY="" + shell API_KEY=<jwt> + shell BASE_URL
  # Tests: does shell API_KEY override settings API_KEY=""?
  write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0a: s.API_KEY=\"\" sh.API_KEY=jwt" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=$SDF_LLM"

  # P0b: settings API_KEY=<jwt> + shell not set (but shell BASE_URL)
  # Tests: can settings.json carry the JWT in API_KEY?
  write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"'"$token"'","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0b: s.API_KEY=jwt sh.(none)" "ANTHROPIC_BASE_URL=$SDF_LLM"

  # P0c: settings API_KEY="wrong" + shell API_KEY=<jwt>
  # Tests: definitive — if PASS, shell wins; if FAIL, settings wins
  write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"wrong-token-12345","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0c: s.API_KEY=wrong sh.API_KEY=jwt" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=$SDF_LLM"

  # P0d: settings AUTH_TOKEN=<jwt> + no API_KEY in settings or shell
  # Tests: can AUTH_TOKEN in settings carry the JWT?
  write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"'"$token"'","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0d: s.AUTH_TOKEN=jwt sh.(none)" "ANTHROPIC_BASE_URL=$SDF_LLM"

  # P0e: settings has nothing auth-related, shell has API_KEY + AUTH_TOKEN + BASE_URL
  # Tests: can shell ENV fully substitute for missing settings entries?
  write_settings_env '{"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0e: s.(minimal) sh.all" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_AUTH_TOKEN=$token" "ANTHROPIC_BASE_URL=$SDF_LLM"

  # P0f: same as P0a but with ANTHROPIC_MODEL set at runtime
  # Tests: does adding model rescue a config that might otherwise hang?
  write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
  run_test "P0f: P0a + model env" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=$SDF_LLM" "ANTHROPIC_MODEL=claude-sonnet-4-20250514"

  echo ""

  # Restore to S1
  write_settings_env "$(settings_env_for S1)"
  echo "(settings.json restored to S1)"
}

# --- N1 Matrix ---

run_n1() {
  echo ""
  echo "## N1: Direct to sdf-llm.slac.stanford.edu"
  echo ""
  echo "| Cell                      | Result"
  echo "|---------------------------|-------"

  local sid eid
  for sid in S1 S2 S3 S4 S5 S7 S8 S9 S10; do
    for eid in E1 E2 E3 E4 E5 E6 E7 E8; do
      run_cell "$sid" "$eid"
    done
  done

  echo ""

  # Restore to S1
  write_settings_env "$(settings_env_for S1)"
  echo "(settings.json restored to S1)"
}

# --- N2 Matrix ---

run_n2() {
  local token
  token="$(get_token)"

  echo ""
  echo "## N2: SOCKS to llm.sdf.slac.stanford.edu"
  echo ""
  echo "| Test                      | Result"
  echo "|---------------------------|-------"

  # S6 base config for all N2 tests
  write_settings_env "$(settings_env_for S6)"

  # N2a: Direct (expect DNS failure)
  run_test "N2a: direct (no proxy)" "ANTHROPIC_API_KEY=$token"

  # N2b: ALL_PROXY (expect SDK ignores it)
  run_test "N2b: ALL_PROXY=socks5h" \
    "ANTHROPIC_API_KEY=$token" \
    "ALL_PROXY=socks5h://127.0.0.1:10101" \
    "NODE_TLS_REJECT_UNAUTHORIZED=0"

  # N2c: HTTPS_PROXY (expect SDK ignores it)
  run_test "N2c: HTTPS_PROXY=socks5h" \
    "ANTHROPIC_API_KEY=$token" \
    "HTTPS_PROXY=socks5h://127.0.0.1:10101" \
    "NODE_TLS_REJECT_UNAUTHORIZED=0"

  echo ""
  echo "NOTE: proxychains4 and SSH port forward tests must be run manually."
  echo ""

  # Restore to S1
  write_settings_env "$(settings_env_for S1)"
  echo "(settings.json restored to S1)"
}

# --- Main ---

backup_settings() {
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  echo "(settings.json backed up to settings.json.bak)"
}

restore_settings() {
  if [[ -f "$SETTINGS_FILE.bak" ]]; then
    cp "$SETTINGS_FILE.bak" "$SETTINGS_FILE"
    echo "(settings.json restored from backup)"
  fi
}

main() {
  [[ -f "$TOKEN_FILE" ]] || die "No token file at $TOKEN_FILE — run device flow first"
  [[ -f "$SETTINGS_FILE" ]] || die "No settings.json at $SETTINGS_FILE"

  local cmd="${1:-help}"

  case "$cmd" in
    p0|P0)
      backup_settings
      trap restore_settings EXIT
      run_p0
      ;;
    n1|N1)
      backup_settings
      trap restore_settings EXIT
      run_n1
      ;;
    n2|N2)
      backup_settings
      trap restore_settings EXIT
      run_n2
      ;;
    all)
      backup_settings
      trap restore_settings EXIT
      run_p0
      run_n1
      run_n2
      ;;
    sniffer)
      echo ""
      echo "## Sniffer: observe Claude Code startup traffic"
      echo ""
      echo "Start the sniffer in another terminal first:"
      echo "  python3 $HOME/.claude/llm-sniffer.py -v --port 18080"
      echo ""
      echo "Then press Enter to run claude through it..."
      read -r
      local token
      token="$(get_token)"
      backup_settings
      trap restore_settings EXIT
      write_settings_env '{"ANTHROPIC_AUTH_TOKEN":"","ANTHROPIC_API_KEY":"","CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}'
      echo "| Test                      | Result"
      echo "|---------------------------|-------"
      run_test "sniffer: basic" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=http://127.0.0.1:18080"
      run_test "sniffer: + model env" "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=http://127.0.0.1:18080" "ANTHROPIC_MODEL=claude-sonnet-4-20250514"
      run_test "sniffer: + --model flag" --model claude-sonnet-4-20250514 "ANTHROPIC_API_KEY=$token" "ANTHROPIC_BASE_URL=http://127.0.0.1:18080"
      write_settings_env "$(settings_env_for S1)"
      echo "(settings.json restored to S1)"
      ;;
    S[1-9]|S10)
      local sid="$cmd"
      local eid="${2:-}"
      backup_settings
      trap restore_settings EXIT
      if [[ -n "$eid" ]]; then
        run_cell "$sid" "$eid"
      else
        echo ""
        echo "## $(describe_s "$sid") × all E"
        echo ""
        echo "| Cell                      | Result"
        echo "|---------------------------|-------"
        for eid in E1 E2 E3 E4 E5 E6 E7 E8; do
          run_cell "$sid" "$eid"
        done
      fi
      write_settings_env "$(settings_env_for S1)"
      echo "(settings.json restored to S1)"
      ;;
    help|--help|-h)
      echo "Usage: $0 <command>"
      echo ""
      echo "Commands:"
      echo "  p0          Run P0 precedence tests"
      echo "  n1          Run N1 matrix (direct to sdf-llm, 15 tests)"
      echo "  n2          Run N2 matrix (SOCKS to llm.sdf)"
      echo "  all         Run everything (p0 + n1 + n2)"
      echo "  S1 [E1]     Run specific S config (optionally with specific E)"
      echo "  S2 E3       Run single cell S2×E3"
      echo ""
      echo "Settings configs:"
      echo "  S1   full (BASE_URL=sdf-llm + AUTH_TOKEN=\"\" + API_KEY=\"\" + DISABLE_TRAFFIC)"
      echo "  S2   no AUTH_TOKEN"
      echo "  S3   no API_KEY"
      echo "  S4   no BASE_URL"
      echo "  S5   minimal (DISABLE_TRAFFIC only)"
      echo "  S6   full with llm.sdf internal hostname"
      echo "  S7   full + ANTHROPIC_MODEL=claude-sonnet-4-20250514"
      echo "  S8   full but no DISABLE_NONESSENTIAL_TRAFFIC"
      echo "  S9   empty env (\"env\": {})"
      echo "  S10  full with JWT baked into settings API_KEY"
      echo ""
      echo "ENV configs:"
      echo "  E1  API_KEY=<jwt>"
      echo "  E2  API_KEY=<jwt> + BASE_URL=sdf-llm"
      echo "  E3  API_KEY=<jwt> + BASE_URL=sdf-llm + AUTH_TOKEN=\"\""
      echo "  E4  AUTH_TOKEN=<jwt> + BASE_URL=sdf-llm (no API_KEY)"
      echo "  E5  API_KEY=<jwt> + AUTH_TOKEN=<jwt> + BASE_URL=sdf-llm"
      echo "  E6  API_KEY=<jwt> + BASE_URL=sdf-llm + ANTHROPIC_MODEL env"
      echo "  E7  API_KEY=<jwt> + BASE_URL=sdf-llm + --model flag"
      echo "  E8  API_KEY=<jwt> + BASE_URL=sdf-llm + debug logging"
      echo ""
      echo "Other commands:"
      echo "  sniffer     Run claude through llm-sniffer.py to observe traffic"
      echo ""
      echo "Token: $TOKEN_FILE"
      echo "Settings: $SETTINGS_FILE"
      ;;
    *)
      die "Unknown command: $cmd (try --help)"
      ;;
  esac
}

main "$@"