"""Adaptador Bluetooth via D-Bus (BlueZ).

Responsabilidade única: comunicação com o stack BlueZ.
Toda interação com org.bluez passa por aqui — nenhum outro módulo
fala com D-Bus diretamente.
"""

from __future__ import annotations

import abc
from typing import Protocol


class DispositivoBluetooth:
    """Representa um dispositivo Bluetooth."""

    def __init__(self, mac: str, nome: str, conectado: bool, emparelhado: bool) -> None:
        self.mac = mac
        self.nome = nome
        self.conectado = conectado
        self.emparelhado = emparelhado

    def __repr__(self) -> str:  # pragma: no cover
        return f"DispositivoBluetooth({self.mac!r}, {self.nome!r}, conectado={self.conectado})"


class AdaptadorBluetoothProtocol(Protocol):
    """Abstração do adaptador Bluetooth (permite mock nos testes)."""

    def esta_disponivel(self) -> bool: ...
    def esta_ligado(self) -> bool: ...
    def ligar(self) -> None: ...
    def desligar(self) -> None: ...
    def listar_dispositivos(self) -> list[DispositivoBluetooth]: ...
    def parear(self, mac: str) -> None: ...
    def conectar(self, mac: str) -> None: ...
    def desconectar(self, mac: str) -> None: ...
    def esquecer(self, mac: str) -> None: ...
    def buscar(self, segundos: int = 10) -> None: ...


class AdaptadorBluetoothDBus:
    """Implementação real usando BlueZ via D-Bus."""

    _BLUEZ_SERVICE = "org.bluez"
    _ADAPTER_IFACE = "org.bluez.Adapter1"
    _DEVICE_IFACE = "org.bluez.Device1"
    _OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
    _PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

    def __init__(self) -> None:
        import dbus  # importação tardia — facilita mock nos testes

        self._dbus = dbus
        self._bus = dbus.SystemBus()
        self._adapter_path = self._encontrar_adaptador()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _encontrar_adaptador(self) -> str | None:
        gerenciador = self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, "/"),
            self._OBJECT_MANAGER,
        )
        for caminho, interfaces in gerenciador.GetManagedObjects().items():
            if self._ADAPTER_IFACE in interfaces:
                return str(caminho)
        return None

    def _propriedades_adapter(self):
        if not self._adapter_path:
            raise RuntimeError("Nenhum adaptador Bluetooth encontrado.")
        return self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, self._adapter_path),
            self._PROPERTIES_IFACE,
        )

    def _objeto_adapter(self):
        if not self._adapter_path:
            raise RuntimeError("Nenhum adaptador Bluetooth encontrado.")
        return self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, self._adapter_path),
            self._ADAPTER_IFACE,
        )

    def _objeto_dispositivo(self, caminho: str):
        return self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, caminho),
            self._DEVICE_IFACE,
        )

    def _propriedades_dispositivo(self, caminho: str):
        return self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, caminho),
            self._PROPERTIES_IFACE,
        )

    def _caminho_por_mac(self, mac: str) -> str | None:
        gerenciador = self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, "/"),
            self._OBJECT_MANAGER,
        )
        for caminho, interfaces in gerenciador.GetManagedObjects().items():
            if self._DEVICE_IFACE in interfaces:
                props = interfaces[self._DEVICE_IFACE]
                if str(props.get("Address", "")).upper() == mac.upper():
                    return str(caminho)
        return None

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def esta_disponivel(self) -> bool:
        return self._adapter_path is not None

    def esta_ligado(self) -> bool:
        if not self.esta_disponivel():
            return False
        try:
            props = self._propriedades_adapter()
            return bool(props.Get(self._ADAPTER_IFACE, "Powered"))
        except Exception:
            return False

    def ligar(self) -> None:
        props = self._propriedades_adapter()
        props.Set(self._ADAPTER_IFACE, "Powered", self._dbus.Boolean(True))

    def desligar(self) -> None:
        props = self._propriedades_adapter()
        props.Set(self._ADAPTER_IFACE, "Powered", self._dbus.Boolean(False))

    def listar_dispositivos(self) -> list[DispositivoBluetooth]:
        gerenciador = self._dbus.Interface(
            self._bus.get_object(self._BLUEZ_SERVICE, "/"),
            self._OBJECT_MANAGER,
        )
        dispositivos: list[DispositivoBluetooth] = []
        for caminho, interfaces in gerenciador.GetManagedObjects().items():
            if self._DEVICE_IFACE not in interfaces:
                continue
            # só retorna devices do adaptador atual
            if self._adapter_path and not str(caminho).startswith(self._adapter_path):
                continue
            props = interfaces[self._DEVICE_IFACE]
            mac = str(props.get("Address", ""))
            nome = str(props.get("Name", props.get("Alias", mac)))
            conectado = bool(props.get("Connected", False))
            emparelhado = bool(props.get("Paired", False))
            dispositivos.append(DispositivoBluetooth(mac, nome, conectado, emparelhado))
        return dispositivos

    def parear(self, mac: str) -> None:
        """Pareia com dispositivo via bluetoothctl com agente NoInputNoOutput.

        O agente NoInputNoOutput faz o BlueZ aceitar automaticamente a
        confirmação numérica do lado do PC — o usuário só precisa confirmar
        no próprio dispositivo (ex: celular Android).
        """
        import subprocess

        # Envia todos os comandos de uma vez via stdin; bluetoothctl
        # executa em sequência e fecha quando o stdin fechar.
        # Aguardamos 30s para a confirmação do usuário no aparelho.
        comandos = (
            "agent NoInputNoOutput\n"
            "default-agent\n"
            f"pair {mac}\n"
        )
        resultado = subprocess.run(
            ["bluetoothctl"],
            input=comandos,
            capture_output=True,
            text=True,
            timeout=35,
        )

        # Após parear: trust (reconexão automática) + connect
        subprocess.run(["bluetoothctl", "trust", mac], capture_output=True, text=True, timeout=10)
        subprocess.run(["bluetoothctl", "connect", mac], capture_output=True, text=True, timeout=15)

        if resultado.returncode != 0 and "Failed" in resultado.stdout:
            raise RuntimeError(f"Pareamento falhou: {resultado.stdout.strip()}")

    def conectar(self, mac: str) -> None:
        caminho = self._caminho_por_mac(mac)
        if not caminho:
            raise ValueError(f"Dispositivo não encontrado: {mac}")
        self._objeto_dispositivo(caminho).Connect()

    def desconectar(self, mac: str) -> None:
        caminho = self._caminho_por_mac(mac)
        if not caminho:
            raise ValueError(f"Dispositivo não encontrado: {mac}")
        self._objeto_dispositivo(caminho).Disconnect()

    def esquecer(self, mac: str) -> None:
        """Remove dispositivo do BlueZ (despareia e esquece)."""
        import subprocess
        subprocess.run(["bluetoothctl", "remove", mac], capture_output=True, text=True, timeout=10)

    def buscar(self, segundos: int = 10) -> None:
        import time

        props = self._propriedades_adapter()

        # Garante que o adaptador está pareável — sem isso muitos dispositivos
        # Android ficam invisíveis durante o scan.
        pairable_antes = bool(props.Get(self._ADAPTER_IFACE, "Pairable"))
        if not pairable_antes:
            props.Set(self._ADAPTER_IFACE, "Pairable", self._dbus.Boolean(True))

        adapter = self._objeto_adapter()
        try:
            adapter.StartDiscovery()
            time.sleep(segundos)
            adapter.StopDiscovery()
        finally:
            # Restaura estado original de Pairable
            if not pairable_antes:
                props.Set(self._ADAPTER_IFACE, "Pairable", self._dbus.Boolean(False))
