import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Booking from './pages/Booking';
import Dashboard from './pages/Dashboard';

const App = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/agenda" element={<Booking />} />
            <Route path="/admin" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
