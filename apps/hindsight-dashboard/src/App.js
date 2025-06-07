import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link, useLocation } from 'react-router-dom';
import MemoryBlockList from './components/MemoryBlockList';
import MemoryBlockDetail from './components/MemoryBlockDetail';
import KeywordManager from './components/KeywordManager';
import './App.css';

function AppContent() {
  const location = useLocation();

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1 className="app-title">AI Agent Memory Dashboard</h1>
          <Link to="/new-memory-block" className="add-button">
            + Add New Memory Block
          </Link>
        </div>
        <div className="header-bottom">
          <nav className="main-nav">
            <ul className="nav-tabs">
              <li className="nav-item">
                <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
                  Memory Blocks
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/keywords" className={`nav-link ${location.pathname === '/keywords' ? 'active' : ''}`}>
                  Keywords
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<MemoryBlockList />} />
          <Route path="/memory-blocks/:id" element={<MemoryBlockDetail />} />
          <Route path="/keywords" element={<KeywordManager />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
