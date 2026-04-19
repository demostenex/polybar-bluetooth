"""Testes unitários — bluetooth_polybar.py (saida_modulo e saida_list)"""

from __future__ import annotations

import datetime
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stub dbus
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def stub_dbus(monkeypatch):
    stub = types.ModuleType("dbus")
    stub.SystemBus = MagicMock()
    stub.Interface = MagicMock()
    stub.Boolean = bool
    monkeypatch.setitem(sys.modules, "dbus", stub)
    yield stub


# ---------------------------------------------------------------------------
# Adaptador fake (implementa o protocolo sem D-Bus)
# ---------------------------------------------------------------------------

class AdaptadorFake:
    def __init__(self, disponivel=True, ligado=True, dispositivos=None):
        self._disponivel = disponivel
        self._ligado = ligado
        self._dispositivos = dispositivos or []

    def esta_disponivel(self): return self._disponivel
    def esta_ligado(self): return self._ligado
    def listar_dispositivos(self): return self._dispositivos
    def conectar(self, mac): pass
    def desconectar(self, mac): pass
    def ligar(self): self._ligado = True
    def desligar(self): self._ligado = False
    def buscar(self, segundos=10): pass


# ---------------------------------------------------------------------------
# saida_modulo
# ---------------------------------------------------------------------------

def test_modulo_bt_indisponivel():
    from bluetooth_polybar import saida_modulo, ICONE_DESLIGADO
    adaptador = AdaptadorFake(disponivel=False)
    saida = saida_modulo(adaptador)
    assert ICONE_DESLIGADO in saida


def test_modulo_bt_desligado():
    from bluetooth_polybar import saida_modulo, ICONE_DESLIGADO
    adaptador = AdaptadorFake(ligado=False)
    saida = saida_modulo(adaptador)
    assert ICONE_DESLIGADO in saida


def test_modulo_bt_ligado_sem_conexao():
    from bluetooth_polybar import saida_modulo, ICONE_LIGADO
    adaptador = AdaptadorFake(ligado=True, dispositivos=[])
    saida = saida_modulo(adaptador)
    assert ICONE_LIGADO in saida


def test_modulo_bt_um_conectado():
    from adaptador_bluetooth import DispositivoBluetooth
    from bluetooth_polybar import saida_modulo, ICONE_CONECTADO
    dispositivos = [DispositivoBluetooth("AA:BB:CC:DD:EE:FF", "Fone", conectado=True, emparelhado=True)]
    adaptador = AdaptadorFake(dispositivos=dispositivos)
    saida = saida_modulo(adaptador)
    assert ICONE_CONECTADO in saida


def test_modulo_bt_multiplos_conectados():
    from adaptador_bluetooth import DispositivoBluetooth
    from bluetooth_polybar import saida_modulo, ICONE_CONECTADO
    dispositivos = [
        DispositivoBluetooth("AA:BB:CC:DD:EE:FF", "Fone", conectado=True, emparelhado=True),
        DispositivoBluetooth("11:22:33:44:55:66", "Caixa", conectado=True, emparelhado=True),
    ]
    adaptador = AdaptadorFake(dispositivos=dispositivos)
    saida = saida_modulo(adaptador)
    assert ICONE_CONECTADO in saida
    assert "2" in saida


# ---------------------------------------------------------------------------
# saida_list
# ---------------------------------------------------------------------------

def test_list_vazio(tmp_path):
    from bluetooth_polybar import saida_list
    from historico import Historico
    adaptador = AdaptadorFake(dispositivos=[])
    h = Historico(tmp_path / "hist.json")
    saida = saida_list(adaptador, h)
    assert saida == ""


def test_list_historico_aparece(tmp_path):
    from bluetooth_polybar import saida_list
    from historico import Historico
    h = Historico(tmp_path / "hist.json")
    h.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    adaptador = AdaptadorFake(dispositivos=[])
    saida = saida_list(adaptador, h)
    assert "Fone Sony" in saida
    assert "AA:BB:CC:DD:EE:FF" in saida


def test_list_status_conectado(tmp_path):
    from adaptador_bluetooth import DispositivoBluetooth
    from bluetooth_polybar import saida_list
    from historico import Historico
    h = Historico(tmp_path / "hist.json")
    h.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    dispositivos = [DispositivoBluetooth("AA:BB:CC:DD:EE:FF", "Fone Sony", conectado=True, emparelhado=True)]
    adaptador = AdaptadorFake(dispositivos=dispositivos)
    saida = saida_list(adaptador, h)
    assert "conectado" in saida


def test_list_status_historico(tmp_path):
    from bluetooth_polybar import saida_list
    from historico import Historico
    h = Historico(tmp_path / "hist.json")
    h.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    adaptador = AdaptadorFake(dispositivos=[])
    saida = saida_list(adaptador, h)
    assert "histórico" in saida
