# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response # Importar Response para streaming
from flask_cors import CORS
import base64
import requests
import os
import json
from dotenv import load_dotenv
import io

load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Use the correct model ID
MODEL_ID = "gemini-2.0-flash-preview-image-generation"
# Construct the URL for the generateContent endpoint (not streamGenerateContent for now)
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_API_KEY}"

@app.route('/')
def home():
    return jsonify({"message": "FoodAppeal API - Imagens que Vendem"})

@app.route('/process', methods=['POST'])
def process_image():
    """
    Processa uma imagem e um prompt para gerar uma nova imagem usando o Gemini.
    Espera:
    - Uma imagem em request.files['image']
    - Um prompt em request.form['prompt']
    Retorna:
    - JSON com erro se falhar
    - Stream de dados da imagem gerada se sucesso
    """
    try:
        # 1. Receber dados da requisição
        if 'image' not in request.files:
            return jsonify({"error": "Nenhuma imagem enviada"}), 400

        image_file = request.files['image']
        # Provide a clearer prompt hinting at image output
        prompt_text = request.form.get('prompt', 'Por favor, processe esta imagem e gere uma versão aprimorada, tornando-a mais saborosa e visualmente atraente. Retorne diretamente a imagem gerada.')

        # 2. Converter imagem para base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = image_file.content_type or "image/jpeg" # Assume JPEG if not specified

        # 3. Montar payload para o Gemini
        # Crucially, we remove the 'generationConfig' with 'responseModalities'
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            # Imagem de entrada
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        },
                        {
                            # Prompt de texto - MAIS EXPLÍCITO e sem mencionar texto na resposta
                            "text": prompt_text
                        }
                    ]
                }
            ]
            # REMOVED generationConfig for responseModalities
        }

        # 4. Enviar requisição para a API do Gemini
        headers = {'Content-Type': 'application/json'}
        # Add a timeout for robustness
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers=headers,
            timeout=90 # Increased timeout for image generation
        )

        # 5. Tratar resposta
        if response.status_code != 200:
            error_msg = f"Erro na API do Gemini: {response.status_code}"
            try:
                error_details = response.json()
                error_msg += f" - Detalhes: {error_details}"
            except:
                 # If response isn't JSON, get part of the text
                error_msg += f" - Detalhes: {response.text[:500]}..."
            print(f"[ERRO] Gemini API: {error_msg}") # Log server-side
            return jsonify({"error": error_msg}), response.status_code

        result = response.json()

        # 6. Extrair dados da imagem gerada
        candidates = result.get("candidates", [])
        if not candidates:
             return jsonify({"error": "Nenhuma candidata retornada pela API do Gemini"}), 500

        # Iterate through candidates and parts to find the generated image data
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                # Check if the part contains inline_data (the generated image)
                if "inline_data" in part:
                    inline_data = part["inline_data"]
                    generated_image_data_base64 = inline_data.get("data")
                    generated_image_mime_type = inline_data.get("mime_type", "image/png") # Default if not provided

                    if generated_image_data_base64:
                        # 7. Decodificar a imagem gerada
                        try:
                            generated_image_bytes = base64.b64decode(generated_image_data_base64)
                        except Exception as e:
                            print(f"[ERRO] Decodificando imagem gerada: {e}")
                            return jsonify({"error": "Erro ao processar a imagem gerada"}), 500

                        # 8. Retornar a imagem como resposta HTTP
                        return Response(
                            generated_image_bytes,
                            mimetype=generated_image_mime_type,
                            headers={"Content-Disposition": "inline; filename=imagem_editada.png"}
                        )

        # Se chegou aqui, não encontrou imagem gerada na resposta
        # Check for text response (though less likely with image generation model)
        texto_resposta = ""
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                if "text" in part:
                    texto_resposta += part["text"] + " "

        if texto_resposta.strip():
             print(f"[INFO] Resposta de texto recebida (sem imagem): {texto_resposta}")
             return jsonify({
                 "status": "success",
                 "message": "Processamento concluído, mas nenhuma imagem foi gerada.",
                 "texto": texto_resposta.strip()
             })
        else:
            return jsonify({"error": "Falha ao extrair a imagem gerada da resposta da API"}), 500


    except requests.exceptions.Timeout:
        return jsonify({"error": "Tempo limite excedido ao chamar API do Gemini"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"[ERRO] Interno: {str(e)}") # Log detailed error server-side
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# ... (restante do app.py e if __name__ == '__main__': ...)
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))