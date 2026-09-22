from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
from dotenv import load_dotenv 
from backend.database import get_connection, init_db
from datetime import datetime
from zoneinfo import ZoneInfo

from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import uuid
from flasgger import Swagger




load_dotenv()

app = Flask(__name__)
CORS(app)

swagger = Swagger(app, template={
    "info": {
        "title": "API de OCR com Níveis de Acesso",
        "description": "Documentação oficial do MVP de OCR utilizando Flask, JWT e SQLite.",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Exemplo: 'Bearer seu_token_aqui'"
        }
    }
})

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "4<!Nc6s Gy!j;<^:a>mJ")
jwt = JWTManager(app)

app.config["JWT_VERIFY_SUB"] = False


OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_URL = "https://api.ocr.space/parse/image"

init_db()




def processar_ocr_externo(filename, file_bytes):
    try:
        payload = {
            "apikey": OCR_API_KEY,
            "language": "por",
            "isOverlayRequired": False
        }

        files = {
            "file": (filename, file_bytes)
        }

        response = requests.post(OCR_URL, data=payload, files=files)
        data = response.json()

        if data.get("IsErroredOnProcessing"):
            return "Erro no OCR externo."

        texto = data["ParsedResults"][0]["ParsedText"]
        return texto if texto.strip() else "Nenhum texto encontrado."
    except Exception as e:
        print("Erro OCR externo:", e)
        return "Erro ao processar OCR externo."

@app.route("/auth/cadastro", methods=["POST"])
def cadastro():
    """
    Cadastra um novo usuário comum
    ---
    tags:
      - Autenticação
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "usuario@email.com"
            senha:
              type: string
              example: "123456"
    responses:
      201:
        description: Usuário cadastrado com sucesso!
      400:
        description: Email e senha são obrigatórios ou email já cadastrado.
    """
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({"erro": "Email e senha são obrigatórios"}), 400

    hash_senha = generate_password_hash(senha)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hash_senha))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Usuário cadastrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": "Email já cadastrado"}), 400

@app.route("/auth/login", methods=["POST"])
def login():
    """
    Realiza o login do usuário e retorna o token JWT
    ---
    tags:
      - Autenticação
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "usuario@email.com"
            senha:
              type: string
              example: "123456"
    responses:
      200:
        description: Login realizado com sucesso, retorna o token JWT e a role.
      401:
        description: Credenciais inválidas.
    """
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], senha):
        token_acesso = create_access_token(identity=str(user["id"]))
        return jsonify({"token": token_acesso, "email": email, "role": user["role"]}), 200
    
    return jsonify({"erro": "Credenciais inválidas"}), 401

@app.route("/auth/esqueci-senha", methods=["POST"])
def esqueci_senha():
    """
    Solicita a recuperação de senha
    ---
    tags:
      - Autenticação
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "usuario@email.com"
    responses:
      200:
        description: Mensagem informativa de recuperação enviada.
    """
    dados = request.json
    email = dados.get("email")
    return jsonify({"mensagem": "Se o e-mail existir, um link de recuperação será enviado."}), 200


@app.route("/status", methods=["GET"])
def status():
    """
    Verifica o status da API
    ---
    tags:
      - Sistema
    responses:
      200:
        description: API funcionando normalmente.
    """
    return jsonify({"status": "API funcionando"}), 200


@app.route("/ocr", methods=["POST"])
@jwt_required()
def ocr():
    """
    Realiza o upload de uma imagem e processa via OCR externo
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: arquivo
        in: formData
        type: file
        required: true
        description: Imagem a ser processada pelo OCR
    responses:
      201:
        description: OCR processado e salvo com sucesso.
      400:
        description: Arquivo não enviado.
      401:
        description: Token JWT ausente ou inválido.
    """
    user_id = int(get_jwt_identity())

    if "arquivo" not in request.files:
        return jsonify({"erro": "Envie um arquivo no campo 'arquivo'"}), 400

    arquivo = request.files["arquivo"]
    filename = arquivo.filename
    conteudo = arquivo.read()

    texto = processar_ocr_externo(filename, conteudo)

    fuso_local = ZoneInfo("America/Sao_Paulo")
    data_atual_local = datetime.now(fuso_local).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ocr_results (user_id, filename, image, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, filename, conteudo, texto, data_atual_local)
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": novo_id, "texto": texto}), 201


@app.route("/ocr", methods=["GET"])
@jwt_required()
def listar_ocr():
    """
    Lista todos os OCRs cadastrados
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    responses:
      200:
        description: Lista de arquivos recuperada com sucesso.
      401:
        description: Não autorizado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, created_at FROM ocr_results ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/ocr/paginado", methods=["GET"])
@jwt_required()
def paginado():
    """
    Lista os OCRs com paginação e filtro de busca (Respeita regra de acesso Master/User)
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: pagina
        in: query
        type: integer
        required: false
        description: Número da página (padrão 1)
      - name: limite
        in: query
        type: integer
        required: false
        description: Limite de itens por página (padrão 10)
      - name: busca
        in: query
        type: string
        required: false
        description: Termo de busca por nome de arquivo
    responses:
      200:
        description: Resultados paginados retornados com sucesso.
      401:
        description: Não autorizado.
    """
    user_id = int(get_jwt_identity())

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user_db = cursor.fetchone()
    role = user_db["role"] if user_db else "user"

    pagina = int(request.args.get("pagina", 1))
    limite = int(request.args.get("limite", 10))
    busca = request.args.get("busca", "")
    offset = (pagina - 1) * limite

    if role == "master":
        cursor.execute(
            """
            SELECT id, filename, created_at
            FROM ocr_results
            WHERE filename LIKE ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (f"%{busca}%", limite, offset)
        )
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM ocr_results WHERE filename LIKE ?", (f"%{busca}%",))
    else:
        cursor.execute(
            """
            SELECT id, filename, created_at
            FROM ocr_results
            WHERE user_id = ? AND filename LIKE ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, f"%{busca}%", limite, offset)
        )
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM ocr_results WHERE user_id = ? AND filename LIKE ?", (user_id, f"%{busca}%"))
        
    total = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "resultados": [dict(row) for row in rows]
    })


@app.route("/auth/criar-master", methods=["POST"])
def criar_master():
    """
    Cadastra um usuário com privilégios MASTER
    ---
    tags:
      - Autenticação
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "master@email.com"
            senha:
              type: string
              example: "123456"
    responses:
      201:
        description: Usuário MASTER criado com sucesso!
      400:
        description: Erro ao cadastrar ou email já existente.
    """
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")
    hash_senha = generate_password_hash(senha)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'master')", (email, hash_senha))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Usuário MASTER criado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": "Email já cadastrado"}), 400


@app.route("/ocr/<int:item_id>", methods=["GET"])
@jwt_required()
def buscar(item_id):
    """
    Busca os detalhes de um item OCR específico por ID
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID do registro de OCR
    responses:
      200:
        description: Detalhes do OCR encontrados.
      404:
        description: ID não encontrado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ocr_results WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"erro": "ID não encontrado"}), 404

    return jsonify({
        "id": row["id"],
        "filename": row["filename"],
        "texto": row["text"],
        "created_at": row["created_at"]
    })


@app.route("/ocr/<int:item_id>/imagem", methods=["GET"])
@jwt_required()
def obter_imagem(item_id):
    """
    Faz o download da imagem original salva no OCR por ID
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID do registro
    responses:
      200:
        description: Imagem retornada como arquivo JPEG.
      404:
        description: Imagem não encontrada.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image, filename FROM ocr_results WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"erro": "Imagem não encontrada"}), 404

    return send_file(
        io.BytesIO(row["image"]),
        mimetype="image/jpeg",
        download_name=row["filename"]
    )


@app.route("/ocr/<int:item_id>/texto", methods=["GET"])
@jwt_required()
def baixar_texto(item_id):
    """
    Faz o download do texto extraído em formato .txt
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID do registro
    responses:
      200:
        description: Arquivo de texto (.txt) gerado com sucesso.
      404:
        description: ID não encontrado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM ocr_results WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"erro": "ID não encontrado"}), 404

    return send_file(
        io.BytesIO(row["text"].encode("utf-8")),
        mimetype="text/plain",
        download_name=f"ocr_{item_id}.txt"
    )


@app.route("/ocr/<int:item_id>", methods=["PUT"])
@jwt_required()
def atualizar(item_id):
    """
    Atualiza o texto extraído de um registro de OCR
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID do registro
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            texto:
              type: string
              example: "Texto corrigido manualmente"
    responses:
      200:
        description: Registro atualizado com sucesso.
      400:
        description: Campo texto ausente.
    """
    dados = request.json
    if not dados or "texto" not in dados:
        return jsonify({"erro": "Envie JSON com o campo 'texto'"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE ocr_results SET text = ? WHERE id = ?", (dados["texto"], item_id))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Atualizado", "id": item_id}), 200


@app.route("/ocr/<int:item_id>", methods=["DELETE"])
@jwt_required()
def deletar(item_id):
    """
    Remove um registro de OCR do banco de dados
    ---
    tags:
      - OCR
    security:
      - Bearer: []
    parameters:
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID do registro a ser excluído
    responses:
      200:
        description: Registro removido com sucesso.
      401:
        description: Não autorizado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ocr_results WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Removido", "id": item_id}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)