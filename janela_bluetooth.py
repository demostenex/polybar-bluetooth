#!/usr/bin/env python3
"""
janela_bluetooth.py
Janela flutuante de gerenciamento Bluetooth (PyGTK3 — substitui yad).
Fecha ao perder foco ou pressionar Escape.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # noqa: E402

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PYTHON_BIN = str(SCRIPT_DIR / ".venv" / "bin" / "python")
if not pathlib.Path(PYTHON_BIN).exists():
    PYTHON_BIN = sys.executable
BT_SCRIPT = str(SCRIPT_DIR / "bluetooth_polybar.py")

CSS = b"""
window {
    background-color: #1e1e2e;
}
.popup-box {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
}
.section {
    background-color: #313244;
    border-radius: 6px;
    margin: 4px 8px;
    padding: 4px 8px;
}
.section-title {
    color: #6c7086;
    font-size: 9pt;
    margin-bottom: 2px;
}
label { color: #cdd6f4; }
button {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 4px;
    padding: 3px 10px;
    min-height: 0;
}
button:hover { background-color: #585b70; }
button:disabled { color: #6c7086; }
button.close-btn {
    background-color: transparent;
    color: #6c7086;
    font-size: 9pt;
    margin: 2px 8px 6px 8px;
}
button.connect-btn { color: #a6e3a1; }
button.disconnect-btn { color: #f38ba8; }
button.scan-btn { color: #fab387; }
button.power-btn { color: #cba6f7; }
.device-row {
    background-color: transparent;
    border-radius: 4px;
    padding: 4px 6px;
}
.device-row:hover { background-color: #45475a; }
.device-row.selected-device { background-color: #45475a; }
.device-row label { color: #cdd6f4; font-size: 9pt; }
.status-connected { color: #a6e3a1; }
.status-disconnected { color: #6c7086; }
.status-scanning { color: #fab387; }
"""


def _run_bt(mode: str, extra: list[str] | None = None) -> str:
    cmd = [PYTHON_BIN, BT_SCRIPT, "--mode", mode]
    if extra:
        cmd.extend(extra)
    # modo buscar dorme 10s dentro do subprocess + overhead dbus
    timeout = 25 if mode == "buscar" else 15
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def _parse_devices(raw: str) -> list[dict]:
    """Formato tab-sep: mac \\t nome \\t status \\t tooltip"""
    devices = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            devices.append({
                "mac": parts[0].strip(),
                "nome": parts[1].strip(),
                "status": parts[2].strip(),
                "tooltip": parts[3].strip() if len(parts) > 3 else "",
            })
    return devices


class JanelaBluetooth(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(type=Gtk.WindowType.POPUP)
        self._selected_mac: str = ""
        self._scanning = False

        self._apply_css()
        self._build()
        self._carregar_dispositivos()
        self._posicionar()

        self.connect("key-press-event", self._on_key)
        self.connect("focus-out-event", self._on_focus_out)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class("popup-box")
        self.add(outer)

        title = Gtk.Label(label="  Gerenciador Bluetooth")
        title.set_xalign(0)
        title.set_margin_top(8)
        title.set_margin_start(8)
        title.get_style_context().add_class("section-title")
        outer.pack_start(title, False, False, 0)

        # Lista de dispositivos
        list_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        list_section.get_style_context().add_class("section")
        outer.pack_start(list_section, True, True, 0)

        self._list_label = Gtk.Label(label="Dispositivos no histórico")
        self._list_label.set_xalign(0)
        self._list_label.get_style_context().add_class("section-title")
        list_section.pack_start(self._list_label, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(400, 160)
        list_section.pack_start(scroll, True, True, 0)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.connect("row-selected", self._on_row_selected)
        scroll.add(self._listbox)

        # Status bar
        self._status_label = Gtk.Label(label="Selecione um dispositivo")
        self._status_label.set_xalign(0)
        self._status_label.set_margin_start(8)
        self._status_label.set_margin_bottom(4)
        self._status_label.get_style_context().add_class("section-title")
        outer.pack_start(self._status_label, False, False, 0)

        # Botões de ação
        btn_section = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_section.set_margin_start(8)
        btn_section.set_margin_end(8)
        btn_section.set_margin_bottom(4)
        outer.pack_start(btn_section, False, False, 0)

        self._btn_connect = Gtk.Button(label="⚡ Conectar")
        self._btn_connect.get_style_context().add_class("connect-btn")
        self._btn_connect.connect("clicked", self._on_conectar)
        self._btn_connect.set_sensitive(False)
        btn_section.pack_start(self._btn_connect, True, True, 0)

        self._btn_disconnect = Gtk.Button(label="✕ Desconectar")
        self._btn_disconnect.get_style_context().add_class("disconnect-btn")
        self._btn_disconnect.connect("clicked", self._on_desconectar)
        self._btn_disconnect.set_sensitive(False)
        btn_section.pack_start(self._btn_disconnect, True, True, 0)

        self._btn_scan = Gtk.Button(label="🔍 Buscar (10s)")
        self._btn_scan.get_style_context().add_class("scan-btn")
        self._btn_scan.connect("clicked", self._on_buscar)
        btn_section.pack_start(self._btn_scan, True, True, 0)

        self._btn_power = Gtk.Button(label="⏻ BT On/Off")
        self._btn_power.get_style_context().add_class("power-btn")
        self._btn_power.connect("clicked", self._on_toggle_power)
        btn_section.pack_start(self._btn_power, True, True, 0)

        close_btn = Gtk.Button(label="Fechar")
        close_btn.get_style_context().add_class("close-btn")
        close_btn.connect("clicked", lambda _: self.destroy())
        outer.pack_start(close_btn, False, False, 0)

    def _carregar_dispositivos(self) -> None:
        raw = _run_bt("list")
        devices = _parse_devices(raw)

        for child in self._listbox.get_children():
            self._listbox.remove(child)

        if not devices:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("device-row")
            row.add(Gtk.Label(label="  Nenhum dispositivo no histórico"))
            row._mac = ""  # type: ignore[attr-defined]
            self._listbox.add(row)
        else:
            for dev in devices:
                row = Gtk.ListBoxRow()
                row.get_style_context().add_class("device-row")
                row._mac = dev["mac"]  # type: ignore[attr-defined]
                row._status = dev["status"]  # type: ignore[attr-defined]

                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

                # Ícone de status
                connected = "conectado" in dev["status"].lower()
                status_icon = "🔵" if connected else "⚪"
                lbl_icon = Gtk.Label(label=status_icon)
                hbox.pack_start(lbl_icon, False, False, 0)

                # Nome
                lbl_nome = Gtk.Label(label=dev["nome"])
                lbl_nome.set_xalign(0)
                hbox.pack_start(lbl_nome, True, True, 0)

                # Status
                lbl_status = Gtk.Label(label=dev["status"])
                ctx = lbl_status.get_style_context()
                if connected:
                    ctx.add_class("status-connected")
                else:
                    ctx.add_class("status-disconnected")
                hbox.pack_start(lbl_status, False, False, 0)

                row.add(hbox)
                self._listbox.add(row)

        self._listbox.show_all()

    def _on_row_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            self._selected_mac = ""
            self._btn_connect.set_sensitive(False)
            self._btn_disconnect.set_sensitive(False)
            return

        mac = getattr(row, "_mac", "")
        self._selected_mac = mac
        has_device = bool(mac)
        self._btn_connect.set_sensitive(has_device)
        self._btn_disconnect.set_sensitive(has_device)

    def _on_conectar(self, _btn) -> None:
        if not self._selected_mac:
            return
        self._set_status("Conectando…")
        self._btn_connect.set_sensitive(False)

        def _do():
            _run_bt("conectar", ["--mac", self._selected_mac])
            GLib.idle_add(self._after_action, "Conectado!")

        threading.Thread(target=_do, daemon=True).start()

    def _on_desconectar(self, _btn) -> None:
        if not self._selected_mac:
            return
        self._set_status("Desconectando…")

        def _do():
            _run_bt("desconectar", ["--mac", self._selected_mac])
            GLib.idle_add(self._after_action, "Desconectado.")

        threading.Thread(target=_do, daemon=True).start()

    def _on_buscar(self, _btn) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._btn_scan.set_label("🔍 Buscando…")
        self._btn_scan.set_sensitive(False)
        self._set_status("Buscando dispositivos por 10 segundos…", "scanning")

        def _do():
            _run_bt("buscar")
            GLib.idle_add(self._after_busca)

        threading.Thread(target=_do, daemon=True).start()

    def _after_busca(self) -> None:
        self._scanning = False
        self._btn_scan.set_label("🔍 Buscar (10s)")
        self._btn_scan.set_sensitive(True)
        self._set_status("Busca concluída. Lista atualizada.")
        self._carregar_dispositivos()

    def _on_toggle_power(self, _btn) -> None:
        self._set_status("Alternando Bluetooth…")

        def _do():
            _run_bt("toggle-power")
            GLib.idle_add(self._after_action, "Bluetooth alternado.")

        threading.Thread(target=_do, daemon=True).start()

    def _after_action(self, msg: str) -> None:
        self._set_status(msg)
        self._btn_connect.set_sensitive(bool(self._selected_mac))
        self._btn_disconnect.set_sensitive(bool(self._selected_mac))
        self._carregar_dispositivos()

    def _set_status(self, msg: str, classe: str = "") -> None:
        self._status_label.set_text(msg)
        ctx = self._status_label.get_style_context()
        for c in ["status-connected", "status-scanning", "section-title"]:
            ctx.remove_class(c)
        if classe == "scanning":
            ctx.add_class("status-scanning")
        else:
            ctx.add_class("section-title")

    def _on_key(self, _win, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_focus_out(self, _win, _event) -> bool:
        if not self._scanning:
            self.destroy()
        return False

    def _posicionar(self) -> None:
        self.show_all()
        self.realize()

        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        _screen, px, py = pointer.get_position()

        w, h = self.get_size()
        sw = display.get_default_screen().get_width()
        sh = display.get_default_screen().get_height()

        x = max(0, min(px - w // 2, sw - w - 4))
        y = py - h - 8
        if y < 0:
            y = py + 28

        self.move(x, y)


def main() -> None:
    import warnings
    warnings.filterwarnings("ignore")
    os.environ.setdefault("NO_AT_BRIDGE", "1")

    win = JanelaBluetooth()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
