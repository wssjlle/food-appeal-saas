# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response # Importar Response para streaming
from flask_cors import CORS
import base64
import requests
import os
import json
from dotenv import load_dotenv
import io

# -*- coding: utf-8 -*-
# ... (imports: Flask, request, jsonify, Response, CORS, base64, requests, os, load_dotenv - remain the same) ...

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

# -*- coding: utf-8 -*-
# ... (imports e setup anteriores permanecem os mesmos) ...
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
        prompt_text = request.form.get('prompt', 'Deixe essa imagem mais saborosa.')

        # 2. Converter imagem para base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = image_file.content_type or "image/jpeg" # Assume JPEG se não especificado

        # 3. Montar payload para o Gemini (formato específico do modelo de geração de imagem)
        payload = {
            "contents": [
                {
                    "role": "user", # Papel do conteúdo
                    "parts": [
                        {
                            # Imagem de entrada
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        },
                        {
                            # Prompt de texto - MAIS EXPLÍCITO
                            "text": f"Por favor, processe esta imagem e gere uma versão aprimorada. {prompt_text} Certifique-se de retornar a imagem diretamente."
                        }
                    ]
                }
            ],
            # Solicitar explicitamente que a resposta seja uma imagem e texto.
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"] # CHANGED HERE - Exige ambas
            }
        }

        # 4. Enviar requisição para a API do Gemini
        # Usar headers para garantir JSON
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers=headers,
            timeout=90 # Timeout maior para geração de imagem
        )

        # 5. Tratar resposta
        if response.status_code != 200:
            error_msg = f"Erro na API do Gemini: {response.status_code}"
            try:
                error_details = response.json()
                error_msg += f" - Detalhes: {error_details}"
            except:
                error_msg += f" - Detalhes: {response.text[:500]}" # Primeiros 500 chars
            print(f"Erro Gemini: {error_msg}") # Log para debug
            return jsonify({"error": error_msg}), response.status_code

        result = response.json()

        # 6. Extrair dados da imagem gerada - ITERAÇÃO CORRIGIDA
        # O modelo retorna um Candidate, que tem Content, que tem Parts
        # Precisamos iterar por todos os parts para encontrar o inline_data (a imagem gerada)
        candidates = result.get("candidates", [])
        if not candidates:
             return jsonify({"error": "Nenhuma candidata retornada pela API do Gemini"}), 500

        # Iterar pelos candidates e parts para encontrar a imagem gerada
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                # Verificar se a part contém inline_data (a imagem gerada)
                if "inline_data" in part:
                    inline_data = part["inline_data"]
                    generated_image_data_base64 = inline_data.get("data")
                    generated_image_mime_type = inline_data.get("mime_type", "image/png") # Default se não vier

                    if generated_image_data_base64:
                        # 7. Decodificar a imagem gerada
                        try:
                            generated_image_bytes = base64.b64decode(generated_image_data_base64)
                        except Exception as e:
                            print(f"Erro ao decodificar imagem gerada: {e}")
                            return jsonify({"error": "Erro ao processar a imagem gerada"}), 500

                        # 8. Retornar a imagem como resposta HTTP
                        # Usar flask.send_file seria ideal, mas vamos retornar os bytes diretamente com o tipo correto
                        return Response(
                            generated_image_bytes,
                            mimetype=generated_image_mime_type,
                            headers={"Content-Disposition": "inline; filename=imagem_editada.png"} # Nome sugerido
                        )

        # Se chegou aqui, não encontrou imagem gerada na resposta imediata
        # Verificar se há texto explicativo (pode vir antes da imagem em respostas futuras ou em caso de erro)
        texto_resposta = ""
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                if "text" in part:
                    texto_resposta += part["text"] + " "

        if texto_resposta.strip():
             print(f"Resposta de texto recebida (sem imagem imediata): {texto_resposta}")
             return jsonify({
                 "status": "success",
                 "message": "Processamento concluído. Verifique se a imagem foi gerada conforme solicitado.",
                 "texto_descritivo": texto_resposta.strip() # Retorna o texto para contexto
             })
        else:
            return jsonify({"error": "Falha ao extrair a imagem gerada da resposta da API"}), 500


    except requests.exceptions.Timeout:
        return jsonify({"error": "Tempo limite excedido ao chamar API do Gemini"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"Erro interno: {str(e)}") # Log detalhado do erro
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# ... (restante do app.py e if __name__ == '__main__': ...)

# ... (restante do app.py e if __name__ == '__main__': ...)


# ... (restante do app.py e if __name__ == '__main__': ...)
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))