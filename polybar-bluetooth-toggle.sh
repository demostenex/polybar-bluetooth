#!/usr/bin/env bash
# Abre/fecha a janela GTK de gerenciamento Bluetooth.
# Uso:
#   polybar-bluetooth-toggle.sh              → abre/fecha janela principal
#   polybar-bluetooth-toggle.sh --toggle-bt  → liga/desliga Bluetooth
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

BT_SCRIPT="$SCRIPT_DIR/bluetooth_polybar.py"
JANELA="$SCRIPT_DIR/janela_bluetooth.py"
PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-bluetooth.pid"

# Liga/desliga Bluetooth direto (clique direito no ícone)
if [[ "${1:-}" == "--toggle-bt" ]]; then
  "$PYTHON_BIN" "$BT_SCRIPT" --mode toggle-power
  exit 0
fi

# Fecha janela se já estiver aberta
if [[ -f "$PID_FILE" ]]; then
  mapfile -t pids <"$PID_FILE" || true
  em_execucao=0
  for pid in "${pids[@]}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      em_execucao=1
    fi
  done
  rm -f "$PID_FILE"
  [[ "$em_execucao" -eq 1 ]] && exit 0
fi

# Abre a janela GTK
NO_AT_BRIDGE=1 "$PYTHON_BIN" "$JANELA" &
echo "$!" > "$PID_FILE"
