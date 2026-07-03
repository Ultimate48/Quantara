import React from 'react';

/**
 * CodeEditor — The existing raw formula table + signal rule textarea,
 * extracted into its own component as the "Advanced / Code View".
 */

export default function CodeEditor({
  stratCols, setStratCols,
  stratSignal, setStratSignal,
  indicatorsMeta, expandPreset,
  showToast,
}) {
  const [selectedPreset, setSelectedPreset] = React.useState(
    indicatorsMeta.length > 0 ? indicatorsMeta[0].name : 'SMA'
  );
  const [presetParams, setPresetParams] = React.useState({
    period: 20, fast: 12, slow: 26, signal: 9,
  });

  const handleAddColumn = () => {
    setStratCols([...stratCols, { name: '', formula: '' }]);
  };

  const handleRemoveColumn = (index) => {
    setStratCols(stratCols.filter((_, i) => i !== index));
  };

  const handleColumnChange = (index, key, val) => {
    const updated = [...stratCols];
    updated[index] = { ...updated[index], [key]: val };
    setStratCols(updated);
  };

  const handleInsertPreset = () => {
    const expanded = expandPreset(selectedPreset, presetParams);
    if (expanded.length === 0) {
      showToast('Unknown preset or error expanding.', 'error');
      return;
    }
    const existingNames = stratCols.map(c => c.name);
    const uniqueExpanded = expanded.filter(e => !existingNames.includes(e.name));
    setStratCols([...stratCols, ...uniqueExpanded]);
    showToast(`Added ${expanded.length} column(s) for ${selectedPreset}.`, 'success');
  };

  return (
    <div className="mode-panel">
      {/* Preset Indicator Insert Block */}
      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', color: '#fff' }}>Add Preset Indicators</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '1rem', alignItems: 'end' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Indicator</label>
            <select
              className="select-field"
              value={selectedPreset}
              onChange={(e) => setSelectedPreset(e.target.value)}
            >
              {indicatorsMeta.map(ind => (
                <option key={ind.name} value={ind.name}>{ind.name} - {ind.description}</option>
              ))}
            </select>
          </div>

          {selectedPreset !== 'MACD' ? (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>Period</label>
              <input
                type="number"
                className="input-field"
                value={presetParams.period}
                onChange={(e) => setPresetParams({ ...presetParams, period: e.target.value })}
              />
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Fast</label>
                <input type="number" className="input-field" style={{ padding: '0.75rem 0.5rem' }} value={presetParams.fast} onChange={(e) => setPresetParams({ ...presetParams, fast: e.target.value })} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Slow</label>
                <input type="number" className="input-field" style={{ padding: '0.75rem 0.5rem' }} value={presetParams.slow} onChange={(e) => setPresetParams({ ...presetParams, slow: e.target.value })} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Signal</label>
                <input type="number" className="input-field" style={{ padding: '0.75rem 0.5rem' }} value={presetParams.signal} onChange={(e) => setPresetParams({ ...presetParams, signal: e.target.value })} />
              </div>
            </div>
          )}

          <button type="button" onClick={handleInsertPreset} className="btn" style={{ height: '42px' }}>
            Insert Preset
          </button>
        </div>
      </div>

      {/* Columns Table */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <label className="form-label" style={{ margin: 0, alignSelf: 'center' }}>Formula Mappings (Columns)</label>
          <button type="button" onClick={handleAddColumn} className="btn" style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
            + Add Custom Row
          </button>
        </div>

        <div className="table-container" style={{ maxHeight: '300px', overflowY: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Column Name</th>
                <th>Formula Expression</th>
                <th style={{ width: '60px' }}>Remove</th>
              </tr>
            </thead>
            <tbody>
              {stratCols.length === 0 ? (
                <tr>
                  <td colSpan="3" style={{ textAlign: 'center', color: 'var(--color-text-dim)' }}>
                    No columns mapped yet. Add a custom row or insert presets above.
                  </td>
                </tr>
              ) : (
                stratCols.map((col, index) => (
                  <tr key={index}>
                    <td>
                      <input
                        type="text"
                        className="input-field"
                        style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}
                        placeholder="e.g. sma_20"
                        value={col.name}
                        onChange={(e) => handleColumnChange(index, 'name', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        className="input-field"
                        style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}
                        placeholder="e.g. close.rolling(20).mean()"
                        value={col.formula}
                        onChange={(e) => handleColumnChange(index, 'formula', e.target.value)}
                      />
                    </td>
                    <td>
                      <button type="button" onClick={() => handleRemoveColumn(index)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem' }}>
                        &times;
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Signal Rule */}
      <div className="form-group">
        <label className="form-label">Signal Rule</label>
        <textarea
          className="textarea-field"
          style={{ fontFamily: 'var(--font-mono)' }}
          placeholder="e.g. sma_5 > sma_20 : 1, sma_5 < sma_20 : -1, True : 0"
          value={stratSignal}
          onChange={(e) => setStratSignal(e.target.value)}
        />
      </div>
    </div>
  );
}
