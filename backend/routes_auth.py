from flask import Blueprint, request, jsonify
from backend.database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/cadastro", methods=["POST"])
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

@auth_bp.route("/auth/login", methods=["POST"])
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

@auth_bp.route("/auth/esqueci-senha", methods=["POST"])
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
    return jsonify({"mensagem": "Se o e-mail existir, um link de recuperação será enviado."}), 200

@auth_bp.route("/auth/criar-master", methods=["POST"])
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