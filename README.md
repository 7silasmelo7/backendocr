

# 🔍 Leitor Inteligente de OCR com Autenticação e Níveis de Acesso

> Sistema completo de **reconhecimento óptico de caracteres (OCR)** com arquitetura desacoplada, autenticação JWT, múltiplos níveis de acesso (User/Master), documentação interativa via Swagger e persistência em SQLite.

---

## 📌 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Tecnologias](#-tecnologias)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Documentação da API (Swagger)](#-documentação-da-api-swagger)
- [Como Executar](#-como-executar)
- [Endpoints da API](#-endpoints-da-api)
- [Banco de Dados e Permissões](#-banco-de-dados-e-permissões)

---

## 📖 Sobre o Projeto

O **Leitor Inteligente de OCR** é uma aplicação voltada para o processamento e gestão segura de documentos e imagens extraídas via OCR. O sistema conta com:

- **Autenticação Segura:** Controle de acesso baseado em JSON Web Tokens (`flask-jwt-extended`) e senhas encriptadas com Werkzeug.

- **Níveis de Acesso:**

  - **Usuário Comum (`user`):** Visualiza e gere apenas os seus próprios históricos de OCR.
  - **Usuário Master (`master`):** Acesso global e irrestrito a todos os arquivos extraídos por qualquer utilizador do sistema.

- **Integração Externa:** Processamento óptico de caracteres utilizando a [API OCR.space](https://ocr.space/ocrapi) em português.

### Estrutura de Pastas

```
backend/
├── backend/
│   ├── api.py
│   ├── database.py
│   ├── routes_auth.py
│   └── routes_ocr.py
├── .env
├── Dockerfile
└── requirements.txt

```

---

## 🛠️ Tecnologias

| Tecnologia | Finalidade |
|------------|-----------|
| [Python 3.10+](https://python.org) | Linguagem principal do backend |
| [Flask](https://flask.palletsprojects.com/) | Framework para construção da API REST |
| [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) | Gestão de autenticação baseada em tokens JWT |
| [Flasgger](https://github.com/flasgger/flasgger) | Documentação interativa da API baseada em Swagger/OpenAPI |
| [Flask-CORS](https://flask-cors.readthedocs.io/) | Liberação de requisições de origem cruzada para o frontend |
| [Pillow](https://pillow.readthedocs.io/) | Manipulação de imagens |
| [OCR.space API](https://ocr.space/ocrapi) | Reconhecimento óptico de texto |
| [SQLite](https://sqlite.org/) | Banco de dados relacional leve |

---

## ✅ Pré-requisitos


Certifique-se de ter instalado em sua máquina:

- **Python 3.10 ou superior**
- **pip** (incluso com o Python)
- **Docker** (opcional, caso prefira rodar conteinerizado)
- **Chave de API** gratuita do OCR.space

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/7silasmelo7/backendocr

```




### 2. Crie e ative um ambiente virtual


```
cd backend
```

```bash
# Criar
python -m venv venv
```

```bash
# Ativar — Windows
venv\Scripts\activate
```

```bash
# Ativar — Linux / macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

> **💡 Dica:** `pillow-heif` é **opcional** — adiciona suporte a arquivos `.heic` (fotos de iPhone). Pode ser omitido sem impacto no funcionamento principal.

---

### 📡 4. Crie sua conta gratis na OCR.SPACE 



OCR_API_KEY: https://ocr.space/ocrapi/freekey

---



### 🔐 5. Crie sua chave encriptografada

JWT_SECRET_KEY: https://jwtsecretkeygenerator.com/

---

## ⚙️ Configure o arquivo .env

Crie um arquivo .env na raiz do backend contendo:


```env
OCR_API_KEY=sua_chave_ocr_space_aqui
JWT_SECRET_KEY=sua_chave_secreta_jwt_aqui
```

> ⚠️ **Importante:** Nunca exponha ou versione este arquivo. Adicione `.env` ao seu `.gitignore`.

---

## ⚙️ Execute o servidor Flask

```

python -m backend.api

```

O servidor iniciará localmente em: http://localhost:8000

---

## 🐳 Executando com Docker (Recomendado)

Este projeto contém um Dockerfile configurado para rodar a aplicação flask em um container isolado, cumprindo os requisitos de conteinerização.

1. Construindo a imagem no docker

```
docker build --no-cache -t backend-ocr .
```

2. Criando o container com um banco de dados no docker

```
docker run -d -p 8000:8000 -v dados_ocr:/app --name container-backend backend-ocr
```

---

## 📚 Documentação da API (Swagger)

Com o servidor em execução, acesse a interface interativa do Swagger no seu navegador para testar todas as rotas, simular autenticação e verificar os payloads:

👉 http://localhost:8000/apidocs/

Para testar as rotas protegidas:

  1. Faça o login com seu email e senha cadastrada na rota POST /auth/login para obter o seu token JWT.

  2. Ao obter seu token procura o botão verde no topo da página "Authorize" na opção "Value" coloque Bearer e cole o token gerado.

  3. Clique no botão verde "Authorize".

---

## 🔌 Endpoints da API

### Autenticação e Gestão de Utilizadores

- POST /auth/cadastro — Cadastra um novo utilizador comum (user).

- POST /auth/login — Autentica o utilizador e devolve o token JWT de acesso e a sua respetiva   role.

- POST /auth/criar-master — Cria um utilizador com privilégios administrativos (master).

- POST /auth/esqueci-senha — Endpoint base para solicitação de recuperação de senha.

### Sistema e OCR

- GET /status — Verifica se a API está online e a operar corretamente.

- POST /ocr — Realiza o upload de um arquivo (imagem/PDF), processa via OCR externo e persiste no banco vinculado ao ID do utilizador autenticado.

- GET /ocr — Lista todos os registos de OCR.

- GET /ocr/paginado — Lista os resultados de forma paginada e com filtros de busca (aplica restrições automáticas caso seja user comum ou traz visão global caso seja master).

- GET /ocr/{id} — Retorna os detalhes de um registo específico.

- GET /ocr/{id}/imagem — Faz o download da imagem original armazenada.

- GET /ocr/{id}/texto — Faz o download do texto extraído em formato .txt.

- PUT /ocr/{id} — Atualiza o texto extraído de um registo.

- DELETE /ocr/{id} — Remove um registo de OCR do banco de dados.

---

## 🗄️ Estrutura do Banco de Dados (SQLite)

O sistema cria automaticamente o arquivo ocr_results.db contendo duas tabelas principais:
   
   1. users: Gere os utilizadores (id, email, password_hash, reset_token, role).
      
   2. ocr_results: Armazena os dados extraídos (id, user_id, filename, image em BLOB, text,created_at) com chave estrangeira ligada à tabela de utilizadores.
---




