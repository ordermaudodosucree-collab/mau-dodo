import React, { useState } from 'react';
import Navigation from './Navigation';
import Kanban from './Kanban';
import Dashboard from './Dashboard';
import Stocks from './Stocks';
import Historique from './Historique';
import { Toaster } from 'react-hot-toast';
import MatieresPremières from './MatieresPremières';
import './App.css';

function App() {
  const [page, setPage] = useState('kanban');

  return (
    <div className="App">
      <Toaster position="top-right" />
      <Navigation page={page} setPage={setPage} />
      {page === 'kanban'     && <Kanban />}
      {page === 'dashboard'  && <Dashboard />}
      {page === 'stocks'     && <Stocks />}
      {page === 'historique' && <Historique />}
      {page === 'matieres' && <MatieresPremières />}
    </div>
  );
}

export default App;