# Bluetooth + Polybar

Módulo Polybar para gerenciamento de dispositivos Bluetooth com histórico persistente e janela visual.

Ícone muda de cor conforme o estado:

| Estado | Ícone | Cor |
|--------|-------|-----|
| BT desligado / indisponível | 󰂲 | cinza |
| Ligado, nenhum dispositivo conectado | 󰂯 | azul |
| 1 ou mais dispositivos conectados | 󰂱 | verde |

## Dependências do sistema

```
yad  python3  dbus-python (via pip)
```

A biblioteca `dbus-python` depende do pacote de sistema `libdbus-glib-1-dev` (Debian/Ubuntu) ou equivalente:

```bash
sudo apt install libdbus-glib-1-dev
```

## Instalação

```bash
cd bluetooth-polybar
mkdir -p ~/.config/polybar/scripts
cp bluetooth_polybar.py adaptador_bluetooth.py historico.py ~/.config/polybar/scripts/
cp polybar-bluetooth-toggle.sh ~/.config/polybar/scripts/
chmod +x ~/.config/polybar/scripts/polybar-bluetooth-toggle.sh
python -m venv ~/.config/polybar/scripts/.venv
~/.config/polybar/scripts/.venv/bin/pip install -r requirements.txt
```

Adicione o bloco de `polybar-module.ini` no seu `~/.config/polybar/config.ini` e inclua `bluetooth` em `modules-right`.

## Cliques no módulo

- **Esquerdo**: abre/fecha a janela de gerenciamento (yad)
- **Direito**: liga/desliga o Bluetooth

## Janela de gerenciamento

Exibe todos os dispositivos do histórico com status atual (conectado / emparelhado / histórico). Botões disponíveis:

- **Conectar** — conecta sem desconectar dispositivos já ativos
- **Desconectar** — desconecta um dispositivo específico
- **Buscar** — inicia busca por novos dispositivos por 10 segundos
- **Ligar / Desligar** — alterna o estado do adaptador Bluetooth

## Testes

```bash
cd bluetooth-polybar
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
# todos os testes
.venv/bin/pytest tests/
# um único arquivo
.venv/bin/pytest tests/test_historico.py
# um único teste
.venv/bin/pytest tests/test_historico.py::test_registrar_um_dispositivo
```
