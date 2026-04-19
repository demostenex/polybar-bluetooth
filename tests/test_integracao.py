"""Testes de integração — bluetooth_polybar.py via subprocess.

D-Bus é mockado via monkeypatch para rodar em CI sem hardware Bluetooth.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import textwrap

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "bluetooth_polybar.py"


def _rodar(args: list[str], stub_dir: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    """Executa bluetooth_polybar via subprocess com sys.path controlado."""
    stub = str(stub_dir) if stub_dir else ""
    script_dir = str(SCRIPT.parent)

    # script_dir inserido primeiro (vai para [0]), depois stub_dir é inserido em [0]
    # resultado final: sys.path = [stub_dir, script_dir, ...]
    code = (
        "import sys, runpy; "
        + f"sys.path.insert(0, {script_dir!r}); "
        + (f"sys.path.insert(0, {stub!r}); " if stub else "")
        + f"sys.argv = [{str(SCRIPT)!r}] + {args!r}; "
        + f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Helper: cria um stub de dbus como arquivo .py acessível via PYTHONPATH
# ---------------------------------------------------------------------------

@pytest.fixture()
def stub_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Cria um diretório com stubs de dbus e adaptador mockado."""
    stub = tmp_path / "stubs"
    stub.mkdir()

    # stub do módulo dbus
    (stub / "dbus.py").write_text(
        textwrap.dedent("""\
            SystemBus = None
            Interface = None
            Boolean = bool
        """),
        encoding="utf-8",
    )

    # sobrescreve adaptador_bluetooth para retornar dados controlados
    (stub / "adaptador_bluetooth.py").write_text(
        textwrap.dedent("""\
            class AdaptadorBluetoothProtocol: pass

            class DispositivoBluetooth:
                def __init__(self, mac, nome, conectado, emparelhado):
                    self.mac = mac
                    self.nome = nome
                    self.conectado = conectado
                    self.emparelhado = emparelhado

            class AdaptadorBluetoothDBus:
                def esta_disponivel(self): return True
                def esta_ligado(self): return True
                def listar_dispositivos(self):
                    return [
                        DispositivoBluetooth("AA:BB:CC:DD:EE:FF", "Fone Sony", True, True),
                        DispositivoBluetooth("11:22:33:44:55:66", "Caixa JBL", False, True),
                    ]
                def conectar(self, mac): pass
                def desconectar(self, mac): pass
                def ligar(self): pass
                def desligar(self): pass
                def buscar(self, segundos=10): pass
        """),
        encoding="utf-8",
    )

    return stub

# ---------------------------------------------------------------------------
# Testes de integração
# ---------------------------------------------------------------------------

def test_modo_module_retorna_icone_conectado(stub_dir, tmp_path):
    resultado = _rodar(["--mode", "module"], stub_dir=stub_dir)
    assert resultado.returncode == 0
    assert "󰂱" in resultado.stdout


def test_modo_module_saida_unica_linha(stub_dir):
    resultado = _rodar(["--mode", "module"], stub_dir=stub_dir)
    linhas = [l for l in resultado.stdout.splitlines() if l.strip()]
    assert len(linhas) == 1


def test_modo_list_retorna_dispositivos(stub_dir, tmp_path):
    historico = tmp_path / "hist.json"
    historico.write_text(
        json.dumps([
            {"mac": "AA:BB:CC:DD:EE:FF", "nome": "Fone Sony", "ultimo_uso": "2025-01-10T12:00:00"},
        ]),
        encoding="utf-8",
    )
    resultado = _rodar(
        ["--mode", "list", "--historico-arquivo", str(historico)],
        stub_dir=stub_dir,
    )
    assert resultado.returncode == 0
    assert "Fone Sony" in resultado.stdout


def test_modo_list_saida_tab_separada(stub_dir, tmp_path):
    historico = tmp_path / "hist.json"
    historico.write_text(
        json.dumps([
            {"mac": "AA:BB:CC:DD:EE:FF", "nome": "Fone Sony", "ultimo_uso": "2025-01-10T12:00:00"},
        ]),
        encoding="utf-8",
    )
    resultado = _rodar(
        ["--mode", "list", "--historico-arquivo", str(historico)],
        stub_dir=stub_dir,
    )
    for linha in resultado.stdout.strip().splitlines():
        colunas = linha.split("\t")
        assert len(colunas) == 4, f"Linha não tem 4 colunas: {linha!r}"


def test_modo_module_sem_dbus_nao_falha(tmp_path):
    """Simula ausência do D-Bus: o módulo não deve travar ou lançar exceção."""
    stub = tmp_path / "stubs_sem_dbus"
    stub.mkdir()

    (stub / "adaptador_bluetooth.py").write_text(
        textwrap.dedent("""\
            class AdaptadorBluetoothProtocol: pass
            class DispositivoBluetooth: pass
            class AdaptadorBluetoothDBus:
                def __init__(self): raise RuntimeError("D-Bus indisponível")
        """),
        encoding="utf-8",
    )
    (stub / "dbus.py").write_text("", encoding="utf-8")

    resultado = _rodar(["--mode", "module"], stub_dir=stub)
    assert resultado.returncode == 0
    assert resultado.stdout.strip() != ""
