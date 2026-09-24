from flask import Blueprint, request, jsonify, send_file
import requests
import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.database import get_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

ocr_bp = Blueprint("ocr", __name__)

OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_URL = "https://api.ocr.space/parse/image"

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

@ocr_bp.route("/status", methods=["GET"])
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

@ocr_bp.route("/ocr", methods=["POST"])
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

@ocr_bp.route("/ocr", methods=["GET"])
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
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, created_at FROM ocr_results ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@ocr_bp.route("/ocr/paginado", methods=["GET"])
@jwt_required()
def paginado():
    """
    Lista os OCRs com paginação e filtro de busca
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
      - name: limite
        in: query
        type: integer
        required: false
      - name: busca
        in: query
        type: string
        required: false
    responses:
      200:
        description: Resultados paginados retornados com sucesso.
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
            SELECT id, filename, created_at FROM ocr_results
            WHERE filename LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            (f"%{busca}%", limite, offset)
        )
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM ocr_results WHERE filename LIKE ?", (f"%{busca}%",))
    else:
        cursor.execute(
            """
            SELECT id, filename, created_at FROM ocr_results
            WHERE user_id = ? AND filename LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?
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

@ocr_bp.route("/ocr/<int:item_id>", methods=["GET"])
@jwt_required()
def buscar(item_id):
    """
    Busca os detalhes de um item OCR por ID
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
    responses:
      200:
        description: Detalhes encontrados.
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

@ocr_bp.route("/ocr/<int:item_id>/imagem", methods=["GET"])
@jwt_required()
def obter_imagem(item_id):
    """
    Download da imagem original
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
    responses:
      200:
        description: Imagem JPEG.
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

@ocr_bp.route("/ocr/<int:item_id>/texto", methods=["GET"])
@jwt_required()
def baixar_texto(item_id):
    """
    Download do texto extraído em .txt
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
    responses:
      200:
        description: Arquivo de texto gerado.
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

@ocr_bp.route("/ocr/<int:item_id>", methods=["PUT"])
@jwt_required()
def atualizar(item_id):
    """
    Atualiza o texto extraído
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
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            texto:
              type: string
    responses:
      200:
        description: Atualizado com sucesso.
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

@ocr_bp.route("/ocr/<int:item_id>", methods=["DELETE"])
@jwt_required()
def deletar(item_id):
    """
    Remove um registro de OCR
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
    responses:
      200:
        description: Removido com sucesso.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ocr_results WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Removido", "id": item_id}), 200