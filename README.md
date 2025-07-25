# 📡 MensageriaSockets - Sistema de Mensageria em Rede

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)

## 📋 Descrição
Trabalho desenvolvido para a disciplina de **Redes de Computadores** do 5º período de Sistemas de Informação no IFMG, implementando um sistema completo de troca de mensagens utilizando sockets TCP/IP com interface gráfica.

## ✨ Funcionalidades
| Módulo | Descrição |
|--------|-----------|
| **Chat Privado** | Comunicação 1-1 entre usuários |
| **Grupos** | Salas de chat com múltiplos participantes |
| **Histórico** | Armazenamento local das conversas |
| **Contatos** | Listagem de usuários online |
| **Convites** | Sistema para adicionar membros a grupos |

## 🛠️ Tecnologias
- **Backend**:
  - Python 3.8+
  - Sockets TCP/IP
  - Threads para concorrência
- **Frontend**:
  - Tkinter (GUI)
  - JSON para serialização

## 🚀 Instalação
```bash
# Clonar repositório
git clone https://github.com/LuSilva710/MensageriaSockets-main.git
cd MensageriaSockets-main

# Iniciar servidor
python SERVIDOR.py

# Iniciar cliente (em terminal separado)
python CLIENTE.py