import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Landing from './pages/Landing';
import Booking from './pages/Booking';
import Dashboard from './pages/Dashboard';
import Gallery from './pages/Gallery';
import TrimClub from './pages/TrimClub';

// Navbar Simples
const Navbar = () => (
  <nav style={{ padding: '1rem 2rem', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '2rem', alignItems: 'center' }}>
    <Link to="/" style={{ fontWeight: 800, fontSize: '1.5rem' }}>Trim</Link>
    <Link to="/galeria" style={{ color: 'var(--color-text-secondary)' }}>Galeria</Link>
    <Link to="/club" style={{ color: 'var(--color-text-secondary)' }}>Trim Club</Link>
  </nav>
);

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
                  <Route path="/agenda" element={<Booking />} />
                  <Route path="/galeria" element={<Gallery />} />
                  <Route path="/club" element={<TrimClub />} />
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
