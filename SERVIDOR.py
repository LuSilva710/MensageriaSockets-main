import socket
import threading
import json
import traceback
from datetime import datetime
from dtos import CommandDTO

class Server:
    def __init__(self, host='127.0.0.1', port=5050):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen()
        
        self.clients = {}
        self.contacts = {}
        self.groups = {'Geral': set()}
        self.messages = {'individual': {}, 'group': {'Geral': []}}
        self.running = True

        self.commands: list[CommandDTO] = []
        self._load_commands()
        
        print(f"[SERVIDOR OUVINDO] {self.host}:{self.port}")

    def update_all_clients(self):
        online_users = list(self.clients.keys())
        for username, client in self.clients.items():
            try:
                user_groups = [g for g in self.groups if username in self.groups[g]]
                update_data = {
                    'type': 'update',
                    'contacts': [u for u in online_users if u != username],
                    'groups': user_groups,
                    'all_groups': list(self.groups.keys())
                }
                client.send(json.dumps(update_data).encode('utf-8'))
            except Exception as e:
                print(f"[ERRO UPDATE] {username}: {e}")
                self.handle_disconnect(username)

    def handle_disconnect(self, username):
        if username in self.clients:
            try:
                self.clients[username].close()
            except:
                pass
            del self.clients[username]
        
        if username in self.contacts:
            self.contacts[username]['status'] = 'offline'
        
        for group in self.groups.values():
            if username in group:
                group.remove(username)
        
        print(f"[DESCONECTADO] {username}")
        self.update_all_clients()

    def broadcast(self, message, sender=None, group_name='Geral', msg_type='text'):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg_data = {
                'type': 'group_message' if group_name != 'individual' else 'private_message',
                'sender': sender,
                'message': message['message'] if group_name == 'individual' else message,
                'timestamp': timestamp,
                'group': group_name if group_name != 'individual' else None
            }

            if group_name != 'individual' and msg_data["message"]["message"].startswith("/"):
                self._handle_command(msg_data)
                return

            if group_name == 'individual':
                recipient = message['recipient']
                msg_data['recipient'] = recipient
                
                key = tuple(sorted((sender, recipient)))
                if key not in self.messages['individual']:
                    self.messages['individual'][key] = []
                
                msg_data['id'] = len(self.messages['individual'][key])
                self.messages['individual'][key].append(msg_data)
                
                if recipient in self.clients:
                    try:
                        self.clients[recipient].send(json.dumps(msg_data).encode('utf-8'))
                        print(f"[MSG PRIVADA] {sender} -> {recipient}")
                    except:
                        self.handle_disconnect(recipient)
            else:
                if group_name not in self.messages['group']:
                    self.messages['group'][group_name] = []
                
                msg_data['id'] = len(self.messages['group'][group_name])
                self.messages['group'][group_name].append(msg_data)
                
                print(f"[DEBUG] Enviando para grupo {group_name}: {self.groups[group_name]}")
                
                for member in self.groups.get(group_name, set()):
                    if member in self.clients:
                        try:
                            self.clients[member].send(json.dumps(msg_data).encode('utf-8'))
                            print(f"[MSG GRUPO] {group_name}: {sender} -> {member}")
                        except:
                            self.handle_disconnect(member)
            
                    
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"[ERRO BROADCAST] {error_info}")

    def handle_client(self, conn, addr):
        username = None
        try:
            username = conn.recv(1024).decode('utf-8').strip()
            if not username:
                raise ValueError("Nome de usuário vazio")
                
            self.clients[username] = conn
            self.contacts[username] = {'status': 'online'}
            self.groups['Geral'].add(username)
            
            print(f"[NOVA CONEXÃO] {username} de {addr}")
            
            conn.send(json.dumps({
                'type': 'connection_ack',
                'message': f"Bem-vindo {username}",
                'status': 'success',
                'your_name': username,
                'history': {
                    'individual': {k: v for k, v in self.messages['individual'].items() if username in k},
                    'group': {g: msgs for g, msgs in self.messages['group'].items() if username in self.groups.get(g, set())}
                }
            }).encode('utf-8'))
            
            self.update_all_clients()
            
            while self.running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                        
                    data = json.loads(data.decode('utf-8'))
                    print(f"[MSG RECEBIDA] {username}: {data.get('type')}")
                    
                    if data.get('type') == 'group_message':
                        self.broadcast(data, username, data['group'])
                    elif data.get('type') == 'private_message':
                        self.broadcast(data, username, 'individual')
                    elif data.get('type') == 'create_group':
                        group_name = data['group_name']
                        if group_name not in self.groups:
                            self.groups[group_name] = set([username])
                            self.messages['group'][group_name] = []
                            print(f"[NOVO GRUPO] {group_name} por {username}")
                            self.update_all_clients()
                    elif data.get('type') == 'invite_to_group':
                        group_name = data['group_name']
                        contact_name = data['contact_name']
                        if group_name in self.groups and contact_name in self.clients:
                            if contact_name not in self.groups[group_name]:
                                self.groups[group_name].add(contact_name)
                                print(f"[CONVITE ACEITO] {contact_name} entrou em {group_name}")
                                self.update_all_clients()
                                self.clients[contact_name].send(json.dumps({
                                    'type': 'group_invite',
                                    'group_name': group_name,
                                    'invited_by': username
                                }).encode('utf-8'))
                            
                except json.JSONDecodeError:
                    print(f"[ERRO JSON] {username}")
                except Exception as e:
                    print(f"[ERRO CLIENTE] {username}: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERRO CONEXÃO] {addr}: {e}")
        finally:
            if username:
                self.handle_disconnect(username)

    def _load_commands(self, path="config/commands.json"):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if len(data) == 0:
            print(f"[ERRO] Falha ao carregar comandos em: {path}")
            return

        for command in data:
            self.commands.append(
                CommandDTO(
                    command["name"],
                    command["description"],
                    command["usage"],
                    command["min_args"]
                ))
        print(f"[INFO] {len(data)} comandos carregados.")

    def _get_command(self, command_name: str) -> CommandDTO:
        for c in self.commands:
            if c.name == command_name:
                return c
        return None

    def _handle_command(self, msg_data):
        user_message = msg_data["message"]["message"]
        command_str = user_message[1:]
        sender = msg_data["sender"]

        args = command_str.split()
        command = self._get_command(args[0])

        if command == None:
            self._send_private_message(sender, "Comando não existe.")
            return

        if (len(args) >= 2 and args[1] in ["-h", "--help"]) or len(args) < command.min_args:
            self._send_private_message(sender, f"\ndesc: {command.description}\nusage:\n    {command.usage}")
            return

        self._interpret_command(command, msg_data)

    def _interpret_command(self, command: CommandDTO, msg_data: dict):
        sender = msg_data["sender"]
        group_name = msg_data["group"]
        args = msg_data["message"]["message"][1:].split()
        match command.name:
            case "history":
                self._history_command(sender, group_name)
            case "delete":
                self._delete_command(sender, group_name, args)
            case "edit":
                self._edit_command(sender, group_name, args)

    def _edit_command(self, sender: str, group_name: str, args: list[str]):
        message_id = int(args[1])
        new_message = args[2]

        message = self._get_message_by_id(group_name, message_id, sender)
        if len(message) > 0:
            message["message"] = new_message
            message["edited"] = True
            self._update_message(message, group_name, sender)


    def _delete_command(self, sender: str, group_name: str, args: list[str]):
        message_id = int(args[1])
        message = self._get_message_by_id(group_name, message_id, sender)

        if len(message) > 0:
            message["deleted"] = True
            self._update_message(message, group_name, sender)

    def _history_command(self, sender: str, group_name: str):
        history = self._get_user_message_history(sender, group_name)
        string_builder = "\n"
        string_builder += f"ID: Mensagem\n"
        for message in history:
            string_builder += f"{message[0]}: {message[1]}\n"

        self._send_private_message(sender, string_builder)

    def _get_message_by_id(self, group_name: str, message_id: int, sender: str) -> dict:
        group = self.messages["group"][group_name]
        for message in group:
            if message["id"] == message_id and message["sender"] == sender:
                return message
        return {}

    """
    Reenvia uma mensagem para todos os membros de um grupo(usado para atualizar uma mensagem quando ela é apagada/editada)
    """
    def _update_message(self, message: dict, group_name: str, sender: str):
        for member in self.groups.get(group_name, set()):
            if member in self.clients:
                try:
                    self.clients[member].send(json.dumps(message).encode('utf-8'))
                    print(f"[MSG GRUPO] {group_name}: {sender} -> {member}")
                except:
                    self.handle_disconnect(member)

    """ 
    Retorna uma lista com o histórico de mensagens de um usuário em um grupo no seguinte formato:
        (id_mensagem, mensagem)
    """
    def _get_user_message_history(self, username: str, group_name: str) -> list[tuple]:
        history = []
        group = self.messages["group"][group_name]
        for message in group:
            if message["sender"] == username and not message.get("deleted", False):
                message_data = (message["id"], message["message"]["message"])
                history.append(message_data)

        return history

    # Envia mensagem do servidor para um usuário
    def _send_private_message(self, receiver: str, message: str):
        message_dict = {"recipient": receiver, "message": message}
        self.broadcast(message_dict, sender="Server", group_name='individual')

    def start(self):
        print(f"[SERVIDOR INICIADO] {self.host}:{self.port}")
        try:
            while self.running:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
                print(f"[CONEXÕES ATIVAS] {threading.active_count() - 1}")
        except KeyboardInterrupt:
            print("\n[DESLIGANDO SERVIDOR]")
            self.running = False
            for client in list(self.clients.values()):
                try:
                    client.close()
                except:
                    pass
            self.server.close()

if __name__ == "__main__":
    server = Server()
    server.start()