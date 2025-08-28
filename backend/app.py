# -*- coding: utf-8 -*-
# ... (imports e setup anteriores permanecem os mesmos) ...
import io # Importar io para manipular buffers binários
from flask import Flask, request, jsonify, send_file, Response # Importar send_file e Response para retornar arquivos e streams
from flask_cors import CORS
import json
import base64
import requests
import os
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Use o modelo correto
MODEL_ID = "gemini-2.0-flash-preview-image-generation"
# Construa a URL correta para streamGenerateContent
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:streamGenerateContent?key={GEMINI_API_KEY}"

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
        prompt_text = request.form.get('prompt', 'Por favor, processe esta imagem e gere uma versão aprimorada, tornando-a mais saborosa e visualmente atraente. Retorne diretamente a imagem gerada.')

        # 2. Converter imagem para base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = image_file.content_type or "image/jpeg" # Assume JPEG se não especificado

        # 3. Montar payload para o Gemini streamGenerateContent
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
                            # Prompt de texto
                            "text": prompt_text
                        }
                    ]
                }
            ],
            # Configuração para pedir resposta em imagem e texto (opcional)
            "generation_config": {
                "response_modalities": ["IMAGE", "TEXT"] # Pedir especificamente imagem e texto
            }
        }

        # 4. Enviar requisição para a API do Gemini (usando streamGenerateContent)
        headers = {'Content-Type': 'application/json'}

        # Usar requests.post com stream=True para receber o conteúdo em partes
        response = requests.post(
            GEMINI_STREAM_URL,
            json=payload,
            headers=headers,
            timeout=90, # Timeout maior para geração de imagem
            stream=True # MUITO IMPORTANTE para stream
        )

        # 5. Tratar resposta (STREAM)
        if response.status_code != 200:
            error_msg = f"Erro na API do Gemini: {response.status_code}"
            try:
                error_details = response.json()
                error_msg += f" - Detalhes: {error_details}"
            except:
                 # Se resposta não for JSON, pegar parte do texto
                error_msg += f" - Detalhes: {response.text[:500]}..." # Primeiros 500 chars
            print(f"[ERRO] Gemini API (Stream): {error_msg}") # Log server-side
            return jsonify({"error": error_msg}), response.status_code

        # 6. Processar o stream
        # A resposta é um stream de eventos Server-Sent Events (SSE) ou NDJSON.
        # Cada 'chunk' é uma linha JSON.
        image_data_b64 = None
        accumulated_text = ""

        # Iterar sobre as linhas da resposta (chunks)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                try:
                    # Parsear cada linha como JSON
                    chunk_data = json.loads(decoded_line)
                    
                    # Verificar se há candidatos
                    candidates = chunk_data.get("candidates", [])
                    for candidate in candidates:
                        content = candidate.get("content", {})
                        parts = content.get("parts", [])
                        for part in parts:
                            # Procurar por dados de imagem inline_data
                            if "inline_data" in part:
                                inline_data = part["inline_data"]
                                image_data_b64 = inline_data.get("data")
                                mime_type = inline_data.get("mime_type", "image/png")
                                print("[INFO] Imagem encontrada no stream.")
                                break # Sai dos loops internos se achar a imagem
                        if image_data_b64:
                            break
                    if image_data_b64:
                        break
                    
                    # Acumular texto, se houver (fallback)
                    if not image_data_b64:
                         for candidate in candidates:
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    accumulated_text += part["text"]

                except json.JSONDecodeError as e:
                    print(f"[ERRO] Erro ao decodificar chunk JSON: {e}")
                    print(f"[DEBUG] Linha problemática: {decoded_line}")
                    continue # Ignorar linhas que não são JSON válidos

        # 7. Verificar se a imagem foi encontrada
        if image_data_b64:
            try:
                # Decodificar os dados base64 da imagem
                image_bytes = base64.b64decode(image_data_b64)
                
                # Criar um buffer de BytesIO
                image_buffer = io.BytesIO(image_bytes)
                image_buffer.seek(0) # Voltar ao início do buffer

                # Determinar extensão para filename sugerido
                file_extension = ".png"
                if mime_type == "image/jpeg":
                    file_extension = ".jpg"
                elif mime_type == "image/gif":
                    file_extension = ".gif"
                # Adicione mais conforme necessário

                # Retornar a imagem como resposta HTTP usando send_file
                # ou Response para maior controle
                return Response(
                    image_buffer.getvalue(),
                    mimetype=mime_type,
                    headers={
                        "Content-Disposition": f"inline; filename=imagem_editada{file_extension}",
                        # Cache-control opcional
                        # "Cache-Control": "no-cache, no-store, must-revalidate",
                        # "Pragma": "no-cache",
                        # "Expires": "0"
                    }
                )
            except Exception as e:
                print(f"[ERRO] Erro ao decodificar ou enviar a imagem: {e}")
                return jsonify({"error": "Erro ao processar a imagem gerada"}), 500
        else:
            # Se não encontrou imagem, mas tem texto acumulado
            if accumulated_text.strip():
                print(f"[INFO] Resposta de texto recebida (sem imagem): {accumulated_text}")
                return jsonify({
                    "status": "success",
                    "message": "Processamento concluído, mas nenhuma imagem foi gerada conforme solicitado.",
                    "texto": accumulated_text.strip()
                })
            else:
                # Nenhum dado de imagem ou texto significativo encontrado
                print("[ERRO] Nenhum dado de imagem ou texto útil encontrado no stream.")
                return jsonify({"error": "Falha ao extrair a imagem ou texto gerado da resposta da API Stream"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"error": "Tempo limite excedido ao chamar API do Gemini"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"[ERRO] Interno: {str(e)}") # Log detalhado do erro
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# ... (restante do app.py e if __name__ == '__main__': ...)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))