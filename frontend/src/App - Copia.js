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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    setDownloadUrl(''); // Clear previous download URL

    if (!image) {
      setError('Por favor, selecione uma imagem');
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('image', image);
    formData.append('prompt', prompt);

    try {
      // Important: Use 'blob' to receive binary image data
      const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:5000'}/process`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let errorMsg = `Erro ${res.status}`;
        try {
          const errorData = await res.json();
          errorMsg = errorData.error || errorMsg;
        } catch (e) {
          // If not JSON, read as text
          errorMsg = await res.text();
        }
        throw new Error(errorMsg);
      }

      // Check content type
      const contentType = res.headers.get('content-type');
      if (contentType && contentType.indexOf('application/json') !== -1) {
        // If backend returns JSON (e.g., error message or text response)
        const data = await res.json();
        setResult(data);
        console.log("Backend returned JSON:", data); // Log for debugging
      } else {
        // Assume it's the image blob
        const blob = await res.blob();

        // Create a download URL for the blob
        const imageUrl = URL.createObjectURL(blob);
        setDownloadUrl(imageUrl); // Set the URL for potential download

        // Display the image in the result section
        setResult({ imageUrl: imageUrl, isImage: true });

        // --- Optional: Force automatic download ---
        // const link = document.createElement('a');
        // link.href = imageUrl;
        // link.download = 'imagem_editada.png'; // Suggested filename
        // document.body.appendChild(link);
        // link.click();
        // document.body.removeChild(link);
        // URL.revokeObjectURL(imageUrl); // Clean up
        // ----------------------------

      }

    } catch (err) {
      console.error("Fetch error:", err); // Log detailed error
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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

        {result && (
          <div className="result-section">
            <h2>Resultado</h2>
            <div className="result-content">
              {result.isImage ? (
                <div>
                  <h3>Imagem Gerada:</h3>
                  {/* Display loading indicator if image is still loading */}
                  {loading ? (
                     <p>Carregando imagem...</p>
                   ) : (
                     <>
                       <img src={result.imageUrl} alt="Imagem Editada" style={{ maxWidth: '100%', height: 'auto' }} />
                       {/* Optional: Add a download button */}
                       <a href={downloadUrl} download="imagem_editada.png">
                         <button type="button">Baixar Imagem</button>
                       </a>
                     </>
                   )}
                </div>
              ) : result.imageUrl ? (
                // Case where imageUrl was set for download (if auto-download was used)
                <p>{result.message}</p>
              ) : result.texto ? (
                // If backend returns text (unlikely with new setup, but possible error response)
                <div className="result-text">
                  <h3>Resposta do Modelo:</h3>
                  <p>{result.texto}</p>
                </div>
              ) : (
                // General result display (e.g., JSON messages)
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