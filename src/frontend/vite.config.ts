import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  // Build de produção exige VITE_API_URL: não há URL de backend fixa no código (#4).
  const env = loadEnv(mode, process.cwd(), '')
  if (command === 'build' && !env.VITE_API_URL?.trim()) {
    throw new Error(
      'VITE_API_URL não está definida. Defina a URL do backend com /api antes do build, ' +
        'por exemplo: VITE_API_URL=https://trim-api.onrender.com/api npm run build ' +
        '(veja src/frontend/.env.example).',
    )
  }

  return {
    plugins: [react()],
  }
})
