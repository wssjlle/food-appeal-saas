# -*- coding: utf-8 -*-
# Importações
import io
import os
import base64
import json
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import mimetypes

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar Flask app
app = Flask(__name__)
CORS(app)

# Obter a chave da API do Gemini das variáveis de ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não está definida nas variáveis de ambiente.")

# Modelo e URL da API
MODEL_ID = "gemini-2.0-flash-preview-image-generation"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:streamGenerateContent?key={GEMINI_API_KEY}"

@app.route('/')
def home():
    """Endpoint raiz para verificar se o serviço está online."""
    return jsonify({"message": "FoodAppeal API - Imagens que Vendem", "status": "online"})

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
        if not image_bytes:
             return jsonify({"error": "Imagem vazia ou inválida"}), 400
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

            print("[INFO] Iniciando processamento do stream SSE...")

        # 6. Processar o stream SSE corretamente
        # A resposta é um stream de eventos Server-Sent Events (SSE).
        # Cada evento tem um formato: " <conteúdo JSON>\n\n"
        # Precisamos iterar e acumular os dados até encontrar "\n\n"

        full_sse_event_data = ""
        image_data_buffers = [] # Lista para acumular partes da imagem se necessário
        accumulated_text = ""
        finished = False
        candidate_count = 0 # Contador para depuração

        # Iterar sobre as linhas da resposta (chunks)
        # response.iter_lines() é a maneira correta de lidar com SSE/NDJSON
        for line_index, line in enumerate(response.iter_lines()):
            if line:
                decoded_line = line.decode('utf-8')
                print(f"[DEBUG] Linha recebida #{line_index}: {decoded_line[:100]}...") # Log da linha bruta

                if decoded_line.startswith(""):
                    # Extrair o conteúdo JSON após ""
                    json_data_str = decoded_line[5:].strip() # Remove "data:" e espaços
                    print(f"[DEBUG] Conteúdo JSON extraído #{line_index}: {json_data_str[:100]}...")

                    try:
                        # Decodificar o conteúdo como JSON
                        chunk_data = json.loads(json_data_str)
                        print(f"[DEBUG] Chunk JSON #{line_index} decodificado com sucesso.")

                        # Verificar se há candidatos
                        candidates = chunk_data.get("candidates", [])
                        print(f"[DEBUG] Número de candidatos no chunk #{line_index}: {len(candidates)}")
                        for i, candidate in enumerate(candidates):
                            candidate_count += 1
                            print(f"[DEBUG] Processando candidato #{candidate_count} no chunk #{line_index}")
                            content = candidate.get("content", {})
                            role = content.get("role", "unknown")
                            parts = content.get("parts", [])
                            print(f"[DEBUG] Candidato #{candidate_count} - Role: {role}, Partes: {len(parts)}")

                            for j, part in enumerate(parts):
                                print(f"[DEBUG] Processando parte #{j+1} do candidato #{candidate_count}")
                                # Procurar por dados de imagem inline_data
                                if "inline_data" in part:
                                    inline_data = part["inline_data"]
                                    image_data_b64 = inline_data.get("data")
                                    mime_type = inline_data.get("mime_type", "image/png")
                                    print(f"[INFO] Imagem encontrada no candidato #{candidate_count}, parte #{j+1}. Mime-type: {mime_type}")
                                    if image_data_b64:
                                        image_data_buffers.append(image_data_b64)
                                        print(f"[INFO] Tamanho acumulado dos dados da imagem: {len(''.join(image_data_buffers))} caracteres base64")

                                # Acumular texto, se houver (fallback)
                                if "text" in part:
                                    text_chunk = part["text"]
                                    accumulated_text += text_chunk
                                    print(f"[INFO] Texto acumulado (últimos 50 chars): {accumulated_text[-50:] if accumulated_text else ''}")

                        # Verificar se terminou
                        # if "finishReason" in candidate: # Verificar finishReason em cada candidato pode não ser ideal
                        #     finish_reason = candidate["finishReason"]
                        #     print(f"[INFO] Motivo de término: {finish_reason}")
                        #     finished = True

                    except json.JSONDecodeError as e:
                        print(f"[ERRO] Erro ao decodificar conteúdo JSON do SSE na linha #{line_index}: {e}")
                        print(f"[DEBUG] Conteúdo problemático: {json_data_str[:100]}...")
                        continue # Ignorar linhas com erro de JSON

                # Verificar se o evento terminou (\n\n) - O iter_lines já lida com isso
                # O requests.iter_lines divide por \n, então cada 'line' é uma linha individual.
                # O SSE usa \n\n para delimitar eventos. O iter_lines entregará linhas vazias
                # entre eventos, mas como estamos checando 'if line:', pulamos linhas vazias.
                # Portanto, o loop continua normalmente para cada linha ''.

            else:
                # Linha vazia (\n) indica o fim de um evento SSE
                # Podemos usar isso se necessário, mas o iter_lines já separa corretamente.
                print(f"[DEBUG] Linha vazia encontrada na iteração #{line_index} (fim de evento SSE?)")
                pass


        print("[INFO] Processamento do stream SSE concluído.")
        print(f"[DEBUG] Total de candidatos processados: {candidate_count}")
        print(f"[DEBUG] Tamanho final de image_data_buffers: {len(image_data_buffers)}")
        print(f"[DEBUG] Tamanho final de accumulated_text: {len(accumulated_text)}")


        # 7. Verificar se a imagem foi encontrada OU texto foi acumulado
        if image_data_buffers:
            # Concatenar todas as partes da imagem (se houver mais de uma)
            full_image_data_b64 = "".join(image_data_buffers)
            print(f"[INFO] Tentando decodificar os dados da imagem combinada. Tamanho: {len(full_image_data_b64)} chars")
            try:
                # Decodificar os dados base64 da imagem COMPLETA
                image_bytes = base64.b64decode(full_image_data_b64)
                print(f"[INFO] Imagem decodificada com sucesso. Tamanho em bytes: {len(image_bytes)}")

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
                response_headers = {
                    "Content-Disposition": f"inline; filename=imagem_editada{file_extension}",
                    # Cache-control opcional
                    # "Cache-Control": "no-cache, no-store, must-revalidate",
                    # "Pragma": "no-cache",
                    # "Expires": "0"
                }
                print(f"[INFO] Enviando imagem como resposta. Headers: {response_headers}")
                return Response(
                    image_buffer.getvalue(),
                    mimetype=mime_type,
                    headers=response_headers
                )
            except Exception as e:
                print(f"[ERRO] Erro ao decodificar ou enviar a imagem: {e}")
                return jsonify({"error": "Erro ao processar a imagem gerada"}), 500
        elif accumulated_text.strip():
            print(f"[INFO] Resposta de texto recebida (sem imagem): {accumulated_text}")
            return jsonify({
                "status": "success",
                "message": "Processamento concluído, mas nenhuma imagem foi gerada conforme solicitado.",
                "texto": accumulated_text.strip()
            })
        else:
            # Nenhum dado de imagem ou texto significativo encontrado
            print("[ERRO] Nenhuma imagem ou texto útil encontrado no stream SSE.")
            # Adicione logs específicos sobre o que estava vazio
            print(f"[DEBUG] Estado final - image_data_buffers: {image_data_buffers}")
            print(f"[DEBUG] Estado final - accumulated_text: '{accumulated_text}'")
            return jsonify({"error": "Falha ao extrair a imagem ou texto gerado da resposta da API Stream"}), 500


    except requests.exceptions.Timeout:
        return jsonify({"error": "Tempo limite excedido ao chamar API do Gemini"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"[ERRO] Interno: {str(e)}") # Log detalhado do erro
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# Executar o aplicativo se este arquivo for executado diretamente
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
