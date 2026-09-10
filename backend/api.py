from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
from dotenv import load_dotenv 
from backend.database import get_connection, init_db
from datetime import datetime
from zoneinfo import ZoneInfo


load_dotenv()

app = Flask(__name__)
CORS(app)


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


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "API funcionando"}), 200


@app.route("/ocr", methods=["POST"])
def ocr():
    if "arquivo" not in request.files:
        return jsonify({"erro": "Envie um arquivo no campo 'arquivo'"}), 400

    arquivo = request.files["arquivo"]
    filename = arquivo.filename
    conteudo = arquivo.read()

    texto = processar_ocr_externo(filename, conteudo)

    # Gera a data e hora atual baseada no fuso horário local
    fuso_local = ZoneInfo("America/Sao_Paulo")
    data_atual_local = datetime.now(fuso_local).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    
    # Salva explicitamente a data e hora local no banco
    cursor.execute(
        "INSERT INTO ocr_results (filename, image, text, created_at) VALUES (?, ?, ?, ?)",
        (filename, conteudo, texto, data_atual_local)
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": novo_id, "texto": texto}), 201


@app.route("/ocr", methods=["GET"])
def listar_ocr():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, created_at FROM ocr_results ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/ocr/paginado", methods=["GET"])
def paginado():
    pagina = int(request.args.get("pagina", 1))
    limite = int(request.args.get("limite", 10))
    busca = request.args.get("busca", "")

    offset = (pagina - 1) * limite

    conn = get_connection()
    cursor = conn.cursor()
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

    cursor.execute(
        "SELECT COUNT(*) FROM ocr_results WHERE filename LIKE ?",
        (f"%{busca}%",)
    )
    total = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "resultados": [dict(row) for row in rows]
    })


@app.route("/ocr/<int:item_id>", methods=["GET"])
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
def deletar(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ocr_results WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Removido", "id": item_id}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)