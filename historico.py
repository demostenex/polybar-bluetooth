"""Histórico persistente de dispositivos Bluetooth.

Responsabilidade única: salvar e carregar o registro de dispositivos
já utilizados, ordenados por uso mais recente.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any

HISTORICO_PADRAO = pathlib.Path.home() / ".config" / "polybar" / "scripts" / "bluetooth_history.json"


class RegistroDispositivo:
    """Entrada no histórico."""

    FORMATO_DATA = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, mac: str, nome: str, ultimo_uso: datetime.datetime) -> None:
        self.mac = mac.upper()
        self.nome = nome
        self.ultimo_uso = ultimo_uso

    def para_dict(self) -> dict[str, Any]:
        return {
            "mac": self.mac,
            "nome": self.nome,
            "ultimo_uso": self.ultimo_uso.strftime(self.FORMATO_DATA),
        }

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "RegistroDispositivo":
        ultimo_uso = datetime.datetime.strptime(dados["ultimo_uso"], cls.FORMATO_DATA)
        return cls(mac=dados["mac"], nome=dados["nome"], ultimo_uso=ultimo_uso)

    def __repr__(self) -> str:  # pragma: no cover
        return f"RegistroDispositivo({self.mac!r}, {self.nome!r})"


class Historico:
    """Gerencia o arquivo JSON de histórico."""

    def __init__(self, caminho: pathlib.Path = HISTORICO_PADRAO) -> None:
        self._caminho = caminho

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def carregar(self) -> list[RegistroDispositivo]:
        if not self._caminho.exists():
            return []
        try:
            dados = json.loads(self._caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        registros = []
        for item in dados:
            try:
                registros.append(RegistroDispositivo.de_dict(item))
            except (KeyError, ValueError):
                continue
        return sorted(registros, key=lambda r: r.ultimo_uso, reverse=True)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def registrar(self, mac: str, nome: str) -> None:
        """Adiciona ou atualiza um dispositivo e persiste."""
        registros = self.carregar()
        mac = mac.upper()
        # remove entrada antiga com mesmo mac
        registros = [r for r in registros if r.mac != mac]
        registros.insert(0, RegistroDispositivo(mac, nome, datetime.datetime.now()))
        self._salvar(registros)

    def remover(self, mac: str) -> None:
        """Remove um dispositivo do histórico."""
        registros = [r for r in self.carregar() if r.mac != mac.upper()]
        self._salvar(registros)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _salvar(self, registros: list[RegistroDispositivo]) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self._caminho.write_text(
            json.dumps([r.para_dict() for r in registros], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
