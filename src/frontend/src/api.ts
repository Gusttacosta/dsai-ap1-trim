import axios from 'axios';

// Em `npm run dev`, sem VITE_API_URL, usa o backend local. O build exige a
// variável (ver vite.config.ts), então produção nunca cai neste padrão.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
