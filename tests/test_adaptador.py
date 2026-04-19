"""Testes unitários — adaptador_bluetooth.py"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub do módulo dbus para rodar sem hardware
# ---------------------------------------------------------------------------

def _criar_stub_dbus():
    dbus_mock = types.ModuleType("dbus")
    dbus_mock.SystemBus = MagicMock()  # instância chamável, não a classe
    dbus_mock.Interface = MagicMock()
    dbus_mock.Boolean = bool
    return dbus_mock


@pytest.fixture(autouse=True)
def stub_dbus(monkeypatch):
    stub = _criar_stub_dbus()
    monkeypatch.setitem(sys.modules, "dbus", stub)
    yield stub


# ---------------------------------------------------------------------------
# Testes de DispositivoBluetooth
# ---------------------------------------------------------------------------

def test_dispositivo_atributos():
    from adaptador_bluetooth import DispositivoBluetooth

    d = DispositivoBluetooth("AA:BB:CC:DD:EE:FF", "Fone", conectado=True, emparelhado=True)
    assert d.mac == "AA:BB:CC:DD:EE:FF"
    assert d.nome == "Fone"
    assert d.conectado is True
    assert d.emparelhado is True


def test_dispositivo_desconectado():
    from adaptador_bluetooth import DispositivoBluetooth

    d = DispositivoBluetooth("11:22:33:44:55:66", "Caixa", conectado=False, emparelhado=True)
    assert d.conectado is False


# ---------------------------------------------------------------------------
# Testes do AdaptadorBluetoothDBus (com D-Bus mockado)
# ---------------------------------------------------------------------------

def _criar_adaptador_mockado(stub_dbus, adaptador_path="/org/bluez/hci0", powered=True, devices=None):
    """Monta um AdaptadorBluetoothDBus com objetos D-Bus completamente mockados."""
    from adaptador_bluetooth import AdaptadorBluetoothDBus

    devices = devices or []

    # Simula GetManagedObjects
    objetos = {adaptador_path: {"org.bluez.Adapter1": {"Powered": powered}}}
    for d in devices:
        dev_path = f"{adaptador_path}/dev_{d['mac'].replace(':', '_')}"
        objetos[dev_path] = {
            "org.bluez.Device1": {
                "Address": d["mac"],
                "Name": d["nome"],
                "Connected": d.get("conectado", False),
                "Paired": d.get("emparelhado", True),
            }
        }

    gerenciador_mock = MagicMock()
    gerenciador_mock.GetManagedObjects.return_value = objetos

    propriedades_mock = MagicMock()
    propriedades_mock.Get.return_value = powered

    def interface_side_effect(obj, iface):
        if iface == "org.freedesktop.DBus.ObjectManager":
            return gerenciador_mock
        if iface == "org.freedesktop.DBus.Properties":
            return propriedades_mock
        return MagicMock()

    stub_dbus.Interface.side_effect = interface_side_effect

    bus_mock = MagicMock()
    stub_dbus.SystemBus.return_value = bus_mock

    adaptador = AdaptadorBluetoothDBus()
    return adaptador, propriedades_mock


def test_esta_disponivel_com_adaptador(stub_dbus):
    adaptador, _ = _criar_adaptador_mockado(stub_dbus)
    assert adaptador.esta_disponivel() is True


def test_esta_disponivel_sem_adaptador(stub_dbus):
    from adaptador_bluetooth import AdaptadorBluetoothDBus

    gerenciador_mock = MagicMock()
    gerenciador_mock.GetManagedObjects.return_value = {}
    stub_dbus.Interface.return_value = gerenciador_mock
    stub_dbus.SystemBus.return_value = MagicMock()

    adaptador = AdaptadorBluetoothDBus()
    assert adaptador.esta_disponivel() is False


def test_esta_ligado_true(stub_dbus):
    adaptador, props = _criar_adaptador_mockado(stub_dbus, powered=True)
    props.Get.return_value = True
    assert adaptador.esta_ligado() is True


def test_esta_ligado_false(stub_dbus):
    adaptador, props = _criar_adaptador_mockado(stub_dbus, powered=False)
    props.Get.return_value = False
    assert adaptador.esta_ligado() is False


def test_listar_dispositivos(stub_dbus):
    dispositivos_dados = [
        {"mac": "AA:BB:CC:DD:EE:FF", "nome": "Fone Sony", "conectado": True, "emparelhado": True},
        {"mac": "11:22:33:44:55:66", "nome": "Caixa JBL", "conectado": False, "emparelhado": True},
    ]
    adaptador, _ = _criar_adaptador_mockado(stub_dbus, devices=dispositivos_dados)
    resultado = adaptador.listar_dispositivos()

    macs = {d.mac for d in resultado}
    assert "AA:BB:CC:DD:EE:FF" in macs
    assert "11:22:33:44:55:66" in macs

    fone = next(d for d in resultado if d.mac == "AA:BB:CC:DD:EE:FF")
    assert fone.conectado is True
    assert fone.nome == "Fone Sony"


def test_listar_dispositivos_vazio(stub_dbus):
    adaptador, _ = _criar_adaptador_mockado(stub_dbus, devices=[])
    assert adaptador.listar_dispositivos() == []
