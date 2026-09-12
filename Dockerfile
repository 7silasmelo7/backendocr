# 1. Usa uma imagem oficial do Python, versão leve (slim)
FROM python:3.10-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Copia o arquivo de dependências para dentro do container
COPY requirements.txt .

# 4. Instala as bibliotecas listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o restante do código do seu projeto para o container
COPY . .

# 6. Informa ao Docker que a aplicação vai rodar na porta 8000
EXPOSE 8000

# 7. Define o comando padrão para iniciar a sua API
CMD ["python", "-m", "backend.api"]