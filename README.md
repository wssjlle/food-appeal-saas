# 🍽️ FoodAppeal - SaaS de Edição de Imagens para Negócios Alimentícios

**Crie imagens de alimentos irresistíveis para atrair mais clientes, sem gastar com designer.**

## 🎯 Sobre o Projeto

FoodAppeal é um SaaS que ajuda padarias, restaurantes, pizzarias e outros negócios do ramo alimentício a criar imagens profissionais de seus produtos para redes sociais e plataformas de delivery.

## 🚀 Tecnologias Utilizadas

- **Frontend**: React.js
- **Backend**: Python Flask
- **IA**: Google Gemini API
- **Deploy**: Grátis no Railway/Vercel

## 📋 Pré-requisitos

1. Conta no Google AI Studio (para API Key do Gemini)
2. Contas no Railway e Vercel (para deploy gratuito)

## 🛠️ Como Rodar Localmente

### Backend

```bash
cd backend
pip install -r requirements.txt
# Crie um arquivo .env com sua GEMINI_API_KEY
flask run


Frontend

cd frontend
npm install
npm start

☁️ Deploy Gratuito

Backend no Railway
Faça fork deste repositório
Conecte ao Railway
Adicione a variável de ambiente GEMINI_API_KEY
Frontend no Vercel
Importe o diretório frontend
Configure a variável REACT_APP_API_URL com a URL do seu backend
🤝 Contribuindo
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests.