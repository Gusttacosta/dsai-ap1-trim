import React from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import Landing from './pages/Landing';
import Booking from './pages/Booking';
import Dashboard from './pages/Dashboard';
import Gallery from './pages/Gallery';
import TrimClub from './pages/TrimClub';
import Fidelidade from './pages/Fidelidade';

import Login from './pages/Login';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = React.useState(!!localStorage.getItem('token'));

  React.useEffect(() => {
    setIsAuthenticated(!!localStorage.getItem('token'));
  }, [location]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    navigate('/login');
  };

  return (
    <nav style={{ padding: '1rem 2rem', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '2rem', alignItems: 'center' }}>
      <Link to="/" style={{ fontWeight: 800, fontSize: '1.5rem' }}>Trim</Link>
      <Link to="/galeria" style={{ color: 'var(--color-text-secondary)' }}>Galeria</Link>
      <Link to="/club" style={{ color: 'var(--color-text-secondary)' }}>Trim Club</Link>
      <Link to="/fidelidade" style={{ color: 'var(--color-text-secondary)' }}>Prêmios</Link>
      <div style={{ flex: 1 }} />
      {isAuthenticated ? (
        <button onClick={handleLogout} style={{ padding: '0.5rem 1rem', background: 'transparent', border: '1px solid var(--color-border)', color: '#fff', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Sair</button>
      ) : (
        <Link to="/login" style={{ padding: '0.5rem 1rem', background: 'var(--color-primary)', color: '#000', borderRadius: '8px', fontWeight: 'bold' }}>Entrar</Link>
      )}
    </nav>
  );
};

const App = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Routes>
          <Route path="/admin/*" element={<Dashboard />} />
          <Route path="*" element={
            <>
              <Navbar />
              <main className="main-content">
                <Routes>
                  <Route path="/" element={<Landing />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/agenda" element={<Booking />} />
                  <Route path="/galeria" element={<Gallery />} />
                  <Route path="/club" element={<TrimClub />} />
                  <Route path="/fidelidade" element={<Fidelidade />} />
                </Routes>
              </main>
            </>
          } />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;
