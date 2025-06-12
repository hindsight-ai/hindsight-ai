import React, { useState, useEffect, useCallback } from 'react';
import agentService from '../api/agentService';
import PaginationControls from './PaginationControls';
import { CopyToClipboardButton } from './CopyToClipboardButton';
import { BulkActionBar } from './BulkActionBar';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import AddAgentDialog from './AddAgentDialog'; // Import the new dialog component
import './MemoryBlockList.css'; // Reusing existing styles

const AgentManagementPage = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total_pages: 1,
    total_items: 0,
  });
  const [sort, setSort] = useState({ field: 'created_at', order: 'desc' });
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [showAddAgentDialog, setShowAddAgentDialog] = useState(false); // State for dialog visibility
  const [confirmationMessage, setConfirmationMessage] = useState(null); // State for confirmation message

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let fetchedData;
      if (searchTerm) {
        fetchedData = await agentService.searchAgents(searchTerm);
        setPagination(prev => ({
          ...prev,
          total_pages: 1,
          total_items: fetchedData.length,
        }));
      } else {
        fetchedData = await agentService.getAgents({
          page: pagination.page,
          per_page: pagination.per_page,
          sort_by: sort.field,
          sort_order: sort.order,
        });
        setPagination(prev => ({
          ...prev,
          total_pages: fetchedData.total_pages,
          total_items: fetchedData.total_items,
        }));
      }
      const agentsArray = Array.isArray(fetchedData) ? fetchedData : (fetchedData.items || []);
      setAgents(agentsArray);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError('Failed to load agents. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.per_page, searchTerm, sort.field, sort.order]);

  useEffect(() => {
    setAgents([]);
    setLoading(true);
    fetchAgents();
  }, [fetchAgents]);

  const handleAddAgent = async (agentName) => {
    setError(null); // Clear previous errors
    setLoading(true);
    try {
      await agentService.createAgent({ agent_name: agentName });
      setConfirmationMessage(`Agent "${agentName}" created successfully!`);
      setShowAddAgentDialog(false); // Close dialog on success
      await fetchAgents(); // Refresh the list
      // Clear confirmation message after a few seconds
      setTimeout(() => setConfirmationMessage(null), 5000);
    } catch (err) {
      console.error('Failed to create agent:', err);
      setError(`Failed to create agent: ${err.response?.data?.detail || err.message}. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAgent = async (agentId) => {
    if (window.confirm('Are you sure you want to delete this agent and all its associated data (memory blocks, transcripts)? This action cannot be undone.')) {
      try {
        setLoading(true);
        await agentService.deleteAgent(agentId);
        await fetchAgents();
        setSelectedAgents(prevSelected => prevSelected.filter(id => id !== agentId));
      } catch (err) {
        console.error('Failed to delete agent:', err);
        setError('Failed to delete agent. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  const handlePerPageChange = (e) => {
    setPagination(prev => ({ ...prev, per_page: parseInt(e.target.value, 10), page: 1 }));
  };

  const handlePageInputChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 1) {
      setPagination(prev => ({ ...prev, page: value }));
    }
  };

  const handleSortChange = (field) => {
    setSort(prev => ({
      field,
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleSelectAgent = (agentId) => {
    setSelectedAgents(prevSelected =>
      prevSelected.includes(agentId)
        ? prevSelected.filter(id => id !== agentId)
        : [...prevSelected, agentId]
    );
  };

  const handleSelectAllAgents = () => {
    if (selectedAgents.length === agents.length && agents.length > 0) {
      setSelectedAgents([]);
    } else {
      setSelectedAgents(agents.map(agent => agent.agent_id));
    }
  };

  const handleBulkDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${selectedAgents.length} selected agents and all their associated data? This action cannot be undone.`)) {
      try {
        setLoading(true);
        await Promise.all(selectedAgents.map(agentId => agentService.deleteAgent(agentId)));
        setSelectedAgents([]);
        await fetchAgents();
      } catch (err) {
        console.error('Failed to bulk delete agents:', err);
        setError('Failed to bulk delete agents. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const columnDefinitions = [
    { id: 'select', label: 'Select', size: 3, isResizable: false, minSize: 3, maxSize: 3 },
    { id: 'id', label: 'ID', size: 8, isSortable: true },
    { id: 'created_at', label: 'Creation Date', size: 7, isSortable: true },
    { id: 'agent_name', label: 'Agent Name', size: 70, isSortable: true },
    { id: 'actions', label: 'Actions', size: 12, isResizable: false, minSize: 12, maxSize: 12 },
  ];

  const initialColumnLayout = columnDefinitions.map(col => col.size);
  const [columnLayout, setColumnLayout] = useState(initialColumnLayout);

  const renderHeader = () => (
    <PanelGroup direction="horizontal" className="memory-block-table-header" onLayout={setColumnLayout}>
      {columnDefinitions.map((col, index) => (
        <React.Fragment key={col.id}>
          <Panel
            id={col.id}
            defaultSize={col.size}
            minSize={col.minSize || 5}
            maxSize={col.maxSize || 100}
            className={`header-cell ${col.isSortable ? 'sortable-header' : ''}`}
            onClick={() => col.isSortable && handleSortChange(col.id)}
            onKeyDown={(e) => col.isSortable && (e.key === 'Enter' || e.key === ' ') && handleSortChange(col.id)}
            tabIndex={col.isSortable ? 0 : -1}
            role="columnheader"
            aria-sort={sort.field === col.id ? (sort.order === 'asc' ? 'ascending' : 'descending') : 'none'}
          >
            {col.id === 'select' ? (
              <input
                type="checkbox"
                onChange={handleSelectAllAgents}
                checked={selectedAgents.length === agents.length && agents.length > 0}
                aria-label="Select all agents"
              />
            ) : (
              <>
                {col.label}
                {sort.field === col.id && <span className="sort-arrow">{sort.order === 'asc' ? '▲' : '▼'}</span>}
              </>
            )}
          </Panel>
          {index < columnDefinitions.length - 1 && (
            <PanelResizeHandle className="resize-handle" />
          )}
        </React.Fragment>
      ))}
    </PanelGroup>
  );

  const renderRow = (agent) => (
    <div className="memory-block-table-row" key={agent.agent_id} role="row">
      {columnDefinitions.map((col, index) => (
        <React.Fragment key={col.id}>
          <div
            className="data-cell-wrapper"
            style={{ flexBasis: `${columnLayout[index]}%` }}
            role="cell"
          >
            <div className={`data-cell ${col.id}-cell`}>
              {renderCellContent(agent, col.id)}
            </div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );

  const renderCellContent = (agent, columnId) => {
    if (!agent) return null;

    switch (columnId) {
      case 'select':
        return (
          <input
            type="checkbox"
            checked={selectedAgents.includes(agent.agent_id)}
            onChange={() => handleSelectAgent(agent.agent_id)}
          />
        );
      case 'id':
        return <CopyToClipboardButton textToCopy={agent.agent_id} displayId={agent.agent_id ? String(agent.agent_id).substring(0, 8) : ''} />;
      case 'agent_name':
        return agent.agent_name;
      case 'created_at':
        return agent.created_at ? new Date(agent.created_at).toLocaleString() : '';
      case 'actions':
        return (
          <div className="actions-cell">
            <button
              onClick={() => handleDeleteAgent(agent.agent_id)}
              className="action-icon-button remove-button"
              title="Delete Agent"
            >
              🗑️
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  if (loading) return <div className="loading-message">Loading agents...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="agent-management-page">
      <h1>Agent Management</h1>

      <div className="search-bar-container">
        <input
          type="text"
          placeholder="Search agents by name..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="search-input-large"
        />
        <button onClick={fetchAgents} className="filter-toggle-button">Search</button>
      </div>

      {/* Removed the direct input field for new agent name */}
      <div className="add-agent-section">
        <button onClick={() => setShowAddAgentDialog(true)} className="filter-toggle-button">Add Agent</button>
      </div>

      {selectedAgents.length > 0 && (
        <BulkActionBar selectedCount={selectedAgents.length} onBulkRemove={handleBulkDelete} />
      )}

      {confirmationMessage && (
        <div className="confirmation-message">
          {confirmationMessage}
        </div>
      )}

      {agents.length === 0 && !loading && !error && !searchTerm ? ( // Adjusted condition for empty state
        <div className="empty-state-message">
          <p>No agents found. Click "Add Agent" to create your first agent!</p>
          <button onClick={() => setShowAddAgentDialog(true)}>Add First Agent</button>
        </div>
      ) : (
        <>
          <div className="memory-block-table-container">
            {renderHeader()}
            <div className="memory-block-table-body">
              {agents.map(renderRow)}
            </div>
          </div>
          {!searchTerm && (
            <PaginationControls
              pagination={pagination}
              onPageChange={handlePageChange}
              onPerPageChange={handlePerPageChange}
              onPageInputChange={handlePageInputChange}
              fetchMemoryBlocks={fetchAgents}
            />
          )}
        </>
      )}

      <AddAgentDialog
        show={showAddAgentDialog}
        onClose={() => setShowAddAgentDialog(false)}
        onCreate={handleAddAgent}
        loading={loading}
        error={error}
      />
    </div>
  );
};

export default AgentManagementPage;
