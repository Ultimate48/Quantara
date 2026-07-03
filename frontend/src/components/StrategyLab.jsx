import React, { useState, useEffect } from 'react';
import TemplateGallery from './TemplateGallery';
import VisualBuilder from './VisualBuilder';
import NodeEditor from './NodeEditor';
import CodeEditor from './CodeEditor';

/**
 * StrategyLab — Main container for the Strategy Lab page.
 * Features a mode tab bar (Templates | Visual Builder | Node Editor | Code)
 * with a strategy list sidebar and shared save/delete logic.
 */

const MODES = [
  { id: 'templates', label: 'Templates',      icon: '📚' },
  { id: 'visual',    label: 'Visual Builder',  icon: '📐' },
  { id: 'nodes',     label: 'Node Editor',     icon: '🔗' },
  { id: 'code',      label: 'Code',            icon: '💻' },
];

export default function StrategyLab({
  strategies, fetchStrategies,
  indicatorsMeta, expandPreset,
  showToast,
}) {
  // Strategy selection
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [isEditingStrategy, setIsEditingStrategy] = useState(false);

  // Strategy form fields (shared across all modes)
  const [stratName, setStratName] = useState('');
  const [stratDesc, setStratDesc] = useState('');
  const [stratCols, setStratCols] = useState([]);
  const [stratSignal, setStratSignal] = useState('');

  // UI state
  const [activeMode, setActiveMode] = useState('templates');
  const [validationError, setValidationError] = useState('');
  const [isSubmittingStrategy, setIsSubmittingStrategy] = useState(false);
  const [forceDeleteTarget, setForceDeleteTarget] = useState(null);

  // Templates
  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  // Fetch templates on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      setLoadingTemplates(true);
      try {
        const res = await fetch('/api/strategies/templates');
        if (!res.ok) throw new Error('Failed to load templates.');
        const data = await res.json();
        setTemplates(data);
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        setLoadingTemplates(false);
      }
    };
    fetchTemplates();
  }, [showToast]);

  // Sync form fields when selectedStrategy changes
  useEffect(() => {
    if (selectedStrategy) {
      setStratName(selectedStrategy.name);
      setStratDesc(selectedStrategy.description || '');
      setStratCols(selectedStrategy.columns || []);
      setStratSignal(selectedStrategy.signal_rule || '');
      setValidationError('');
    }
  }, [selectedStrategy]);

  // ——— Template Usage ———
  const handleUseTemplate = (template) => {
    setSelectedStrategy(null);
    setIsEditingStrategy(false);
    setStratName('');
    setStratDesc(template.description || '');
    setStratCols([...template.columns]);
    setStratSignal(template.signal_rule);
    setValidationError('');
    setActiveMode('visual');
  };

  // ——— New Strategy ———
  const handleNewStrategy = () => {
    setSelectedStrategy(null);
    setIsEditingStrategy(false);
    setStratName('');
    setStratDesc('');
    setStratCols([]);
    setStratSignal('');
    setValidationError('');
  };

  // ——— Select Existing ———
  const handleSelectStrategy = (s) => {
    setSelectedStrategy(s);
    setIsEditingStrategy(true);
    // Switch to code mode when viewing existing strategy for easy editing
    if (activeMode === 'templates') setActiveMode('visual');
  };

  // ——— Save Strategy ———
  const handleSaveStrategy = async (e) => {
    e.preventDefault();
    if (!stratName.trim()) {
      showToast('Strategy Name is required.', 'error');
      return;
    }
    if (!stratSignal.trim()) {
      showToast('Signal Rule is required.', 'error');
      return;
    }

    setIsSubmittingStrategy(true);
    setValidationError('');

    const bodyData = {
      name: stratName.trim(),
      description: stratDesc.trim() || null,
      columns: stratCols.filter(c => c.name.trim() && c.formula.trim()),
      signal_rule: stratSignal.trim(),
    };

    try {
      let res;
      if (isEditingStrategy && selectedStrategy) {
        res = await fetch(`/api/strategies/${selectedStrategy.name}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            description: bodyData.description,
            columns: bodyData.columns,
            signal_rule: bodyData.signal_rule,
          }),
        });
      } else {
        res = await fetch('/api/strategies/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyData),
        });
      }

      const data = await res.json();

      if (!res.ok) {
        setValidationError(data.detail || 'Validation failed.');
        throw new Error(data.detail || 'Failed to save strategy.');
      }

      showToast(
        isEditingStrategy
          ? `Strategy '${stratName}' updated successfully.`
          : `Strategy '${stratName}' created successfully.`,
        'success'
      );

      await fetchStrategies();
      setIsEditingStrategy(false);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmittingStrategy(false);
    }
  };

  // ——— Delete Strategy ———
  const handleDeleteStrategy = async (force = false) => {
    if (!selectedStrategy) return;

    try {
      const res = await fetch(`/api/strategies/${selectedStrategy.name}?force=${force}`, {
        method: 'DELETE',
      });
      const data = await res.json();

      if (!res.ok) {
        if (data.detail && data.detail.includes('dependent')) {
          setForceDeleteTarget(selectedStrategy.name);
        } else {
          throw new Error(data.detail || 'Failed to delete strategy.');
        }
        return;
      }

      showToast(data.message || 'Strategy deleted.', 'success');
      setForceDeleteTarget(null);
      setSelectedStrategy(null);
      setIsEditingStrategy(false);
      handleNewStrategy();
      await fetchStrategies();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title">Strategy Lab</h1>
        <p className="page-subtitle">Build trading strategies using templates, visual tools, node graphs, or raw code.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '2rem' }}>
        {/* ——— Strategies Sidebar ——— */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 style={{ color: '#fff' }}>My Strategies</h3>
            <button
              onClick={handleNewStrategy}
              className="btn btn-primary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
            >
              + New
            </button>
          </div>

          {strategies.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)' }}>No strategies found. Create one now.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {strategies.map(s => (
                <div
                  key={s.name}
                  onClick={() => handleSelectStrategy(s)}
                  className={`nav-item ${selectedStrategy?.name === s.name ? 'active' : ''}`}
                  style={{ display: 'block', padding: '0.75rem 1rem', textDecoration: 'none' }}
                >
                  <div style={{ fontWeight: '600', color: selectedStrategy?.name === s.name ? 'var(--accent-cyan)' : '#fff' }}>
                    {s.name}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '0.25rem' }}>
                    {s.description || 'No description'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ——— Main Editor Area ——— */}
        <div className="card">
          <h3 style={{ marginBottom: '1rem', color: '#fff' }}>
            {isEditingStrategy ? `Edit Strategy: ${stratName}` : 'Create New Strategy'}
          </h3>

          {/* Mode Tab Bar */}
          <div className="strategy-mode-tabs">
            {MODES.map(mode => (
              <button
                key={mode.id}
                className={`mode-tab ${activeMode === mode.id ? 'active' : ''}`}
                onClick={() => setActiveMode(mode.id)}
              >
                <span className="mode-icon">{mode.icon}</span>
                {mode.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSaveStrategy}>
            {/* Name & Description (always visible) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Strategy Name</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. MyStrategy"
                  value={stratName}
                  onChange={(e) => setStratName(e.target.value)}
                  disabled={isEditingStrategy}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Description</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Explain the strategy's mechanics"
                  value={stratDesc}
                  onChange={(e) => setStratDesc(e.target.value)}
                />
              </div>
            </div>

            {/* ——— Active Mode Content ——— */}
            {activeMode === 'templates' && (
              <TemplateGallery
                templates={templates}
                onUseTemplate={handleUseTemplate}
                showToast={showToast}
              />
            )}

            {activeMode === 'visual' && (
              <VisualBuilder
                stratCols={stratCols}
                setStratCols={setStratCols}
                stratSignal={stratSignal}
                setStratSignal={setStratSignal}
                indicatorsMeta={indicatorsMeta}
                expandPreset={expandPreset}
                showToast={showToast}
              />
            )}

            {activeMode === 'nodes' && (
              <NodeEditor
                stratCols={stratCols}
                setStratCols={setStratCols}
                stratSignal={stratSignal}
                setStratSignal={setStratSignal}
                showToast={showToast}
              />
            )}

            {activeMode === 'code' && (
              <CodeEditor
                stratCols={stratCols}
                setStratCols={setStratCols}
                stratSignal={stratSignal}
                setStratSignal={setStratSignal}
                indicatorsMeta={indicatorsMeta}
                expandPreset={expandPreset}
                showToast={showToast}
              />
            )}

            {/* Validation Error Block */}
            {validationError && (
              <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--color-red)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', marginTop: '1.5rem', fontSize: '0.9rem', color: '#ff8a8a', whiteSpace: 'pre-wrap' }}>
                <strong>Validation Error:</strong><br />
                {validationError}
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem' }}>
              <div>
                {isEditingStrategy && (
                  <button type="button" onClick={() => handleDeleteStrategy(false)} className="btn btn-danger">
                    Delete Strategy
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  onClick={handleNewStrategy}
                  className="btn"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingStrategy}>
                  {isSubmittingStrategy ? 'Validating & Saving...' : 'Save Strategy'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Force Delete Confirmation Overlay */}
      {forceDeleteTarget && (
        <div className="modal-overlay">
          <div className="card modal-content" style={{ maxWidth: '450px' }}>
            <h3 style={{ color: 'var(--color-red)', marginBottom: '1rem' }}>Cascade Delete Required</h3>
            <p style={{ color: 'var(--color-text-main)', marginBottom: '1.5rem', lineHeight: '1.4' }}>
              Strategy <strong>{forceDeleteTarget}</strong> has saved backtest runs. Deleting this strategy will also delete all associated backtest runs.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button onClick={() => setForceDeleteTarget(null)} className="btn">
                Cancel
              </button>
              <button onClick={() => handleDeleteStrategy(true)} className="btn btn-danger">
                Force Delete (Cascade)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
