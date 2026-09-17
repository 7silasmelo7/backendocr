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




load_dotenv()

app = Flask(__name__)
CORS(app)

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
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    # Verifica se o usuário existe e se a senha criptografada bate
    if user and check_password_hash(user["password_hash"], senha):
        identidade = {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        }
        token_acesso = create_access_token(identity=str(user["id"]))
        return jsonify({"token": token_acesso, "email": email, "role": user["role"]}), 200
    
    return jsonify({"erro": "Credenciais inválidas"}), 401

@app.route("/auth/esqueci-senha", methods=["POST"])
def esqueci_senha():
    dados = request.json
    email = dados.get("email")

    # 1. Verificar se o e-mail existe no banco
    # 2. Gerar um token único (ex: token = str(uuid.uuid4()))
    # 3. Salvar esse token na coluna 'reset_token' do usuário
    # 4. Enviar um e-mail com o link contendo o token (ex: http://seu-site.com/reset?token=XYZ)
    
    # Nota: Para envio real de e-mails, você precisará usar bibliotecas como 'flask-mail' ou APIs como SendGrid.
    return jsonify({"mensagem": "Se o e-mail existir, um link de recuperação será enviado."}), 200


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "API funcionando"}), 200




@app.route("/ocr", methods=["POST"])
@jwt_required()
def ocr():

    usuario_atual = get_jwt_identity()
    user_id = int(get_jwt_identity())

    if "arquivo" not in request.files:
        return jsonify({"erro": "Envie um arquivo no campo 'arquivo'"}), 400

    arquivo = request.files["arquivo"]
    filename = arquivo.filename
    conteudo = arquivo.read()

    texto = processar_ocr_externo(filename, conteudo)

    # Gera a data e hora  baseada no fuso horário local
    fuso_local = ZoneInfo("America/Sao_Paulo")
    data_atual_local = datetime.now(fuso_local).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    
    # Salva data e hora local no banco
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, created_at FROM ocr_results ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/ocr/paginado", methods=["GET"])
@jwt_required()
def paginado():
    # Pega o ID diretamente do token e converte para número
    user_id = int(get_jwt_identity())

    # Consulta o banco para descobrir se é 'master' ou 'user'
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
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")
    hash_senha = generate_password_hash(senha)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Força o role 'master' diretamente no banco
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'master')", (email, hash_senha))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Usuário MASTER criado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": "Email já cadastrado"}), 400


@app.route("/ocr/<int:item_id>", methods=["GET"])
@jwt_required()
def buscar(item_id):
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ocr_results WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Removido", "id": item_id}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)