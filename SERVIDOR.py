import socket
import threading
import json
from datetime import datetime

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
                    if member in self.clients and member != sender:
                        try:
                            self.clients[member].send(json.dumps(msg_data).encode('utf-8'))
                            print(f"[MSG GRUPO] {group_name}: {sender} -> {member}")
                        except:
                            self.handle_disconnect(member)
            
                    
        except Exception as e:
            print(f"[ERRO BROADCAST] {e}")

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