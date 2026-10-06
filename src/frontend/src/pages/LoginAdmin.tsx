import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const LoginAdmin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    try {
      const response = await api.post('/auth/login', { email, password });
      
      const role = response.data.user?.role;
      if (role === 'admin' || role === 'barber') {
        localStorage.setItem('token', response.data.access_token);
        navigate('/admin');
      } else {
        setError('Acesso negado. Apenas administradores e barbeiros podem acessar este painel.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro na autenticação');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '4rem auto', padding: '2rem', background: '#1c1c1e', borderRadius: '12px' }}>
      <h2 style={{ color: 'var(--color-primary)' }}>Acesso Profissional</h2>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>Painel exclusivo para barbeiros e administração.</p>
      
      {error && <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</p>}
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <input 
          type="email" 
          placeholder="E-mail" 
          value={email} 
          onChange={e => setEmail(e.target.value)} 
          required
          style={{ padding: '0.8rem', borderRadius: '8px', border: '1px solid var(--color-border)', background: '#2c2c2e', color: '#fff' }}
        />
        <input 
          type="password" 
          placeholder="Senha" 
          value={password} 
          onChange={e => setPassword(e.target.value)} 
          required
          style={{ padding: '0.8rem', borderRadius: '8px', border: '1px solid var(--color-border)', background: '#2c2c2e', color: '#fff' }}
        />
        <button type="submit" style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: 'var(--color-primary)', color: '#000', fontWeight: 'bold', cursor: 'pointer', marginTop: '0.5rem' }}>
          Acessar Painel
        </button>
      </form>
    </div>
  );
};

export default LoginAdmin;
