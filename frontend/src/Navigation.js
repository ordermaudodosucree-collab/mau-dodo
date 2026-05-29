import React from 'react';
import logo from './logo.png';
import './Navigation.css';

export default function Navigation({ page, setPage }) {
  return (
    <nav className="nav">
      <div className="nav-logo">
        <img src={logo} alt="Mau Dodo Sucrée" className="nav-logo-img" />
        <div className="nav-logo-text">
          <div className="nav-logo-name">Mau Dodo Sucrée</div>
          <div className="nav-logo-sub">Gestion des commandes</div>
        </div>
      </div>
      <div className="nav-links">
        <button
          className={`nav-btn ${page === 'kanban' ? 'active' : ''}`}
          onClick={() => setPage('kanban')}
        >
          📋 Commandes
        </button>
        <button
          className={`nav-btn ${page === 'dashboard' ? 'active' : ''}`}
          onClick={() => setPage('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-btn ${page === 'stocks' ? 'active' : ''}`}
          onClick={() => setPage('stocks')}
        >
          📦 Stocks
        </button>
        <button
          className={`nav-btn ${page === 'historique' ? 'active' : ''}`}
          onClick={() => setPage('historique')}
        >
          📜 Historique
        </button>
      </div>
    </nav>
  );
}
