import tkinter as tk
from tkinter import scrolledtext

def enviar_mensagem():
    mensagem = entrada_mensagem.get()
    if mensagem.strip() != "":
        area_mensagens.config(state='normal')
        area_mensagens.insert(tk.END, f"Você: {mensagem}\n")
        area_mensagens.config(state='disabled')
        entrada_mensagem.delete(0, tk.END)
        area_mensagens.yview(tk.END)  # Scroll automático para a última linha

# Cria a janela principal
janela = tk.Tk()
janela.title("Mensageria Estilo WhatsApp")
janela.geometry("400x500")

# Área de mensagens com scrollbar
area_mensagens = scrolledtext.ScrolledText(janela, wrap=tk.WORD, state='disabled', bg="white", font=("Arial", 12))
area_mensagens.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Frame inferior para entrada de mensagem e botão enviar
frame_inferior = tk.Frame(janela)
frame_inferior.pack(fill=tk.X, padx=10, pady=10)

# Campo de entrada de mensagem
entrada_mensagem = tk.Entry(frame_inferior, font=("Arial", 12))
entrada_mensagem.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

# Botão de enviar
botao_enviar = tk.Button(frame_inferior, text="Enviar", command=enviar_mensagem)
botao_enviar.pack(side=tk.RIGHT)

# Inicia o loop da interface
janela.mainloop()
