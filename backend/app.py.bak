import os
import base64
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Configuração da API do Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route("/process", methods=["POST"])
def process():
    try:
        # 1. Receber imagem do usuário
        if "image" not in request.files:
            return jsonify({"error": "Nenhuma imagem enviada"}), 400

        image_file = request.files["image"]
        image_bytes = image_file.read()

        # 2. Prompt fixo para tratar imagem
        prompt = (
            "Realce a nitidez e aumente a clareza geral, "
            "intensifique as cores de forma natural, "
            "dê aparência de frescor, suculência e saúde, "
            "valorizando a textura sem exageros artificiais. "
            "A iluminação deve valorizar o alimento, como se fosse foto profissional."
        )

        # 3. Chamar Gemini
        result = model.generate_content([prompt, image_bytes])

        # 4. Verificar se veio imagem como saída
        part = result.candidates[0].content.parts[0]
        if hasattr(part, "inline_data"):
            image_base64 = part.inline_data.data
            image_bytes = base64.b64decode(image_base64)

            # Retornar a imagem já tratada
            return Response(image_bytes, mimetype="image/png")

        # Caso venha apenas texto
        return jsonify({"result": result.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
