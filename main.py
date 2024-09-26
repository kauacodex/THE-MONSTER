import threading
import keyboard
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
import easyocr  # Importa o EasyOCR
import numpy as np  # Importa o NumPy
from groq import Groq

# Coloque sua chave da API aqui
GROQ_API_KEY = "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"

# Configurar o cliente da API do Groq com a chave da API
client = Groq(api_key=GROQ_API_KEY)

# Inicializa o leitor do EasyOCR
reader = easyocr.Reader(["pt"])  # 'pt' para português


class SelectionArea:
    """Classe para a área de seleção da captura de tela."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Remove a barra de título
        self.root.geometry("300x300+0+0")  # Tamanho inicial da janela
        self.root.attributes("-alpha", 0.3)  # Transparente
        self.root.bind("<Escape>", self.close)

        self.canvas = tk.Canvas(self.root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Variáveis de controle
        self.start_x = None
        self.start_y = None
        self.rect = None

        # Bind dos eventos do mouse
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.root.update_idletasks()
        self.root.attributes("-topmost", True)  # Manter a janela no topo
        self.root.geometry(
            f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0"
        )  # Ajusta a janela para ocupar toda a tela
        self.root.mainloop()

    def on_button_press(self, event):
        """Captura a posição inicial do mouse."""
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline="red"
        )

    def on_mouse_drag(self, event):
        """Atualiza o retângulo conforme o mouse é arrastado."""
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        """Captura a área selecionada e fecha a aplicação."""
        x1 = min(self.start_x, event.x)
        x2 = max(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        y2 = max(self.start_y, event.y)

        self.root.destroy()  # Fecha a janela

        # Captura a imagem da área selecionada
        self.capture_area(x1, y1, x2, y2)

    def capture_area(self, x1, y1, x2, y2):
        """Captura a imagem da área selecionada."""
        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        extracted_text = self.extract_text(image)

        if extracted_text.strip():
            response = self.get_ai_response(extracted_text)
            self.show_popup(response)
        else:
            self.show_popup("Nenhum texto foi extraído.")

    def extract_text(self, image):
        """Extrai texto da imagem capturada usando EasyOCR."""
        image_np = np.array(image)  # Converte a imagem para um array NumPy
        result = reader.readtext(image_np, detail=0)  # detail=0 retorna apenas o texto
        return " ".join(result)  # Junta as partes do texto extraído

    def get_ai_response(self, question):
        """Envia a pergunta para a IA do Groq e recebe a resposta com instruções específicas."""
        prompt = (
            f'Responda à pergunta: "{question}" de forma clara. '
            f"Para perguntas de múltipla escolha, indique a letra da resposta correta e explique brevemente sua escolha, CASO NAO FOR UMA NOTICIA, IGNORE OS PROMPTS A SEGUIR, MAS SEMPRE PESQUISE CONSUNTE FONTES PARA ACERTAR AS RESPOSTAS, PRINCIPALMENTE FORUNS. NÃO LEIA APENAS O TITULO DA NOTICIA, E SIM ELA COMPLETA. EVITE RESPOSTAS MUITO GRANDES, SEMPRE RESUMIDAMENTE. SE A RESPOSTA CORRETA FOR UMA, NAO COLOQUE OUTRA NA RESPOSTA FINAL. "
            f"Para perguntas de preencher lacuna, forneça a resposta correta e uma breve explicação. "
            f"Concentre-se em dados verificáveis e evite suposições, exiba a data que foram feitas as pesquisas, busque respostas mais precisas na internet não exite em pesquisas, sempre pesquise, Pesquise a resposta em outras fontes. Sempre busque responstas mais atualizadas e de fontes confiaveis. Não questione a pergunta, se a pergunta for feita do jeito que tá, é pra ser assim. somente responda."
        )

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
        )

        # Separa resposta e explicação
        response_content = chat_completion.choices[0].message.content
        if "Explicação:" in response_content:  # Supondo que o modelo usa esse formato
            answer, explanation = response_content.split("Explicação:", 1)
            return f"Resposta: {answer.strip()}\n\nExplicação: {explanation.strip()}"
        return response_content  # Retorna a resposta se não houver explicação

    def show_popup(self, message):
        """Exibe um popup com a mensagem da IA."""
        messagebox.showinfo("Resposta da IA", message)

    def close(self, event=None):
        """Fecha a aplicação."""
        self.root.quit()  # Usa quit() para encerrar o loop principal do Tkinter
        self.root.destroy()  # Fecha a janela


def start_selection_area():
    """Inicia a área de seleção."""
    SelectionArea()


def on_hotkey():
    """Função que ativa a seleção quando a combinação de teclas é pressionada."""
    threading.Thread(
        target=start_selection_area
    ).start()  # Inicia a área de seleção em uma nova thread


# Registra a combinação de teclas
keyboard.add_hotkey("win+shift+d", on_hotkey)

# Mantém o script rodando
print("Pressione Win + Shift + D para capturar a tela e extrair texto.")
keyboard.wait()  # O script ficará rodando indefinidamente
