#!/usr/bin/env bash
# Abre/fecha a janela GTK de gerenciamento Bluetooth.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Janelas GTK precisam do python3 do sistema (tem gi/PyGObject)
PYTHON_GTK="$(command -v python3)"
# Scripts do projeto usam o venv (tem dbus, bluetooth etc.)
PYTHON_VENV="$SCRIPT_DIR/.venv/bin/python"
[ -x "$PYTHON_VENV" ] || PYTHON_VENV="$PYTHON_GTK"

BT_SCRIPT="$SCRIPT_DIR/bluetooth_polybar.py"
JANELA="$SCRIPT_DIR/janela_bluetooth.py"
PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-bluetooth.pid"

# Liga/desliga Bluetooth direto (clique direito no ícone)
if [[ "${1:-}" == "--toggle-bt" ]]; then
  "$PYTHON_VENV" "$BT_SCRIPT" --mode toggle-power
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
NO_AT_BRIDGE=1 "$PYTHON_GTK" "$JANELA" &
echo "$!" > "$PID_FILE"
