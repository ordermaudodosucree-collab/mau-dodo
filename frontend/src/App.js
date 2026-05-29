import React from 'react';
import Kanban from './Kanban';
import { Toaster } from 'react-hot-toast';
import './App.css';

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" />
      <Kanban />
    </div>
  );
}

export default App;