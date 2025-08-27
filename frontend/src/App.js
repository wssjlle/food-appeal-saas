// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

function App() {
  const [image, setImage] = useState(null);
  const [prompt, setPrompt] = useState('Deixe essa imagem mais saborosa.'); // Default prompt
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(''); // State for download URL

  // ... (dentro de App.js, na função handleSubmit)

const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);
  setError('');
  setResult(null); // Limpa resultado anterior

  const formData = new FormData();
  formData.append('image', image);
  formData.append('prompt', prompt);

  try {
    // IMPORTANTE: Mantenha responseType como 'blob' para lidar com imagens E texto.
    const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:5000'}/process`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      // Tentar ler o erro como JSON
      let errorMsg = `Erro ${res.status}`;
      try {
        const errorData = await res.json();
        errorMsg = errorData.error || errorMsg;
      } catch (e) {
        // Se não for JSON, ler como texto
        errorMsg = await res.text();
      }
      throw new Error(errorMsg);
    }

    // Verificar o tipo de conteúdo da resposta
    const contentType = res.headers.get('content-type');

    if (contentType && contentType.indexOf('application/json') !== -1) {
        // Se for JSON (ex: mensagem de "nenhuma imagem gerada" ou erro)
        const data = await res.json();
        setResult(data); // Mostra a mensagem JSON
        console.log("Backend retornou JSON:", data); // Log para debug
    } else {
        // Se NÃO for JSON, assume que é um 'blob' (potencialmente uma imagem binária)
        const blob = await res.blob(); // <-- CORREÇÃO AQUI

        // Criar URL para o blob
        const imageUrl = URL.createObjectURL(blob);

        // === Opção 1: Forçar Download ===
        // const link = document.createElement('a');
        // link.href = imageUrl;
        // link.download = 'imagem_editada.png'; // Nome do arquivo
        // document.body.appendChild(link);
        // link.click();
        // document.body.removeChild(link);
        // URL.revokeObjectURL(imageUrl); // Limpar URL

        // === Opção 2: Mostrar no navegador (preferido) ===
        setResult({ imageUrl: imageUrl, isImage: true });
        // =============================================
    }

  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};

// ... (restante do App.js)

  return (
    <div className="App">
      <header className="App-header">
        <h1>🍽️ FoodAppeal</h1>
        <p>Crie imagens de alimentos irresistíveis para atrair mais clientes</p>
      </header>

      <main className="main-content">
        <form onSubmit={handleSubmit} className="upload-form">
          <div className="form-group">
            <label htmlFor="image">Imagem do prato/produto:</label>
            <input
              type="file"
              id="image"
              accept="image/*"
              onChange={(e) => setImage(e.target.files[0])}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="prompt">Prompt de edição:</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Descreva como deseja que a imagem seja editada..."
              rows={4}
            />
          </div>

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Processando...' : '✨ Transformar Imagem'}
          </button>
        </form>

        {error && (
          <div className="error-message">
            <p>❌ {error}</p>
            {/* Log error to console for debugging if needed */}
            {/* {console.error("Error state:", error)} */}
          </div>
        )}

         {/* Dentro do render do App.js, onde mostra o resultado */}
 {result && (
  <div className="result-section">
    <h2>Resultado</h2>
    <div className="result-content">
      {result.isImage ? (
        <div>
          <h3>Imagem Gerada:</h3>
          <img src={result.imageUrl} alt="Imagem Editada" style={{ maxWidth: '100%', height: 'auto' }} />
          {/* Opcional: Adicionar botão para download novamente */}
          <a href={result.imageUrl} download="imagem_editada.png">
            <button type="button">Baixar Imagem</button>
          </a>
        </div>
       ) : result.imageUrl ? ( // Caso tenha imageUrl de download forçado
         <p>{result.message}</p>
       ) : result.texto ? (
         <div className="result-text">
           <h3>Resposta do Modelo:</h3>
           <p>{result.texto}</p>
         </div>
       ) : (
         <div className="result-text">
           <h3>Mensagem:</h3>
           <pre>{JSON.stringify(result, null, 2)}</pre>
         </div>
       )}
    </div>
  </div>
 )}
      </main>

      <footer className="App-footer">
        <p>FoodAppeal - Imagens que Vendem 📸</p>
      </footer>
    </div>
  );
}

export default App;