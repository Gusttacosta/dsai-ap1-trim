import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    try {
      if (isRegister) {
        await api.post('/auth/register', { email, password, full_name: name });
        setIsRegister(false);
        setError('Conta criada! Faça o login.');
      } else {
        const response = await api.post('/auth/login', { email, password });
        
        const role = response.data.user?.role;
        if (role === 'admin' || role === 'barber') {
          setError('Sua conta é de profissional. Use a página de acesso profissional.');
          return;
        }

        localStorage.setItem('token', response.data.access_token);
        navigate('/');
      }
    } catch (err: any) {
      if (err.response?.status === 422) {
        // Pydantic returns an array of validation errors in 'detail'
        const details = err.response.data.detail;
        if (Array.isArray(details)) {
          setError(details.map((d: any) => d.msg).join(' | '));
        } else {
          setError('Erro de preenchimento. Verifique os dados (A senha exige mínimo 8 chars, 1 número e 1 letra).');
        }
      } else {
        setError(err.response?.data?.detail || 'Erro na autenticação');
      }
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '4rem auto', padding: '2rem', background: '#1c1c1e', borderRadius: '12px' }}>
      <h2>{isRegister ? 'Criar Conta' : 'Acesso do Cliente'}</h2>
      {error && <p style={{ color: 'var(--color-primary)', marginBottom: '1rem' }}>{error}</p>}
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {isRegister && (
          <input 
            type="text" 
            placeholder="Seu Nome" 
            value={name} 
            onChange={e => setName(e.target.value)} 
            style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: '#2c2c2e', color: '#fff' }}
          />
        )}
        <input 
          type="email" 
          placeholder="E-mail" 
          value={email} 
          onChange={e => setEmail(e.target.value)} 
          required
          style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: '#2c2c2e', color: '#fff' }}
        />
        <input 
          type="password" 
          placeholder="Senha" 
          value={password} 
          onChange={e => setPassword(e.target.value)} 
          required
          style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: '#2c2c2e', color: '#fff' }}
        />
        <button type="submit" style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: 'var(--color-primary)', color: '#000', fontWeight: 'bold', cursor: 'pointer' }}>
          {isRegister ? 'Cadastrar' : 'Entrar'}
        </button>
      </form>
      
      <p style={{ marginTop: '1rem', textAlign: 'center', cursor: 'pointer', color: '#8e8e93' }} onClick={() => setIsRegister(!isRegister)}>
        {isRegister ? 'Já tenho conta. Fazer login.' : 'Não tem conta? Cadastre-se'}
      </p>
    </div>
  );
};

export default Login;

