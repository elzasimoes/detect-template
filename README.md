## 📹 Template Detector - Aplicação Flask para Detecção de Templates em Vídeos
### 📋 Descrição
Este projeto é uma aplicação web desenvolvida em Flask que permite aos usuários enviar um vídeo e uma imagem template para detecção de correspondências. Utiliza OpenCV para processamento de imagem e Socket.IO para comunicação em tempo real com o cliente.

### ✨ Funcionalidades
- Upload de vídeo e imagem template
- Ajuste de sensibilidade (threshold) para detecção
- Processamento assíncrono com feedback em tempo real
- Interface responsiva com Bootstrap 5
- Sistema de logs completo

### 🛠️ Tecnologias Utilizadas
- Backend: Python 3.11, Flask, Flask-SocketIO
- Processamento de Imagem: OpenCV
- Frontend: HTML5, Bootstrap 5, Socket.IO

### Infraestrutura: 
- Docker, Docker Compose

### 🚀 Como Executar o Projeto
#### Pré-requisitos
- Docker e Docker Compose instalados
- Python 3.11 (opcional para desenvolvimento local)

##### Método 1: Usando Docker (Recomendado)
1. Clone o repositório
```bash
git clone https://github.com/elzasimoes/detect-template.git
cd detect-template
```
2. Construa e inicie o container:
```bash
docker compose up --build
```
3. Acesse a aplicação em: http://localhost:5000

##### Método 2: Execução Local (Sem Docker)

1. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate     # Windows
```
2. Instale as dependências
```bash
pip install -r requirements.txt
```

3. Execute a aplicação
```bash
python app.py
```

4. Acesse a aplicação em: http://localhost:5000

#### Logs
A aplicação gera logs detalhados em:

- Console (durante execução)
- logs/template_detector.log (arquivo rotativo)


🛑 Parando a Aplicação
```bash
docker compose down
```