import threading
import keyboard
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, ImageFilter, ImageOps
import easyocr  # Importa o EasyOCR
import numpy as np  # Importa o NumPy
from groq import Groq
import os

# Coloque sua chave da API aqui
GROQ_API_KEY = "sua_chave_da_api_aqui"

# Configurar o cliente da API do Groq com a chave da API
client = Groq(api_key=GROQ_API_KEY)

# Inicializa o leitor do EasyOCR
reader = easyocr.Reader(
    ["pt"], model_storage_directory="easyocr_model"
)  # 'pt' para português

# Define o nome do arquivo onde a imagem será salva
IMAGE_FILENAME = "captured_image.png"
FILTERED_IMAGE_FILENAME = "filtered_image.png"  # Nome para a imagem filtrada


def cls():
    os.system("cls" if os.name == "nt" else "clear")


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
        """Captura a imagem da área selecionada e salva como PNG."""
        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))

        # Salva a imagem capturada como PNG, substituindo a anterior
        image.save(IMAGE_FILENAME)

        # Pré-processamento da imagem
        filtered_image = self.preprocess_image(image)

        # Salva a imagem filtrada para referência
        filtered_image.save(FILTERED_IMAGE_FILENAME)

        extracted_text = self.extract_text(filtered_image)

        if extracted_text.strip():
            response = self.get_ai_response(extracted_text)
            self.show_popup(response)
        else:
            self.show_popup("Nenhum texto foi extraído.")

    def preprocess_image(self, image):
        """Pré-processa a imagem para melhorar a detecção de texto."""
        # Converte para escala de cinza
        image = image.convert("L")
        # Aplica um leve desfoque para suavizar a imagem
        image = image.filter(
            ImageFilter.GaussianBlur(radius=1)
        )  # Aumentar o raio, se necessário
        # Aumenta o contraste
        image = ImageOps.autocontrast(image)

        return image

    def extract_text(self, image):
        """Extrai texto da imagem capturada usando EasyOCR."""
        image_np = np.array(image)  # Converte a imagem para um array NumPy
        result = reader.readtext(
            image_np,
            detail=1,
            min_size=10,  # Ajuste o min_size para garantir que textos pequenos sejam capturados
            paragraph=True,  # Mantém a formatação em parágrafos
        )

        # Formatação do texto extraído
        formatted_text = ""

        for item in result:
            if len(item) == 3:  # Verifica se há 3 elementos (bbox, text, prob)
                _, text, _ = item  # Ignora prob
                formatted_text += text.strip() + " "  # Mantém o texto na mesma linha
            elif len(item) == 2:  # Se houver apenas bbox e text
                _, text = item
                formatted_text += text.strip() + " "  # Mantém o texto na mesma linha
            else:
                continue  # Ignora qualquer item que não tenha 2 ou 3 elementos

        # Remover espaços em branco e garantir que quebras de linha sejam respeitadas
        formatted_text = formatted_text.strip().replace("  ", " ")
        return formatted_text  # Retorna o texto formatado

    def get_ai_response(self, question):
        """Envia a pergunta para a IA do Groq e recebe a resposta com instruções específicas."""
        prompt = (
            f'Por favor, responda à pergunta: "{question}" de maneira clara e direta. '
            f"As respostas devem ser curtas e concisas, focando na informação essencial. "
            f"Use as seguintes diretrizes para a resposta:\n\n"
            f"1. **Formato da Resposta:**\n"
            f"   - Inicie com: Resposta: \n"
            f"   - Em seguida, coloque: Explicação: \n"
            f"   - Para perguntas de múltipla escolha, analise cada opção e indique a letra da resposta correta. "
            f"Explique por que essa é a resposta correta e forneça informações relevantes sobre as opções apresentadas.\n"
            f"   - Para verdadeiro ou falso, use Verdadeiro (V) ou Falso (F).\n"
            f"   - Para preencher lacunas, forneça a resposta correta e uma breve explicação.\n\n"
            f"2. **Fontes e Pesquisa:**\n"
            f"   - Sempre que possível, baseie suas respostas em fontes confiáveis. Pesquise em sites relevantes, especialmente para perguntas relacionadas a regiões ou países. "
            f"Se a resposta não estiver disponível em fontes confiáveis, utilize seu conhecimento.\n"
            f"   - Não leia apenas os títulos das notícias; consulte o conteúdo completo para garantir precisão. "
            f"Se a pergunta for bem formulada, responda diretamente sem questionamentos. Lembre-se de avaliar a veracidade das opções.\n"
            f"   - Cite a fonte e, se aplicável, a data da publicação (se a informação for de um único site confiável; se vários, não coloque a data).\n\n"
            f"3. **Considerações Finais:**\n"
            f"   - Evite respostas longas e complexas. Concentre-se em dados verificáveis e sempre busque as informações mais atualizadas. "
            f"Uma única resposta correta é permitida. Caso não encontre informações online, utilize seu conhecimento para responder.\n"
            f"   - Para perguntas de múltipla escolha, verifique os dados mais recentes sobre os refugiados ucranianos e mencione as opções discutidas."
        )

        cls()
        print("Pressione Windows + Shift + D para iniciar a seleção!")
        print("")
        print(question)

        # Chamando a API do Groq para obter a resposta
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
        )

        # Retorna a resposta
        return chat_completion.choices[0].message.content.strip()

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
cls()
print("Pressione Win + Shift + D para capturar a tela e extrair texto.")
keyboard.wait()  # O script ficará rodando indefinidamente
