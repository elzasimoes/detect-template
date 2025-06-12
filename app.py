import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

import cv2
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder="templates")

# Configuração do SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Configuração de pastas
UPLOAD_FOLDER = "app/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuração de logs
LOG_FOLDER = "app/logs"
os.makedirs(LOG_FOLDER, exist_ok=True)


# Configuração do sistema de logging
def setup_logging():
    """
    Configura o registro em log para a aplicação.

    Configura um manipulador de arquivos rotativo e um manipulador de console com formatos e níveis de log
    específicos. O manipulador de arquivos grava logs em um arquivo com
    rotação, mantendo até 10 arquivos de backup de 1 MB cada. O manipulador
    de console envia logs para o console. O registrador principal é definido como nível DEBUG,
    enquanto o registro detalhado para SocketIO, EngineIO e Werkzeug é
    desativado ao definir seus níveis de log como WARNING.
    """
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_file = os.path.join(LOG_FOLDER, "template_detector.log")

    # Handler para arquivo com rotação (10 arquivos de 1MB cada)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024, backupCount=10, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(logging.INFO)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(logging.DEBUG)

    # Configuração do logger principal
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Desabilitar log verbose do SocketIO
    logging.getLogger("socketio").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


setup_logging()


@app.route("/")
def index():
    """
    Rota principal que exibe a página inicial do aplicativo.

    Returns:
        Response: Renderiza o template 'index.html' que contém o formulário de upload.

    Logs:
        - INFO: Registra quando a página inicial é acessada.
    """
    app.logger.info("Página inicial acessada")
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Processa o upload de arquivos (vídeo e template) e inicia a detecção.

    Recebe via POST:
        - video: Arquivo de vídeo para análise
        - template: Imagem template para busca no vídeo
        - threshold: Valor entre 0-1 para sensibilidade da detecção (opcional, padrão=0.8)

    Returns:
        tuple: Mensagem de status e código HTTP:
            - ("Processing started", 200) em caso de sucesso
            - Mensagens de erro com códigos 400 ou 500 em caso de falha

    Raises:
        Exception: Captura e loga qualquer erro durante o processamento do upload

    Logs:
        - INFO: Início do upload e parâmetros recebidos
        - WARNING: Threshold inválido (usa valor padrão)
        - ERROR: Falhas na validação ou processamento
    """
    try:
        app.logger.info("Iniciando upload de arquivos")

        # Validação básica
        if "video" not in request.files or "template" not in request.files:
            app.logger.error("Arquivos não enviados no request")
            return "Arquivos não enviados", 400

        video = request.files["video"]
        template = request.files["template"]

        # Verificar se arquivos foram selecionados
        if video.filename == "" or template.filename == "":
            app.logger.error("Nenhum arquivo selecionado")
            return "Nenhum arquivo selecionado", 400

        # Obter threshold com valor padrão
        try:
            threshold = float(request.form.get("threshold", 0.8))

            if not 0 <= threshold <= 1:
                raise ValueError
        
        except ValueError:
            app.logger.warning(
                f"Threshold inválido recebido: {request.form.get('threshold')}"
            )
            threshold = 0.8

        app.logger.info(
            f"Parâmetros recebidos - Video: {video.filename}, Template: {template.filename}, Threshold: {threshold}"
        )

        # Salvar arquivos
        video_path = os.path.join(UPLOAD_FOLDER, secure_filename(video.filename))
        template_path = os.path.join(UPLOAD_FOLDER, secure_filename(template.filename))

        video.save(video_path)
        template.save(template_path)

        app.logger.info(f"Arquivos salvos em: {video_path} e {template_path}")

        # Iniciar processamento em thread separada
        socketio.start_background_task(
            process_video, video_path, template_path, threshold
        )

        app.logger.info("Processamento iniciado em thread separada")
        return "Processing started", 200

    except Exception as e:
        app.logger.error(f"Erro durante o upload: {str(e)}", exc_info=True)
        return f"Erro no servidor: {str(e)}", 500


def process_video(video_path, template_path, threshold):
    """
    Processa o vídeo para encontrar o template usando correspondência de padrões.

    Args:
        video_path (str): Caminho para o arquivo de vídeo
        template_path (str): Caminho para a imagem template
        threshold (float): Limiar de correspondência (0-1)

    Processamento:
        1. Abre o vídeo e o template usando OpenCV
        2. Analisa frame a frame usando cv2.matchTemplate()
        3. Emite eventos via Socket.IO com os resultados:
            - template_found: Quando o template é encontrado
            - template_not_found: Quando não encontrado após todo o vídeo
            - processing_error: Em caso de erros

    Logs:
        - INFO: Início do processamento e resultados
        - DEBUG: Progresso a cada 100 frames
        - ERROR: Falhas durante o processamento
    """
    try:
        app.logger.info(f"Iniciando processamento do vídeo: {video_path}")
        start_time = datetime.now()

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            app.logger.error(f"Não foi possível abrir o vídeo: {video_path}")
            socketio.emit("processing_error", {"message": "Erro ao abrir o vídeo"})
            return

        template = cv2.imread(template_path, 0)

        if template is None:
            app.logger.error(f"Não foi possível abrir o template: {template_path}")
            socketio.emit("processing_error", {"message": "Erro ao abrir o template"})
            cap.release()
            return

        # Obter o total de frames para progresso (opcional)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w, h = template.shape[::-1]
        frame_num = 0
        found = False

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_num += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            loc = (res >= threshold).any()

            if loc:
                processing_time = (datetime.now() - start_time).total_seconds()
                app.logger.info(
                    f"Template encontrado no frame {frame_num}. Tempo de processamento: {processing_time:.2f}s"
                )
                socketio.emit(
                    "template_found",
                    {
                        "frame": frame_num,
                        "processing_time": processing_time,
                        "total_frames": total_frames,
                    },
                    callback=lambda: app.logger.debug(
                        "Confirmação de recebimento do cliente"
                    ),
                )
                found = True
                break

        cap.release()

        if not found:
            processing_time = (datetime.now() - start_time).total_seconds()
            app.logger.info(
                f"Template não encontrado. Tempo total: {processing_time:.2f}s"
            )
            socketio.emit(
                "template_not_found",
                {"total_frames": total_frames, "processing_time": processing_time},
                callback=lambda: app.logger.debug(
                    "Confirmação de recebimento do cliente"
                ),
            )

    except Exception as e:
        app.logger.error(
            f"Erro durante o processamento do vídeo: {str(e)}", exc_info=True
        )
        socketio.emit("processing_error", {"message": str(e)})

    finally:
        # Limpeza de arquivos temporários
        try:
            os.remove(video_path)
            os.remove(template_path)
            app.logger.info(
                f"Arquivos temporários removidos: {video_path}, {template_path}"
            )
        except Exception as e:
            app.logger.warning(f"Erro ao remover arquivos temporários: {str(e)}")


if __name__ == "__main__":
    app.logger.info("Iniciando servidor Template Detector")
    try:
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )
    except Exception as e:
        app.logger.critical(f"Erro ao iniciar servidor: {str(e)}", exc_info=True)
    finally:
        app.logger.info("Servidor encerrado")
