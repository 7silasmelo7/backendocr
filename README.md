# 🔍 Leitor Inteligente de OCR

> Sistema completo de **reconhecimento óptico de caracteres (OCR)** que combina uma API REST com uma interface gráfica. Suporta imagens e PDFs, armazena os resultados localmente e permite exportação do texto extraído.

---

## 📌 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Tecnologias](#-tecnologias)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Como Executar](#-como-executar)
- [Endpoints da API](#-endpoints-da-api)
- [Formatos Suportados](#-formatos-suportados)
- [Banco de Dados](#-banco-de-dados)

---

## 📖 Sobre o Projeto

O **Leitor Inteligente de OCR** é composto por dois modos de uso:

- **API REST** (Flask): recebe arquivos via HTTP, processa o OCR e persiste os resultados em um banco SQLite.


A extração de texto é feita por meio da [API OCR.space](https://ocr.space/ocrapi), com suporte ao idioma **português**.

### Estrutura de Pastas

```
backend/
├── backend/
│   ├── api.py         # Servidor Flask — API REST
│   ├── database.py    # Conexão e inicialização do banco SQLite
│   └── .env           # Variáveis de ambiente (não versionar!)
├── package.json
└── ocr_results.db     # Banco de dados (gerado automaticamente)
```

---

## 🛠️ Tecnologias

| Tecnologia | Finalidade |
|------------|-----------|
| [Python 3.10+](https://python.org) | Linguagem principal |
| [Flask](https://flask.palletsprojects.com/) | API REST |
| [Flask-CORS](https://flask-cors.readthedocs.io/) | Liberação de CORS |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | Leitura de PDFs |
| [Pillow](https://pillow.readthedocs.io/) | Manipulação de imagens |
| [OCR.space API](https://ocr.space/ocrapi) | Reconhecimento de texto (OCR) |
| [SQLite](https://sqlite.org/) | Banco de dados local |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Gerenciamento de variáveis de ambiente |

---

## ✅ Pré-requisitos

Certifique-se de ter instalado em sua máquina:

- **Python 3.10 ou superior** → [Download](https://www.python.org/downloads/)
- **pip** (incluso com Python)
- **Git** → [Download](https://git-scm.com/)
- **Chave de API** gratuita do OCR.space → [Obter chave](https://ocr.space/ocrapi)

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd backend
```

### 2. Crie e ative um ambiente virtual

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
pip install flask flask-cors requests Pillow PyMuPDF customtkinter python-dotenv pillow-heif
```

> **💡 Dica:** `pillow-heif` é **opcional** — adiciona suporte a arquivos `.heic` (fotos de iPhone). Pode ser omitido sem impacto no funcionamento principal.

---

## ⚙️ Configuração

Crie ou edite o arquivo `backend/.env` com a sua chave de API:

```env
OCR_API_KEY=SUA_CHAVE_AQUI
```

> ⚠️ **Importante:** Nunca exponha ou versione este arquivo. Adicione `.env` ao seu `.gitignore`.

---

## ▶️ Como Executar

### Modo 1 — API REST (Flask)

```bash
python -m backend.api
```

O servidor iniciará em: **`http://localhost:8000`**

Verifique se está funcionando:

```bash
curl http://localhost:8000/status
# Resposta: {"status": "API funcionando"}
```

---



## 🔌 Endpoints da API

### `GET /status`
Verifica se a API está online.

```bash
curl http://localhost:8000/status
```

---

### `POST /ocr`
Envia um arquivo para OCR e salva o resultado.

```bash
curl -X POST http://localhost:8000/ocr \
  -F "arquivo=@/caminho/para/arquivo.png"
```

**Resposta:**
```json
{
  "id": 1,
  "texto": "Texto extraído do arquivo..."
}
```

---

### `GET /ocr`
Lista todos os resultados salvos.

---

### `GET /ocr/paginado?pagina=1&limite=10&busca=nome`
Lista resultados com **paginação** e **busca por nome de arquivo**.

---

### `GET /ocr/{id}`
Retorna os detalhes de um resultado pelo ID.

---

### `GET /ocr/{id}/imagem`
Faz o download da imagem original vinculada ao resultado.

---

### `GET /ocr/{id}/texto`
Faz o download do texto extraído em formato `.txt`.

---

### `PUT /ocr/{id}`
Atualiza o texto de um resultado existente.

```bash
curl -X PUT http://localhost:8000/ocr/1 \
  -H "Content-Type: application/json" \
  -d '{"texto": "Novo texto corrigido"}'
```

---

### `DELETE /ocr/{id}`
Remove um resultado pelo ID.

```bash
curl -X DELETE http://localhost:8000/ocr/1
```

---

## 📁 Formatos de Arquivo Suportados

| Categoria | Extensões aceitas |
|-----------|------------------|
| **Imagens** | `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.tiff` `.heic` |
| **Documentos** | `.pdf` |

---

## 🗄️ Banco de Dados

O banco **SQLite** é criado automaticamente em `ocr_results.db` na primeira execução. Não é necessária nenhuma configuração adicional.

**Tabela: `ocr_results`**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | `INTEGER` | Chave primária (auto incremento) |
| `filename` | `TEXT` | Nome do arquivo enviado |
| `image` | `BLOB` | Imagem original em binário |
| `text` | `TEXT` | Texto extraído pelo OCR |
| `created_at` | `TIMESTAMP` | Data e hora do processamento |
