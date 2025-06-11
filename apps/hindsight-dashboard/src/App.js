import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link, useLocation } from 'react-router-dom';
import MemoryBlockList from './components/MemoryBlockList';
import MemoryBlockDetail from './components/MemoryBlockDetail';
import KeywordManager from './components/KeywordManager';
import AgentManagementPage from './components/AgentManagementPage';
import ConsolidationSuggestions from './components/ConsolidationSuggestions';
import ConsolidationSuggestionDetail from './components/ConsolidationSuggestionDetail';
import ArchivedMemoryBlockList from './components/ArchivedMemoryBlockList'; // Import ArchivedMemoryBlockList
import './App.css';

function AppContent() {
  const location = useLocation();

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1 className="app-title">AI Agent Memory Dashboard</h1>
          {(location.pathname === '/' || location.pathname === '/memory-blocks') && (
            <Link to="/new-memory-block" className="add-button">
              + Add New Memory Block
            </Link>
          )}
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
              <li className="nav-item">
                <Link to="/agents" className={`nav-link ${location.pathname === '/agents' ? 'active' : ''}`}>
                  Agents
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/consolidation-suggestions" className={`nav-link ${location.pathname === '/consolidation-suggestions' ? 'active' : ''}`}>
                  Consolidation Suggestions
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/archived-memory-blocks" className={`nav-link ${location.pathname === '/archived-memory-blocks' ? 'active' : ''}`}>
                  Archived Memory Blocks
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<MemoryBlockList key={location.pathname} />} />
          <Route path="/memory-blocks" element={<MemoryBlockList key={location.pathname} />} /> {/* Added explicit route for /memory-blocks */}
          <Route path="/memory-blocks/:id" element={<MemoryBlockDetail />} />
          <Route path="/keywords" element={<KeywordManager />} />
          <Route path="/agents" element={<AgentManagementPage key={location.pathname} />} />
          <Route path="/consolidation-suggestions" element={<ConsolidationSuggestions key={location.pathname} />} />
          <Route path="/consolidation-suggestions/:id" element={<ConsolidationSuggestionDetail />} />
          <Route path="/archived-memory-blocks" element={<ArchivedMemoryBlockList key={location.pathname} />} /> {/* New route for archived blocks */}
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
