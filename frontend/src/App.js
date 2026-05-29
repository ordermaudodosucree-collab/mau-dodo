import React, { useState } from 'react';
import Navigation from './Navigation';
import Kanban from './Kanban';
import Dashboard from './Dashboard';
import Stocks from './Stocks';
import { Toaster } from 'react-hot-toast';
import './App.css';

function App() {
  const [page, setPage] = useState('kanban');

  return (
    <div className="App">
      <Toaster position="top-right" />
      <Navigation page={page} setPage={setPage} />
      {page === 'kanban'    && <Kanban />}
      {page === 'dashboard' && <Dashboard />}
      {page === 'stocks'    && <Stocks />}
    </div>
  );
}

export default App;
