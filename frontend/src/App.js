import React, { useState } from 'react';
import './App.css';

function App() {
  const [image, setImage] = useState(null);
  const [prompt, setPrompt] = useState('Edite esta imagem para deixar mais apetitosa e profissional para redes sociais.');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    if (!image) {
      setError('Por favor, selecione uma imagem');
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('image', image);
    formData.append('prompt', prompt);

    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:5000'}/process`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Erro ao processar imagem');
      }

      setResult(data);
    } catch (err) {
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
          </div>
        )}

        {result && (
          <div className="result-section">
            <h2>Resultado</h2>
            <div className="result-content">
              <div className="result-text">
                <h3>Sugestão de edição:</h3>
                <p>{result.descricao}</p>
              </div>
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