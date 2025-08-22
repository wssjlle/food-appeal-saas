from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}"

@app.route('/')
def home():
    return jsonify({"message": "FoodAppeal API - Imagens que Vendem"})

@app.route('/process', methods=['POST'])
def process_image():
    try:
        # Receber imagem e prompt
        if 'image' not in request.files:
            return jsonify({"error": "Nenhuma imagem enviada"}), 400
            
        image_file = request.files['image']
        prompt = request.form.get('prompt', 'Edite esta imagem para deixar mais apetitosa e profissional para redes sociais.')
        
        # Converter imagem para base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Montar payload para Gemini
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": image_file.content_type or "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        }

        # Chamar API do Gemini
        response = requests.post(GEMINI_URL, json=payload)
        
        if response.status_code != 200:
            return jsonify({"error": "Erro na API do Gemini", "details": response.text}), response.status_code

        result = response.json()

        # Extrair resposta do Gemini
        descricao = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Sem descrição")

        return jsonify({
            "status": "success",
            "descricao": descricao,
            "prompt_usado": prompt
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))