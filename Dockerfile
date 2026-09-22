FROM python:3.10-slim

# Instala dependências do sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho principal
WORKDIR /app

# Copia o requirements para a raiz do container
COPY requirements.txt .

# Força a instalação limpa de todas as dependências listadas
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto
COPY . .

EXPOSE 8000

# Executa o módulo apontando para a pasta correta
CMD ["python", "-m", "backend.api"]