# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response # Importar Response para streaming
from flask_cors import CORS
import base64
import requests
import os
import json
from dotenv import load_dotenv
import io # Importar io para manipular buffers binários
from flask import send_file # Importar send_file para retornar arquivos

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
        # Importante: Usar streamGenerateContent para geração de imagem
        contents = [
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
                        "text": prompt_text #f"{prompt_text}" # Mantém o prompt claro
                    }
                ]
            }
        ]

        # Configuração para pedir resposta em imagem e texto (opcional, modelo pode inferir)
        generation_config = {
            "response_modalities": ["IMAGE", "TEXT"] # Pedir especificamente imagem (e talvez texto)
        }


        # 4. Enviar requisição para a API do Gemini (usando streamGenerateContent)
        # Usar requests.Session para lidar com streams de forma mais robusta
        session = requests.Session()
        # Montar a URL correta para streamGenerateContent
        GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:streamGenerateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": contents,
            "generation_config": generation_config
        }

        headers = {'Content-Type': 'application/json'}
        # Usar stream=True para receber o conteúdo em partes
        response = session.post(
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
        # Precisamos coletar os chunks e identificar a parte com a imagem.
        # Este exemplo tenta encontrar o primeiro chunk com dados de imagem inline_data.
        # Se a API enviar múltiplos chunks, isso pode precisar ser ajustado.
        # Uma abordagem mais robusta envolveria um parser SSE (Server-Sent Events),
        # mas para simplificação inicial, vamos tentar ler o JSON diretamente.
        # NOTA: streamGenerateContent pode retornar NDJSON (Newline Delimited JSON) ou JSON regular.
        # Vamos tentar ler como JSON primeiro.

        try:
            full_response_json = response.json()
            # A resposta pode ser uma lista de candidatos ou um único objeto.
            # A lógica abaixo tenta extrair os dados da imagem.
            # print(f"DEBUG: Resposta completa da API Gemini Stream (JSON): {full_response_json}")

            # Verificar se a resposta é uma lista (NDJSON convertido) ou um dicionário
            candidates_list = []
            if isinstance(full_response_json, list):
                 # Pode ser NDJSON onde cada item é um chunk. Iterar.
                 for item in full_response_json:
                     if isinstance(item, dict) and "candidates" in item:
                         candidates_list.extend(item["candidates"])
            elif isinstance(full_response_json, dict) and "candidates" in full_response_json:
                 # Resposta única
                 candidates_list = full_response_json["candidates"]

            if not candidates_list:
                 return jsonify({"error": "Nenhuma candidata retornada pela API do Gemini Stream"}), 500

            # Iterar pelos candidates procurando por inline_data (imagem)
            for candidate in candidates_list:
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "inline_data" in part:
                        inline_data = part["inline_data"]
                        image_data_base64 = inline_data.get("data")
                        image_mime_type = inline_data.get("mime_type", "image/png") # Default

                        if image_data_base64:
                             # 7. Decodificar a imagem gerada
                            try:
                                image_bytes = base64.b64decode(image_data_base64)
                                # 8. Retornar a imagem como resposta HTTP usando send_file
                                # Criar um buffer de BytesIO
                                image_buffer = io.BytesIO(image_bytes)
                                image_buffer.seek(0) # Voltar ao início do buffer

                                # Determinar extensão para filename sugerido
                                file_extension = ".png"
                                if image_mime_type == "image/jpeg":
                                    file_extension = ".jpg"

                                return send_file(
                                    image_buffer,
                                    mimetype=image_mime_type,
                                    as_attachment=False, # Exibir no navegador
                                    download_name=f"imagem_editada{file_extension}" # Nome sugerido
                                )
                            except Exception as e:
                                print(f"[ERRO] Decodificando imagem gerada: {e}")
                                return jsonify({"error": "Erro ao processar a imagem gerada"}), 500

            # Se chegou aqui, não encontrou imagem gerada na resposta imediata
            # Verificar se há texto explicativo (embora tenhamos pedido imagem)
            texto_resposta = ""
            for candidate in candidates_list:
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        texto_resposta += part["text"] + " "

            if texto_resposta.strip():
                 print(f"[INFO] Resposta de texto recebida (sem imagem): {texto_resposta}")
                 # Retorna JSON se só tiver texto
                 return jsonify({
                     "status": "success",
                     "message": "Processamento concluído, mas nenhuma imagem foi gerada conforme solicitado.",
                     "texto": texto_resposta.strip()
                 })
            else:
                return jsonify({"error": "Falha ao extrair a imagem gerada da resposta da API Stream"}), 500


        except ValueError as ve:
            # Se não conseguiu decodificar como JSON, pode ser NDJSON ou outro formato.
            # Lidar com NDJSON manualmente pode ser complexo aqui.
            # Uma alternativa é retornar um erro genérico ou tentar outro método.
            print(f"[ERRO] Erro ao decodificar resposta JSON da API Stream: {ve}")
            # Tentar ler os primeiros bytes como texto para depuração
            response_text_sample = response.text[:1000] # Pegar amostra
            print(f"[DEBUG] Amostra da resposta da API Stream (Texto): {response_text_sample}")
            return jsonify({"error": "Erro ao processar a resposta da API do Gemini (Formato inesperado). Verifique os logs do servidor.", "details": response_text_sample[:200]}), 500
        except Exception as e:
            print(f"[ERRO] Erro interno ao processar stream: {str(e)}")
            return jsonify({"error": f"Erro interno ao processar a resposta da API: {str(e)}"}), 500


    except requests.exceptions.Timeout:
        return jsonify({"error": "Tempo limite excedido ao chamar API do Gemini"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"[ERRO] Interno: {str(e)}") # Log detalhado do erro
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# ... (restante do app.py e if __name__ == '__main__': ...)

# ... (restante do app.py e if __name__ == '__main__': ...)
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))