#!/usr/bin/env bash
# install.sh — install github-agent-skills locally (no root required)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
INSTALL_CLI=1
INSTALL_SKILLS=1
AGENTS=()
DRY_RUN=0
MODE="link" # link | copy

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install the github-agent CLI and portable skills for compatible coding agents.

Options:
  --agents <list>   Comma-separated: cursor,claude,codex,gemini,all,auto
  --copy            Copy skills instead of symlinking
  --link            Symlink skills (default)
  --cli-only        Install Python CLI only
  --skills-only     Install skills only
  --dry-run         Show actions without changing anything
  -h, --help        Show help

Examples:
  ./install.sh
  ./install.sh --agents cursor,claude
  ./install.sh --agents all --copy
EOF
}

log() { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

detect_agents() {
  local found=()
  if [[ -d "${HOME}/.cursor" ]] || command -v cursor >/dev/null 2>&1 || command -v agent >/dev/null 2>&1; then
    found+=("cursor")
  fi
  if [[ -d "${HOME}/.claude" ]] || command -v claude >/dev/null 2>&1; then
    found+=("claude")
  fi
  if [[ -d "${HOME}/.codex" ]] || [[ -d "${HOME}/.agents" ]] || command -v codex >/dev/null 2>&1; then
    found+=("codex")
  fi
  if [[ -d "${HOME}/.gemini" ]] || command -v gemini >/dev/null 2>&1; then
    found+=("gemini")
  fi
  if [[ ${#found[@]} -eq 0 ]]; then
    found=("cursor" "claude")
  fi
  printf '%s\n' "${found[@]}"
}

agent_skill_dir() {
  case "$1" in
    cursor) printf '%s\n' "${HOME}/.cursor/skills" ;;
    claude) printf '%s\n' "${HOME}/.claude/skills" ;;
    codex) printf '%s\n' "${HOME}/.agents/skills" ;;
    gemini) printf '%s\n' "${HOME}/.gemini/skills" ;;
    *) return 1 ;;
  esac
}

install_skill() {
  local agent="$1"
  local skill_name="$2"
  local src="${ROOT}/skills/${skill_name}"
  local dest_root
  dest_root="$(agent_skill_dir "${agent}")"
  local dest="${dest_root}/${skill_name}"

  [[ -d "${src}" ]] || die "Missing skill source: ${src}"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] ${MODE} ${src} -> ${dest}"
    return 0
  fi

  mkdir -p "${dest_root}"
  if [[ -e "${dest}" || -L "${dest}" ]]; then
    rm -rf "${dest}"
  fi
  if [[ "${MODE}" == "copy" ]]; then
    mkdir -p "${dest}"
    cp -R "${src}/." "${dest}/"
  else
    ln -s "${src}" "${dest}"
  fi
  log "Installed ${skill_name} for ${agent} -> ${dest}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agents)
      IFS=',' read -r -a AGENTS <<< "${2:-}"
      shift 2
      ;;
    --copy) MODE="copy"; shift ;;
    --link) MODE="link"; shift ;;
    --cli-only) INSTALL_SKILLS=0; shift ;;
    --skills-only) INSTALL_CLI=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

command -v git >/dev/null 2>&1 || warn "git not found — install git for full workflows"
command -v gh >/dev/null 2>&1 || warn "gh not found — install GitHub CLI and run: gh auth login"
command -v "${PYTHON}" >/dev/null 2>&1 || die "python3 not found"

if [[ ${#AGENTS[@]} -eq 0 ]]; then
  AGENTS=("auto")
fi

if [[ "${AGENTS[0]}" == "auto" ]]; then
  AGENTS=()
  while IFS= read -r line; do
    [[ -n "${line}" ]] && AGENTS+=("${line}")
  done < <(detect_agents)
elif [[ "${AGENTS[0]}" == "all" ]]; then
  AGENTS=("cursor" "claude" "codex" "gemini")
fi

log "github-agent-skills installer"
log "Root: ${ROOT}"
log "Agents: ${AGENTS[*]}"
log "Skill mode: ${MODE}"

if [[ "${INSTALL_CLI}" -eq 1 ]]; then
  VENV="${ROOT}/.venv"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] create ${VENV} and pip install -e ${ROOT}"
  else
    log "Creating local virtualenv at ${VENV}…"
    if [[ ! -x "${VENV}/bin/python" ]]; then
      "${PYTHON}" -m venv "${VENV}"
    fi
    # shellcheck disable=SC1091
    "${VENV}/bin/pip" install -U pip >/dev/null
    "${VENV}/bin/pip" install -e "${ROOT}"
    log "CLI installed: ${VENV}/bin/github-agent"
    "${VENV}/bin/github-agent" --version || true

    BIN_DIR="${HOME}/.local/bin"
    mkdir -p "${BIN_DIR}"
    ln -sfn "${VENV}/bin/github-agent" "${BIN_DIR}/github-agent"
    log "Linked ${BIN_DIR}/github-agent -> ${VENV}/bin/github-agent"
    if ! command -v github-agent >/dev/null 2>&1; then
      warn "Add ~/.local/bin to your PATH if needed:"
      warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    else
      log "CLI OK on PATH: $(command -v github-agent)"
    fi
  fi
fi

if [[ "${INSTALL_SKILLS}" -eq 1 ]]; then
  SKILLS=(github-checkup github-cleanup github-polish github-fix github-today github-recap)
  for agent in "${AGENTS[@]}"; do
    for skill in "${SKILLS[@]}"; do
      install_skill "${agent}" "${skill}"
    done
  done
fi

cat <<'EOF'

Next steps:
  1. gh auth login          # if needed
  2. github-agent auth-check
  3. github-agent checkup
EOF
