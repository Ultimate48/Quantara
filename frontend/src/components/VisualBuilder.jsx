import React, { useState, useMemo } from 'react';

/**
 * VisualBuilder — Two-section visual strategy builder:
 * 1. Indicator Stack Composer: card grid with parameter sliders
 * 2. Visual Signal Rule Builder: structured condition rows
 */

const INDICATOR_ICONS = {
  SMA: '📊', EMA: '📈', RSI: '⚡', MACD: '📉', BB: '🎯', ATR: '🔥', ROC: '🚀',
};

const INDICATOR_SLIDER_CONFIG = {
  SMA:  { params: [{ key: 'period', label: 'Period', min: 2, max: 200, default: 20 }] },
  EMA:  { params: [{ key: 'period', label: 'Period', min: 2, max: 200, default: 12 }] },
  RSI:  { params: [{ key: 'period', label: 'Period', min: 2, max: 50,  default: 14 }] },
  BB:   { params: [{ key: 'period', label: 'Period', min: 5, max: 100, default: 20 }] },
  ATR:  { params: [{ key: 'period', label: 'Period', min: 2, max: 50,  default: 14 }] },
  ROC:  { params: [{ key: 'period', label: 'Period', min: 1, max: 100, default: 20 }] },
  MACD: { params: [
    { key: 'fast',   label: 'Fast EMA',   min: 2, max: 50,  default: 12 },
    { key: 'slow',   label: 'Slow EMA',   min: 5, max: 100, default: 26 },
    { key: 'signal', label: 'Signal EMA', min: 2, max: 50,  default: 9 },
  ]},
};

const OPERATORS = ['>', '<', '>=', '<=', '=='];
const BASE_COLUMNS = ['close', 'open', 'high', 'low', 'volume'];

export default function VisualBuilder({
  stratCols, setStratCols,
  stratSignal, setStratSignal,
  indicatorsMeta, expandPreset,
  showToast,
}) {
  const [selectedIndicator, setSelectedIndicator] = useState(null);
  const [sliderValues, setSliderValues] = useState({});
  const [addedIndicators, setAddedIndicators] = useState([]);

  // Parse signal rule into condition rows for the builder
  const [conditions, setConditions] = useState(() => parseSignalRule(stratSignal));

  // Available columns for the signal builder dropdowns
  const availableColumns = useMemo(() => {
    const colNames = stratCols.map(c => c.name).filter(Boolean);
    return [...new Set([...BASE_COLUMNS, ...colNames])];
  }, [stratCols]);

  // ——— Indicator Stack Composer ———

  const handleSelectIndicator = (indName) => {
    if (selectedIndicator === indName) {
      setSelectedIndicator(null);
      return;
    }
    setSelectedIndicator(indName);
    // Initialize slider values with defaults
    const config = INDICATOR_SLIDER_CONFIG[indName];
    if (config) {
      const defaults = {};
      config.params.forEach(p => { defaults[p.key] = p.default; });
      setSliderValues(defaults);
    }
  };

  const handleSliderChange = (key, val) => {
    setSliderValues(prev => ({ ...prev, [key]: parseInt(val) || 0 }));
  };

  const previewColumns = useMemo(() => {
    if (!selectedIndicator) return [];
    return expandPreset(selectedIndicator, sliderValues);
  }, [selectedIndicator, sliderValues, expandPreset]);

  const handleAddIndicator = () => {
    if (!selectedIndicator || previewColumns.length === 0) return;

    const existingNames = stratCols.map(c => c.name);
    const uniqueCols = previewColumns.filter(c => !existingNames.includes(c.name));

    if (uniqueCols.length === 0) {
      showToast(`All columns for ${selectedIndicator} already exist.`, 'info');
      return;
    }

    setStratCols([...stratCols, ...uniqueCols]);
    setAddedIndicators([...addedIndicators, selectedIndicator]);
    showToast(`Added ${uniqueCols.length} column(s) for ${selectedIndicator}.`, 'success');
    setSelectedIndicator(null);
  };

  // ——— Signal Rule Builder ———

  const handleAddCondition = () => {
    setConditions([
      ...conditions.filter(c => !c.isFallback),
      { column: availableColumns[0] || 'close', operator: '>', value: '0', signal: '1', isFallback: false },
      ...conditions.filter(c => c.isFallback),
    ]);
  };

  const handleConditionChange = (index, field, val) => {
    const updated = [...conditions];
    updated[index] = { ...updated[index], [field]: val };
    setConditions(updated);
  };

  const handleRemoveCondition = (index) => {
    if (conditions[index].isFallback) return;
    setConditions(conditions.filter((_, i) => i !== index));
  };

  // Serialize conditions to signal_rule string format
  const serializedSignal = useMemo(() => {
    return conditions.map(c => {
      if (c.isFallback) return `True : ${c.signal}`;
      return `${c.column} ${c.operator} ${c.value} : ${c.signal}`;
    }).join(', ');
  }, [conditions]);

  // Sync serialized signal back to parent
  React.useEffect(() => {
    setStratSignal(serializedSignal);
  }, [serializedSignal, setStratSignal]);

  // Re-parse when switching to this tab if signal changed externally
  React.useEffect(() => {
    const parsed = parseSignalRule(stratSignal);
    if (parsed.length > 0 && JSON.stringify(parsed) !== JSON.stringify(conditions)) {
      setConditions(parsed);
    }
    // eslint-disable-next-line
  }, []);

  return (
    <div className="mode-panel">
      {/* ——— Section 1: Indicator Stack Composer ——— */}
      <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', marginBottom: '1rem' }}>
        📐 Indicator Stack
      </h4>

      {/* Indicator Cards Grid */}
      <div className="indicator-grid">
        {indicatorsMeta.map(ind => {
          const isAdded = addedIndicators.includes(ind.name);
          const isSelected = selectedIndicator === ind.name;
          return (
            <div
              key={ind.name}
              className={`indicator-card ${isSelected ? 'selected' : ''} ${isAdded ? 'added' : ''}`}
              onClick={() => handleSelectIndicator(ind.name)}
            >
              {isAdded && <span className="added-badge">✓</span>}
              <div className="indicator-card-icon">{INDICATOR_ICONS[ind.name] || '📊'}</div>
              <div className="indicator-card-name">{ind.name}</div>
              <div className="indicator-card-desc">{ind.description}</div>
            </div>
          );
        })}
      </div>

      {/* Config Panel (shown when an indicator is selected) */}
      {selectedIndicator && INDICATOR_SLIDER_CONFIG[selectedIndicator] && (
        <div className="indicator-config-panel">
          <div className="indicator-config-header">
            <span className="indicator-config-title">
              {INDICATOR_ICONS[selectedIndicator]} Configure {selectedIndicator}
            </span>
            <button
              className="btn btn-primary"
              style={{ padding: '0.35rem 1rem', fontSize: '0.8rem' }}
              onClick={handleAddIndicator}
            >
              Add to Strategy
            </button>
          </div>

          {/* Parameter Sliders */}
          {INDICATOR_SLIDER_CONFIG[selectedIndicator].params.map(param => (
            <div key={param.key} className="param-slider-group">
              <div className="param-slider-header">
                <span className="param-slider-label">{param.label}</span>
                <span className="param-slider-value">{sliderValues[param.key] || param.default}</span>
              </div>
              <input
                type="range"
                className="param-slider"
                min={param.min}
                max={param.max}
                value={sliderValues[param.key] || param.default}
                onChange={(e) => handleSliderChange(param.key, e.target.value)}
              />
            </div>
          ))}

          {/* Live Preview */}
          {previewColumns.length > 0 && (
            <div className="preview-columns">
              <div className="preview-columns-title">Columns to be generated</div>
              {previewColumns.map((col, i) => (
                <div key={i} className="preview-column-row">
                  <span className="preview-col-name">{col.name}</span>
                  <span className="preview-col-formula">{col.formula}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Current Columns Summary */}
      {stratCols.length > 0 && (
        <div className="columns-summary">
          <div className="columns-summary-header">
            <span className="columns-summary-title">Active Columns</span>
            <span className="columns-summary-count">{stratCols.length} column(s)</span>
          </div>
          {stratCols.map((col, i) => (
            <div key={i} className="preview-column-row">
              <span className="preview-col-name">{col.name}</span>
              <span className="preview-col-formula">{col.formula}</span>
            </div>
          ))}
        </div>
      )}

      {/* ——— Section 2: Visual Signal Rule Builder ——— */}
      <div className="signal-builder">
        <div className="signal-builder-header">
          <h4 className="signal-builder-title">⚡ Signal Rule Builder</h4>
          <button
            type="button"
            className="btn"
            style={{ padding: '0.3rem 0.8rem', fontSize: '0.8rem' }}
            onClick={handleAddCondition}
          >
            + Add Condition
          </button>
        </div>

        <div className="condition-rows">
          {conditions.map((cond, index) => (
            <div key={index} className={`condition-row ${cond.isFallback ? 'fallback' : ''}`}>
              {!cond.isFallback && (
                <span className="condition-drag" title="Drag to reorder">⋮⋮</span>
              )}

              {cond.isFallback ? (
                <span style={{ flex: 1, fontSize: '0.85rem', color: 'var(--accent-violet)', fontWeight: 600 }}>
                  Default (fallback)
                </span>
              ) : (
                <>
                  {/* Column Select */}
                  <select
                    className="condition-select"
                    value={cond.column}
                    onChange={(e) => handleConditionChange(index, 'column', e.target.value)}
                  >
                    {availableColumns.map(col => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>

                  {/* Operator Select */}
                  <select
                    className="condition-select"
                    style={{ minWidth: '60px' }}
                    value={cond.operator}
                    onChange={(e) => handleConditionChange(index, 'operator', e.target.value)}
                  >
                    {OPERATORS.map(op => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>

                  {/* Value Input */}
                  <input
                    type="text"
                    className="condition-input"
                    value={cond.value}
                    onChange={(e) => handleConditionChange(index, 'value', e.target.value)}
                    placeholder="value"
                  />
                </>
              )}

              <span className="condition-arrow">→</span>

              {/* Signal Select */}
              <select
                className={`signal-select ${cond.signal === '1' ? 'buy' : cond.signal === '-1' ? 'sell' : 'hold'}`}
                value={cond.signal}
                onChange={(e) => handleConditionChange(index, 'signal', e.target.value)}
              >
                <option value="1">Buy (1)</option>
                <option value="-1">Sell (-1)</option>
                <option value="0">Hold (0)</option>
              </select>

              {/* Remove Button */}
              {!cond.isFallback && (
                <button
                  type="button"
                  className="condition-remove"
                  onClick={() => handleRemoveCondition(index)}
                  title="Remove condition"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Serialized Output Preview */}
        <div className="signal-preview">
          <div className="signal-preview-label">Generated Signal Rule</div>
          <div className="signal-preview-code">
            {serializedSignal || 'No conditions defined'}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Parse a signal_rule string back into structured condition objects.
 * Format: "column op value : signal, column op value : signal, True : 0"
 */
function parseSignalRule(ruleStr) {
  if (!ruleStr || !ruleStr.trim()) {
    return [{ column: '', operator: '>', value: '', signal: '0', isFallback: true }];
  }

  const conditions = [];
  const clauses = ruleStr.split(',').map(s => s.trim());

  for (const clause of clauses) {
    const colonIdx = clause.lastIndexOf(':');
    if (colonIdx === -1) continue;

    const conditionPart = clause.substring(0, colonIdx).trim();
    const signalPart = clause.substring(colonIdx + 1).trim();

    if (conditionPart === 'True' || conditionPart === 'true') {
      conditions.push({ column: '', operator: '>', value: '', signal: signalPart, isFallback: true });
      continue;
    }

    // Try to parse "column operator value"
    const match = conditionPart.match(/^(.+?)\s*(>=|<=|==|>|<)\s*(.+)$/);
    if (match) {
      conditions.push({
        column: match[1].trim(),
        operator: match[2],
        value: match[3].trim(),
        signal: signalPart,
        isFallback: false,
      });
    } else {
      // Complex expression — put as-is in column field
      conditions.push({
        column: conditionPart,
        operator: '>',
        value: '0',
        signal: signalPart,
        isFallback: false,
      });
    }
  }

  // Ensure there's always a fallback row
  if (!conditions.some(c => c.isFallback)) {
    conditions.push({ column: '', operator: '>', value: '', signal: '0', isFallback: true });
  }

  return conditions;
}
