import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';

const App = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Landing />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
