from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv 
from backend.database import init_db
from flask_jwt_extended import JWTManager
from flasgger import Swagger

# Importação dos Blueprints
from backend.routes_auth import auth_bp
from backend.routes_ocr import ocr_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuração do Swagger
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

# Configuração do JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "4<!Nc6s Gy!j;<^:a>mJ")
jwt = JWTManager(app)
app.config["JWT_VERIFY_SUB"] = False

# Inicialização do Banco de Dados
init_db()

# Registro dos Blueprints na aplicação Flask
app.register_blueprint(auth_bp)
app.register_blueprint(ocr_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)