#!/usr/bin/env bash
# Abre a janela de gerenciamento Bluetooth (yad com seleção de linha).
# Uso:
#   polybar-bluetooth-toggle.sh              → abre/fecha janela principal
#   polybar-bluetooth-toggle.sh --toggle-bt  → liga/desliga Bluetooth
set -euo pipefail

PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-bluetooth.pid"
LIST_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-bluetooth-list.txt"
PYTHON_BIN="$HOME/.config/polybar/scripts/.venv/bin/python"
SCRIPT="$HOME/.config/polybar/scripts/bluetooth_polybar.py"

# ------------------------------------------------------------------
# Liga/desliga Bluetooth direto (clique direito no ícone)
# ------------------------------------------------------------------
if [[ "${1:-}" == "--toggle-bt" ]]; then
  "$PYTHON_BIN" "$SCRIPT" --mode toggle-power
  exit 0
fi

# ------------------------------------------------------------------
# Fecha janela se já estiver aberta
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Gera lista de dispositivos para o yad
# ------------------------------------------------------------------
_abrir_janela() {
  "$PYTHON_BIN" "$SCRIPT" --mode list >"$LIST_FILE" 2>/dev/null || true

  rows=()
  if [[ -s "$LIST_FILE" ]]; then
    while IFS=$'\t' read -r mac nome status tooltip; do
      [[ -z "${mac:-}" ]] && continue
      rows+=("$mac" "$nome" "$status" "$tooltip")
    done <"$LIST_FILE"
  fi

  if [[ "${#rows[@]}" -eq 0 ]]; then
    rows=("—" "Nenhum dispositivo no histórico." "histórico" "Busque novos dispositivos primeiro.")
  fi

  # --print-column=1 → imprime o MAC da linha selecionada ao clicar um botão
  selected=$(
    yad --list \
      --column="MAC" \
      --column="Dispositivo" \
      --column="Status" \
      --column="Info:TIP" \
      --hide-column=1 \
      --tooltip-column=4 \
      --print-column=1 \
      --title="Gerenciador Bluetooth" \
      --text="Selecione um dispositivo e clique em uma ação:" \
      --width=520 --height=380 \
      --fixed \
      --mouse \
      --skip-taskbar \
      --on-top \
      --sticky \
      --button="Conectar:0" \
      --button="Desconectar:2" \
      --button="Buscar (10s):4" \
      --button="BT On/Off:6" \
      --button="Fechar:8" \
      "${rows[@]}" 2>/dev/null
  ) || exit_code=$?
  exit_code="${exit_code:-0}"

  # yad coloca pipe ao redor do valor: |55:FB:BA:A6:E7:D2|
  mac=$(echo "${selected:-}" | tr -d '|\n ')

  case "$exit_code" in
    0)  # Conectar
      if [[ -n "$mac" && "$mac" != "—" ]]; then
        "$PYTHON_BIN" "$SCRIPT" --mode conectar --mac "$mac" && \
          notify-send "Bluetooth" "Conectando a $(echo "${rows[@]}" | grep -o "$mac[^	]*" | head -1 | cut -f2)…" 2>/dev/null || true
      else
        notify-send "Bluetooth" "Selecione um dispositivo na lista primeiro." 2>/dev/null || true
      fi
      ;;
    2)  # Desconectar
      if [[ -n "$mac" && "$mac" != "—" ]]; then
        "$PYTHON_BIN" "$SCRIPT" --mode desconectar --mac "$mac" && \
          notify-send "Bluetooth" "Dispositivo desconectado." 2>/dev/null || true
      else
        notify-send "Bluetooth" "Selecione um dispositivo na lista primeiro." 2>/dev/null || true
      fi
      ;;
    4)  # Buscar novos dispositivos
      notify-send "Bluetooth" "Buscando dispositivos por 10 segundos…" 2>/dev/null || true
      "$PYTHON_BIN" "$SCRIPT" --mode buscar &
      buscar_pid=$!
      wait "$buscar_pid" 2>/dev/null || true
      notify-send "Bluetooth" "Busca concluída. Reabra a janela para ver novos dispositivos." 2>/dev/null || true
      ;;
    6)  # Liga/Desliga BT
      "$PYTHON_BIN" "$SCRIPT" --mode toggle-power
      ;;
  esac
}

_abrir_janela &
JANELA_PID=$!
echo "$JANELA_PID" >"$PID_FILE"
