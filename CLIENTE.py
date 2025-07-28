import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from datetime import datetime

class ChatClient:
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 5050
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.username = None
        self.current_chat = None
        self.current_chat_type = None
        self.my_groups = []
        self.chat_history = {}
        
        self.setup_gui()
        
    def setup_gui(self):
        """Configura a interface gráfica"""
        self.root = tk.Tk()
        self.root.title("Mensageria Avançada")
        self.root.geometry("1000x700")
        
        # Frame esquerdo (contatos e grupos)
        left_frame = tk.Frame(self.root, width=250, bg="#f0f0f0")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Status
        self.status_frame = tk.Frame(left_frame, bg="#e0e0e0")
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)
        self.status_label = tk.Label(self.status_frame, text="Desconectado", bg="#e0e0e0")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Abas
        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Aba Contatos
        self.contacts_frame = tk.Frame(self.notebook)
        self.contacts_list = tk.Listbox(self.contacts_frame, font=("Arial", 11))
        self.contacts_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.contacts_list.bind('<<ListboxSelect>>', self.select_contact)
        
        # Aba Grupos
        self.groups_frame = tk.Frame(self.notebook)
        self.groups_list = tk.Listbox(self.groups_frame, font=("Arial", 11))
        self.groups_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.groups_list.bind('<<ListboxSelect>>', self.select_group)
        
        self.notebook.add(self.contacts_frame, text="Contatos")
        self.notebook.add(self.groups_frame, text="Grupos")
        
        # Botões
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(btn_frame, text="+ Contato", command=self.add_contact).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(btn_frame, text="+ Grupo", command=self.create_group).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(btn_frame, text="Convidar", command=self.show_invite_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Frame direito (chat)
        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Título do chat
        self.chat_title = tk.Label(right_frame, text="Selecione um chat", font=("Arial", 12, "bold"), bg="#e0e0e0")
        self.chat_title.pack(fill=tk.X, padx=10, pady=5)
        
        # Área de mensagens
        self.chat_area = scrolledtext.ScrolledText(right_frame, state='disabled', wrap=tk.WORD, font=("Arial", 12))
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Entrada de mensagem
        input_frame = tk.Frame(right_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.message_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        tk.Button(input_frame, text="Enviar", command=self.send_message).pack(side=tk.RIGHT)
        
        # Menu de contexto
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Editar", command=self.edit_message)
        self.context_menu.add_command(label="Apagar", command=self.delete_message)
        self.chat_area.bind("<Button-3>", self.show_context_menu)
        
        # Tags para formatação
        self.chat_area.tag_config('system', foreground='blue')
        self.chat_area.tag_config('deleted', foreground='gray')
        self.chat_area.tag_config('my_message', foreground='green')
        
        # Inicia conexão
        self.connect()

    def connect(self):
        """Conecta ao servidor"""
        self.username = simpledialog.askstring("Nome de Usuário", "Digite seu nome:", parent=self.root)
        if not self.username:
            self.root.destroy()
            return
            
        try:
            self.client_socket.connect((self.host, self.port))
            self.client_socket.send(self.username.encode('utf-8'))
            
            # Recebe confirmação e histórico inicial
            response = json.loads(self.client_socket.recv(16384).decode('utf-8'))  # Buffer maior para histórico
            if response.get('status') == 'success':
                self.status_label.config(text=f"Conectado como {self.username}")
                self.process_initial_history(response.get('history', {}))
                threading.Thread(target=self.receive_messages, daemon=True).start()
                self.root.mainloop()
            else:
                messagebox.showerror("Erro", response.get('message', "Erro desconhecido"))
                self.root.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar: {e}")
            self.root.destroy()

    def process_initial_history(self, history_data):
        """Processa o histórico inicial recebido do servidor"""
        # Histórico individual
        for key, messages in history_data.get('individual', {}).items():
            other_user = key[0] if key[0] != self.username else key[1]
            history_key = f"individual_{other_user}"
            self.chat_history[history_key] = messages
        
        # Histórico de grupos
        for group, messages in history_data.get('group', {}).items():
            history_key = f"group_{group}"
            self.chat_history[history_key] = messages

    def receive_messages(self):
        """Recebe mensagens do servidor"""
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                    
                message = json.loads(data.decode('utf-8'))
                print(f"Cliente recebeu: {message}")
                
                if message.get('type') == 'update':
                    self.update_contact_list(message.get('contacts', []), message.get('groups', []))
                elif message.get('type') == 'group_invite':
                    self.handle_group_invite(message)
                elif message.get('type') in ['text', 'private_message', 'group_message', 'system']:
                    self.process_received_message(message)
                    
            except json.JSONDecodeError:
                print("Erro ao decodificar mensagem")
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
                self.status_label.config(text="Desconectado do servidor")
                break

    def process_received_message(self, message):
        if message.get('type') == 'group_message':
            history_key = f"group_{message.get('group')}"
        elif message.get('type') == 'private_message':
            other_user = message.get('sender') if message.get('sender') != self.username else message.get('recipient')
            history_key = f"individual_{other_user}"
        else:
            history_key = "system"

        if history_key not in self.chat_history:
            self.chat_history[history_key] = []
        self.chat_history[history_key].append(message)

        current_key = f"{self.current_chat_type}_{self.current_chat}" if self.current_chat else None

        if message.get('sender') == 'Server' and message.get('type') == 'private_message':
            self.display_message(message)
            return

        if history_key == current_key or message.get('type') == 'system':
            self.display_message(message)

    def display_message(self, message_data):
        """Exibe uma mensagem no chat"""
        self.chat_area.config(state='normal')
        
        try:
            if message_data.get('type') == 'system':
                msg = f"SISTEMA: {message_data.get('message', '')}\n"
                self.chat_area.insert(tk.END, msg, 'system')
            else:
                sender = message_data.get('sender', '')
                msg_content = message_data.get('message', '')
                if isinstance(msg_content, dict):
                    msg_content = msg_content.get('message', '')
                
                timestamp = message_data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
                
                if message_data.get('deleted', False):
                    msg = f"[{timestamp}] {sender} apagou uma mensagem\n"
                    self.chat_area.insert(tk.END, msg, 'deleted')
                else:
                    is_my_message = sender == self.username
                    prefix = f"[{timestamp}] {sender}: "
                    if message_data.get('edited', False):
                        prefix = f"[{timestamp}] {sender} (editado): "
                    
                    msg = prefix + str(msg_content) + "\n"
                    tags = ('my_message',) if is_my_message else ()
                    self.chat_area.insert(tk.END, msg, tags)
        
        except Exception as e:
            print(f"Erro ao exibir mensagem: {e}")
            self.chat_area.insert(tk.END, f"Erro ao processar mensagem\n")
        
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def handle_group_invite(self, invite_data):
        """Lida com convite para grupo"""
        response = messagebox.askyesno(
            "Convite para Grupo",
            f"{invite_data['invited_by']} te convidou para o grupo {invite_data['group_name']}.\nDeseja entrar?",
            parent=self.root
        )
        
        if response:
            try:
                self.client_socket.send(json.dumps({
                    'type': 'invite_to_group',
                    'group_name': invite_data['group_name'],
                    'contact_name': self.username
                }).encode('utf-8'))
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao aceitar convite: {e}")

    def update_contact_list(self, contacts, groups):
        """Atualiza as listas de contatos e grupos"""
        print(f"Contatos atualizados: {contacts}")
        print(f"Grupos atualizados: {groups}")
        self.contacts_list.delete(0, tk.END)
        for contact in contacts:
            if contact != self.username:
                self.contacts_list.insert(tk.END, contact)
        
        self.my_groups = groups
        self.groups_list.delete(0, tk.END)
        for group in groups:
            self.groups_list.insert(tk.END, group)

    def send_message(self):
        """Envia uma mensagem"""
        message = self.message_entry.get().strip()
        if not message or not self.current_chat:
            return
            
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            if self.current_chat_type == 'group':
                msg_data = {
                    'type': 'group_message',
                    'group': self.current_chat,
                    'message': message,
                    'timestamp':  timestamp
                }
            # Atualização local imediata APENAS para o remetente
                self.process_received_message({
                 'type': 'group_message',
                 'sender': self.username,
                 'message': message,
                 'timestamp': timestamp,
                 'group': self.current_chat,
                 'self_sent': True  # Marca como mensagem própria
            })
            else:
                msg_data = {
                    'type': 'private_message',
                    'recipient': self.current_chat,
                    'message': {
                        'recipient': self.current_chat,
                        'message': message
                    },
                    'timestamp': timestamp
                }
            

            
            # Atualização local para mensagens privadas
            self.process_received_message({
                'type': 'private_message',
                'sender': self.username,
                'message': {'recipient': self.current_chat, 'message': message},
                'timestamp': timestamp,
                'recipient': self.current_chat,
                'self_sent': True
            })
            self.client_socket.send(json.dumps(msg_data).encode('utf-8'))
            self.message_entry.delete(0, tk.END)
        
        except Exception as e:
          messagebox.showerror("Erro", f"Falha ao enviar: {e}")

    def select_contact(self, event):
        """Seleciona um contato para conversar"""
        selection = self.contacts_list.curselection()
        if selection:
            self.current_chat = self.contacts_list.get(selection[0])
            self.current_chat_type = 'individual'
            self.chat_title.config(text=f"Chat com {self.current_chat}")
            self.load_chat_history()

    def select_group(self, event):
        """Seleciona um grupo para conversar"""
        selection = self.groups_list.curselection()
        if selection:
            self.current_chat = self.groups_list.get(selection[0])
            self.current_chat_type = 'group'
            self.chat_title.config(text=f"Grupo: {self.current_chat}")
            self.load_chat_history()

    def load_chat_history(self):
        """Carrega o histórico do chat selecionado"""
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        if not self.current_chat:
            return
            
        history_key = f"{self.current_chat_type}_{self.current_chat}"
        
        if history_key in self.chat_history:
            for message in self.chat_history[history_key]:
                self.display_message(message)
        
        self.chat_area.config(state='disabled')

    def add_contact(self):
        """Adiciona um novo contato"""
        contact = simpledialog.askstring("Adicionar Contato", "Nome do contato:", parent=self.root)
        if contact:
            try:
                self.client_socket.send(json.dumps({
                    'type': 'add_contact',
                    'contact_name': contact
                }).encode('utf-8'))
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao adicionar contato: {e}")

    def create_group(self):
        """Cria um novo grupo"""
        group_name = simpledialog.askstring("Novo Grupo", "Nome do grupo:", parent=self.root)
        if group_name:
            try:
                self.client_socket.send(json.dumps({
                    'type': 'create_group',
                    'group_name': group_name
                }).encode('utf-8'))
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao criar grupo: {e}")

    def show_invite_dialog(self):
        """Mostra diálogo para convidar para grupo"""
        if not self.current_chat_type == 'group':
            messagebox.showwarning("Aviso", "Selecione um grupo primeiro", parent=self.root)
            return
            
        invite_window = tk.Toplevel(self.root)
        invite_window.title(f"Convidar para {self.current_chat}")
        invite_window.geometry("300x400")
        
        tk.Label(invite_window, text="Contatos disponíveis:").pack(pady=5)
        
        contacts_listbox = tk.Listbox(invite_window, selectmode=tk.MULTIPLE)
        contacts_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for contact in self.contacts_list.get(0, tk.END):
            contacts_listbox.insert(tk.END, contact)
        
        def send_invites():
            selected = [contacts_listbox.get(i) for i in contacts_listbox.curselection()]
            for contact in selected:
                try:
                    self.client_socket.send(json.dumps({
                        'type': 'invite_to_group',
                        'group_name': self.current_chat,
                        'contact_name': contact
                    }).encode('utf-8'))
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao convidar {contact}: {e}", parent=invite_window)
            invite_window.destroy()
        
        tk.Button(invite_window, text="Convidar Selecionados", command=send_invites).pack(pady=10)

    def show_context_menu(self, event):
        """Mostra menu de contexto"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def edit_message(self):
        """Edita uma mensagem"""
        pass

    def delete_message(self):
        """Apaga uma mensagem"""
        pass

if __name__ == "__main__":
    client = ChatClient()