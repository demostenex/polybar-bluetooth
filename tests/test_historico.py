"""Testes unitários — historico.py"""

from __future__ import annotations

import datetime
import json
import pathlib

import pytest

from historico import Historico, RegistroDispositivo


# ---------------------------------------------------------------------------
# RegistroDispositivo
# ---------------------------------------------------------------------------

def test_registro_para_dict():
    data = datetime.datetime(2025, 1, 15, 10, 30, 0)
    reg = RegistroDispositivo("aa:bb:cc:dd:ee:ff", "Fone Sony", data)
    d = reg.para_dict()
    assert d["mac"] == "AA:BB:CC:DD:EE:FF"
    assert d["nome"] == "Fone Sony"
    assert d["ultimo_uso"] == "2025-01-15T10:30:00"


def test_registro_de_dict():
    dados = {"mac": "AA:BB:CC:DD:EE:FF", "nome": "Fone Sony", "ultimo_uso": "2025-01-15T10:30:00"}
    reg = RegistroDispositivo.de_dict(dados)
    assert reg.mac == "AA:BB:CC:DD:EE:FF"
    assert reg.nome == "Fone Sony"
    assert reg.ultimo_uso == datetime.datetime(2025, 1, 15, 10, 30, 0)


def test_registro_normaliza_mac_para_maiusculo():
    data = datetime.datetime.now()
    reg = RegistroDispositivo("aa:bb:cc:dd:ee:ff", "Caixa", data)
    assert reg.mac == "AA:BB:CC:DD:EE:FF"


# ---------------------------------------------------------------------------
# Historico
# ---------------------------------------------------------------------------

@pytest.fixture()
def arquivo_historico(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "bluetooth_history.json"


@pytest.fixture()
def historico(arquivo_historico: pathlib.Path) -> Historico:
    return Historico(arquivo_historico)


def test_carregar_arquivo_inexistente(historico):
    assert historico.carregar() == []


def test_carregar_arquivo_corrompido(arquivo_historico):
    arquivo_historico.write_text("isso nao e json", encoding="utf-8")
    h = Historico(arquivo_historico)
    assert h.carregar() == []


def test_registrar_cria_arquivo(historico, arquivo_historico):
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    assert arquivo_historico.exists()


def test_registrar_um_dispositivo(historico):
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    registros = historico.carregar()
    assert len(registros) == 1
    assert registros[0].mac == "AA:BB:CC:DD:EE:FF"
    assert registros[0].nome == "Fone Sony"


def test_registrar_atualiza_existente(historico):
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony v2")
    registros = historico.carregar()
    assert len(registros) == 1
    assert registros[0].nome == "Fone Sony v2"


def test_registrar_ordem_por_recencia(historico):
    historico.registrar("11:22:33:44:55:66", "Caixa JBL")
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    registros = historico.carregar()
    assert registros[0].mac == "AA:BB:CC:DD:EE:FF"
    assert registros[1].mac == "11:22:33:44:55:66"


def test_remover_dispositivo(historico):
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    historico.registrar("11:22:33:44:55:66", "Caixa JBL")
    historico.remover("AA:BB:CC:DD:EE:FF")
    registros = historico.carregar()
    assert len(registros) == 1
    assert registros[0].mac == "11:22:33:44:55:66"


def test_remover_inexistente_nao_falha(historico):
    historico.registrar("AA:BB:CC:DD:EE:FF", "Fone Sony")
    historico.remover("00:00:00:00:00:00")
    assert len(historico.carregar()) == 1


def test_registrar_mac_minusculo_normalizado(historico):
    historico.registrar("aa:bb:cc:dd:ee:ff", "Fone")
    registros = historico.carregar()
    assert registros[0].mac == "AA:BB:CC:DD:EE:FF"
