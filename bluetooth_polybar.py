#!/usr/bin/env python3
"""Script principal do módulo Bluetooth para o Polybar.

Modos disponíveis (--mode):
  module        → linha única para o Polybar (ícone + cor por estado)
  list          → linhas tab-separadas para consumo do yad
  toggle-power  → liga/desliga o adaptador Bluetooth
  conectar      → conecta um dispositivo (--mac obrigatório)
  desconectar   → desconecta um dispositivo (--mac obrigatório)
  buscar        → inicia busca por novos dispositivos
"""

from __future__ import annotations

import argparse
import datetime
import sys

from adaptador_bluetooth import AdaptadorBluetoothDBus, AdaptadorBluetoothProtocol
from historico import Historico, RegistroDispositivo

# ------------------------------------------------------------------
# Ícones Nerd Font (Bluetooth)
# ------------------------------------------------------------------
ICONE_DESLIGADO = "󰂲"
ICONE_LIGADO = "󰂯"
ICONE_CONECTADO = "󰂱"

COR_DESLIGADO = "%{F#666666}"
COR_LIGADO = "%{F#5294e2}"
COR_CONECTADO = "%{F#6abf69}"
COR_RESET = "%{F-}"


# ------------------------------------------------------------------
# Formatadores de saída
# ------------------------------------------------------------------


def saida_modulo(adaptador: AdaptadorBluetoothProtocol) -> str:
    """Retorna a string de uma linha que o Polybar exibe."""
    if not adaptador.esta_disponivel():
        return f"{COR_DESLIGADO}{ICONE_DESLIGADO}{COR_RESET}"

    if not adaptador.esta_ligado():
        return f"{COR_DESLIGADO}{ICONE_DESLIGADO}{COR_RESET}"

    conectados = [d for d in adaptador.listar_dispositivos() if d.conectado]
    if not conectados:
        return f"{COR_LIGADO}{ICONE_LIGADO}{COR_RESET}"

    sufixo = f" {len(conectados)}" if len(conectados) > 1 else ""
    return f"{COR_CONECTADO}{ICONE_CONECTADO}{sufixo}{COR_RESET}"


def saida_list(adaptador: AdaptadorBluetoothProtocol, historico: Historico) -> str:
    """Retorna linhas tab-separadas para o yad.

    Formato por linha: mac \\t nome \\t status \\t tooltip
    Dispositivos conectados são automaticamente salvos no histórico.
    """
    dispositivos = {d.mac.upper(): d for d in adaptador.listar_dispositivos()}
    registros = historico.carregar()

    # salva dispositivos conectados no histórico automaticamente
    macs_historico = {r.mac for r in registros}
    for dispositivo in dispositivos.values():
        if dispositivo.conectado and dispositivo.mac not in macs_historico:
            historico.registrar(dispositivo.mac, dispositivo.nome)
            registros.insert(
                0,
                RegistroDispositivo(dispositivo.mac, dispositivo.nome, datetime.datetime.now()),
            )
            macs_historico.add(dispositivo.mac)

    linhas: list[str] = []
    for registro in registros:
        device = dispositivos.get(registro.mac)
        if device and device.conectado:
            status = "conectado"
        elif device and device.emparelhado:
            status = "emparelhado"
        else:
            status = "histórico"
        tooltip = f"{registro.mac} — último uso: {registro.ultimo_uso:%d/%m/%Y %H:%M}"
        linhas.append(f"{registro.mac}\t{registro.nome}\t{status}\t{tooltip}")

    return "\n".join(linhas)


# ------------------------------------------------------------------
# Ações
# ------------------------------------------------------------------


def _conectar(mac: str, adaptador: AdaptadorBluetoothProtocol, historico: Historico) -> int:
    """Conecta sem desconectar dispositivos já ativos."""
    dispositivos = {d.mac.upper(): d for d in adaptador.listar_dispositivos()}
    device = dispositivos.get(mac.upper())
    nome = device.nome if device else mac
    adaptador.conectar(mac)
    historico.registrar(mac, nome)
    return 0


def _desconectar(mac: str, adaptador: AdaptadorBluetoothProtocol) -> int:
    adaptador.desconectar(mac)
    return 0


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Módulo Bluetooth para Polybar")
    parser.add_argument(
        "--mode",
        choices=["module", "list", "toggle-power", "conectar", "desconectar", "buscar"],
        default="module",
    )
    parser.add_argument("--mac", default="", help="MAC do dispositivo alvo")
    parser.add_argument(
        "--historico-arquivo",
        default="",
        help="Caminho alternativo para o arquivo de histórico",
    )
    args = parser.parse_args()

    historico = Historico(
        __import__("pathlib").Path(args.historico_arquivo).expanduser().resolve()
        if args.historico_arquivo
        else __import__("historico").HISTORICO_PADRAO
    )

    try:
        adaptador: AdaptadorBluetoothProtocol = AdaptadorBluetoothDBus()
    except Exception:
        if args.mode == "module":
            print(f"{COR_DESLIGADO}{ICONE_DESLIGADO}{COR_RESET}")
            return 0
        print("Erro: D-Bus/BlueZ não disponível.", file=sys.stderr)
        return 1

    try:
        if args.mode == "module":
            print(saida_modulo(adaptador))
            return 0

        if args.mode == "list":
            saida = saida_list(adaptador, historico)
            if saida:
                print(saida)
            return 0

        if args.mode == "toggle-power":
            if adaptador.esta_ligado():
                adaptador.desligar()
            else:
                adaptador.ligar()
            return 0

        if args.mode == "conectar":
            if not args.mac:
                print("--mac é obrigatório para o modo conectar.", file=sys.stderr)
                return 1
            return _conectar(args.mac, adaptador, historico)

        if args.mode == "desconectar":
            if not args.mac:
                print("--mac é obrigatório para o modo desconectar.", file=sys.stderr)
                return 1
            return _desconectar(args.mac, adaptador)

        if args.mode == "buscar":
            adaptador.buscar()
            return 0

    except Exception as erro:
        if args.mode == "module":
            print(f"{COR_DESLIGADO}{ICONE_DESLIGADO}{COR_RESET}")
            return 0
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
