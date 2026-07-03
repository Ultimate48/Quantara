import React, { useState, useEffect } from 'react';
import EquityChart from './components/EquityChart';
import StrategyLab from './components/StrategyLab';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from 'recharts';

// Inline helper for preset indicator calculations matching indicators.py
const expandPreset = (name, params) => {
  const p = { ...params };
  switch (name) {
    case 'RSI': {
      const period = parseInt(p.period) || 14;
      return [
        { name: 'rsi_delta', formula: 'close.diff()' },
        { name: 'rsi_gain', formula: 'rsi_delta.clip(lower=0)' },
        { name: 'rsi_loss', formula: '-rsi_delta.clip(upper=0)' },
        { name: 'rsi_avg_gain', formula: `rsi_gain.rolling(${period}).mean()` },
        { name: 'rsi_avg_loss', formula: `rsi_loss.rolling(${period}).mean()` },
        { name: 'rsi_rs', formula: 'rsi_avg_gain / rsi_avg_loss' },
        { name: 'rsi', formula: '100 - (100 / (1 + rsi_rs))' }
      ];
    }
    case 'SMA': {
      const period = parseInt(p.period) || 20;
      return [
        { name: `sma_${period}`, formula: `close.rolling(${period}).mean()` }
      ];
    }
    case 'EMA': {
      const period = parseInt(p.period) || 12;
      return [
        { name: `ema_${period}`, formula: `close.ewm(span=${period}, adjust=False).mean()` }
      ];
    }
    case 'BB': {
      const period = parseInt(p.period) || 20;
      return [
        { name: 'bb_mid', formula: `close.rolling(${period}).mean()` },
        { name: 'bb_std', formula: `close.rolling(${period}).std()` },
        { name: 'bb_upper', formula: 'bb_mid + 2 * bb_std' },
        { name: 'bb_lower', formula: 'bb_mid - 2 * bb_std' }
      ];
    }
    case 'MACD': {
      const fast = parseInt(p.fast) || 12;
      const slow = parseInt(p.slow) || 26;
      const signal = parseInt(p.signal) || 9;
      return [
        { name: 'macd_fast', formula: `close.ewm(span=${fast}, adjust=False).mean()` },
        { name: 'macd_slow', formula: `close.ewm(span=${slow}, adjust=False).mean()` },
        { name: 'macd_line', formula: 'macd_fast - macd_slow' },
        { name: 'macd_signal', formula: `macd_line.ewm(span=${signal}, adjust=False).mean()` },
        { name: 'macd_hist', formula: 'macd_line - macd_signal' }
      ];
    }
    case 'ATR': {
      const period = parseInt(p.period) || 14;
      return [
        { name: 'atr_prev_close', formula: 'close.shift(1)' },
        { name: 'atr_tr1', formula: 'high - low' },
        { name: 'atr_tr2', formula: '(high - atr_prev_close).abs()' },
        { name: 'atr_tr3', formula: '(low - atr_prev_close).abs()' },
        { name: 'atr_tr', formula: 'atr_tr1.combine(atr_tr2, max).combine(atr_tr3, max)' },
        { name: 'atr', formula: `atr_tr.rolling(${period}).mean()` }
      ];
    }
    case 'ROC': {
      const period = parseInt(p.period) || 20;
      return [
        { name: `roc_${period}`, formula: `(close - close.shift(${period})) / close.shift(${period}) * 100` }
      ];
    }
    default:
      return [];
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stocks, setStocks] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [backtests, setBacktests] = useState([]);
  const [indicatorsMeta, setIndicatorsMeta] = useState([]);
  
  // Loading states
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingStrategies, setLoadingStrategies] = useState(false);
  const [loadingBacktests, setLoadingBacktests] = useState(false);
  const [loadingIndicators, setLoadingIndicators] = useState(false);
  const [isSubmittingStock, setIsSubmittingStock] = useState(false);
  const [isSubmittingStrategy, setIsSubmittingStrategy] = useState(false);
  const [isSubmittingBacktest, setIsSubmittingBacktest] = useState(false);
  
  // Toast notifications
  const [toasts, setToasts] = useState([]);
  
  // Watchlist (Stocks) Form
  const [stockTicker, setStockTicker] = useState('');
  const [stockStart, setStockStart] = useState('2020-01-01');
  const [stockEnd, setStockEnd] = useState('2023-12-31');
  const [stockInterval, setStockInterval] = useState('1d');
  
  // Backtester Form State
  const [btStrategy, setBtStrategy] = useState('');
  const [btTicker, setBtTicker] = useState('');
  const [btStart, setBtStart] = useState('2020-01-01');
  const [btEnd, setBtEnd] = useState('2023-12-31');
  const [btCapital, setBtCapital] = useState(100000);
  const [btCooldown, setBtCooldown] = useState(0);
  const [btStopLoss, setBtStopLoss] = useState('');
  const [btTakeProfit, setBtTakeProfit] = useState('');
  const [btMode, setBtMode] = useState('long');
  const [btConfirmBuy, setBtConfirmBuy] = useState(1);
  const [btConfirmSell, setBtConfirmSell] = useState(1);
  const [btPositionSize, setBtPositionSize] = useState('all');
  const [btPositionVal, setBtPositionVal] = useState('');
  const [btTxCost, setBtTxCost] = useState(0.0);
  const [btSlippage, setBtSlippage] = useState(0.0);
  
  // Backtester Results State
  const [currentBacktestResult, setCurrentBacktestResult] = useState(null);
  const [tradeLogPage, setTradeLogPage] = useState(1);
  const tradesPerPage = 10;
  
  // History Detail Overlay Modal
  const [detailedRun, setDetailedRun] = useState(null);
  const [loadingRunDetail, setLoadingRunDetail] = useState(false);
  
  // Compare State
  const [selectedCompareIds, setSelectedCompareIds] = useState([]);
  const [comparisonDetails, setComparisonDetails] = useState([]);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [comparisonChartData, setComparisonChartData] = useState([]);

  // Toast handler
  const showToast = (message, type = 'info') => {
    const id = Date.now() + Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  // Fetch initial data
  const fetchStocks = async () => {
    setLoadingStocks(true);
    try {
      const res = await fetch('/api/stocks/');
      if (!res.ok) throw new Error('Failed to load stocks.');
      const data = await res.json();
      setStocks(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingStocks(false);
    }
  };

  const fetchStrategies = async () => {
    setLoadingStrategies(true);
    try {
      const res = await fetch('/api/strategies/');
      if (!res.ok) throw new Error('Failed to load strategies.');
      const data = await res.json();
      setStrategies(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingStrategies(false);
    }
  };

  const fetchBacktests = async () => {
    setLoadingBacktests(true);
    try {
      const res = await fetch('/api/backtest/');
      if (!res.ok) throw new Error('Failed to load backtest runs.');
      const data = await res.json();
      // Sort descending by execution time if not done by backend
      const sortedData = data.sort((a, b) => b.id - a.id);
      setBacktests(sortedData);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingBacktests(false);
    }
  };

  const fetchIndicatorsMeta = async () => {
    setLoadingIndicators(true);
    try {
      const res = await fetch('/api/indicators');
      if (!res.ok) throw new Error('Failed to load indicators metadata.');
      const data = await res.json();
      setIndicatorsMeta(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingIndicators(false);
    }
  };

  useEffect(() => {
    fetchStocks();
    fetchStrategies();
    fetchBacktests();
    fetchIndicatorsMeta();
  }, []);

  // Sync backtest parameters when dropdown selections change
  useEffect(() => {
    if (strategies.length > 0 && !btStrategy) {
      setBtStrategy(strategies[0].name);
    }
    if (stocks.length > 0 && !btTicker) {
      setBtTicker(stocks[0].ticker);
    }
  }, [strategies, stocks]);

  // Fetch Stock Handler
  const handleFetchStock = async (e) => {
    e.preventDefault();
    if (!stockTicker) {
      showToast('Ticker is required.', 'error');
      return;
    }
    setIsSubmittingStock(true);
    try {
      const res = await fetch('/api/stocks/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: stockTicker.trim().toUpperCase(),
          start: stockStart || null,
          end: stockEnd || null,
          interval: stockInterval
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Fetch failed.');
      showToast(data.message || 'Ticker fetched successfully.', 'success');
      setStockTicker('');
      fetchStocks();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmittingStock(false);
    }
  };

  // Execute Backtest Handler
  const handleExecuteBacktest = async (e) => {
    e.preventDefault();
    if (!btStrategy) {
      showToast('Select a strategy.', 'error');
      return;
    }
    if (!btTicker) {
      showToast('Select a stock.', 'error');
      return;
    }

    setIsSubmittingBacktest(true);
    setCurrentBacktestResult(null);
    setTradeLogPage(1);

    // Format position_size parameter
    let posSize = 'all';
    if (btPositionSize !== 'all' && btPositionVal) {
      posSize = `${btPositionSize}:${btPositionVal}`;
    }

    const payload = {
      strategy: btStrategy,
      ticker: btTicker,
      start: btStart || null,
      end: btEnd || null,
      capital: parseFloat(btCapital) || 100000.0,
      cooldown: parseInt(btCooldown) || 0,
      stop_loss: btStopLoss ? parseFloat(btStopLoss) / 100 : null,
      take_profit: btTakeProfit ? parseFloat(btTakeProfit) / 100 : null,
      mode: btMode,
      confirm_buy: parseInt(btConfirmBuy) || 1,
      confirm_sell: parseInt(btConfirmSell) || 1,
      position_size: posSize,
      transaction_cost: parseFloat(btTxCost) / 100 || 0.0,
      slippage: parseFloat(btSlippage) / 100 || 0.0
    };

    try {
      const res = await fetch('/api/backtest/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Backtest failed.');
      
      showToast('Backtest executed successfully!', 'success');
      setCurrentBacktestResult(data);
      fetchBacktests(); // reload history
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmittingBacktest(false);
    }
  };

  // Fetch Backtest Detail for History/Modal
  const viewBacktestDetails = async (runId) => {
    setLoadingRunDetail(true);
    try {
      const res = await fetch(`/api/backtest/${runId}`);
      if (!res.ok) throw new Error('Failed to load backtest details.');
      const data = await res.json();
      setDetailedRun(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingRunDetail(false);
    }
  };

  // Compare Checkbox Toggle
  const handleCompareToggle = (runId) => {
    setSelectedCompareIds(prev => 
      prev.includes(runId) 
        ? prev.filter(id => id !== runId) 
        : [...prev, runId]
    );
  };

  // Run Comparison Fetch & Merge
  useEffect(() => {
    if (activeTab !== 'compare' || selectedCompareIds.length < 2) {
      setComparisonChartData([]);
      setComparisonDetails([]);
      return;
    }

    const fetchComparisonData = async () => {
      setLoadingComparison(true);
      try {
        const detailsPromises = selectedCompareIds.map(async (id) => {
          const res = await fetch(`/api/backtest/${id}`);
          if (!res.ok) throw new Error(`Failed to load details for run #${id}`);
          return res.json();
        });
        
        const results = await Promise.all(detailsPromises);
        setComparisonDetails(results);

        // Merge curves by date
        const dateMap = {};
        results.forEach((run) => {
          const strategyName = strategies.find(s => s.id === run.strategy_id)?.name || `Strategy ${run.strategy_id}`;
          const label = `Run #${run.id} (${strategyName} on ${run.execute_on})`;
          
          run.equity_curve.forEach((pt) => {
            const dateStr = pt.date;
            if (!dateMap[dateStr]) {
              dateMap[dateStr] = { date: dateStr };
            }
            dateMap[dateStr][label] = pt.value;
          });
        });

        // Convert map to sorted array
        const sortedMerged = Object.values(dateMap).sort((a, b) => new Date(a.date) - new Date(b.date));
        setComparisonChartData(sortedMerged);

      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        setLoadingComparison(false);
      }
    };

    fetchComparisonData();

  }, [selectedCompareIds, activeTab]);

  // Format currency
  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  };

  // Format percent
  const formatPercent = (val) => {
    if (val === null || val === undefined) return '';
    const prefix = val >= 0 ? '+' : '';
    return `${prefix}${val.toFixed(2)}%`;
  };

  const getStrategyNameById = (id) => {
    const s = strategies.find(x => x.id === id);
    return s ? s.name : `Strategy #${id}`;
  };

  return (
    <div className="app-container">
      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.type}`}>
            <div style={{ flex: 1 }}>{t.message}</div>
            <button 
              onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))}
              style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '1rem' }}
            >
              &times;
            </button>
          </div>
        ))}
      </div>

      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-section">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: '#06b6d4' }}>
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
          Quantara
        </div>
        
        <nav style={{ flex: 1 }}>
          <ul className="nav-links">
            <li>
              <div onClick={() => setActiveTab('dashboard')} className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="7" height="9" />
                  <rect x="14" y="3" width="7" height="5" />
                  <rect x="14" y="12" width="7" height="9" />
                  <rect x="3" y="16" width="7" height="5" />
                </svg>
                Dashboard
              </div>
            </li>
            <li>
              <div onClick={() => setActiveTab('stocks')} className={`nav-item ${activeTab === 'stocks' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 3v18h18" />
                  <path d="m18 17-5.5-5.5-3 3-5-5" />
                </svg>
                Watchlist
              </div>
            </li>
            <li>
              <div onClick={() => setActiveTab('strategies')} className={`nav-item ${activeTab === 'strategies' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                  <path d="M12 6v6l4 2" />
                </svg>
                Strategy Lab
              </div>
            </li>
            <li>
              <div onClick={() => setActiveTab('backtest')} className={`nav-item ${activeTab === 'backtest' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
                Backtest Lab
              </div>
            </li>
            <li>
              <div onClick={() => setActiveTab('compare')} className={`nav-item ${activeTab === 'compare' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 3h5v5" />
                  <path d="M8 3H3v5" />
                  <path d="M12 22V12" />
                  <path d="m17 21 4-4" />
                  <path d="m7 21-4-4" />
                </svg>
                Compare Runs
              </div>
            </li>
            <li>
              <div onClick={() => setActiveTab('history')} className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 8v4l3 3" />
                  <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" />
                </svg>
                History
              </div>
            </li>
          </ul>
        </nav>
        
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', textAlign: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
          Quantara v2.3.0
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        
        {/* ==================== DASHBOARD VIEW ==================== */}
        {activeTab === 'dashboard' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">Dashboard Overview</h1>
              <p className="page-subtitle">Algorithmic trading metrics and backtester summaries at a glance.</p>
            </header>

            {/* Stats Grid */}
            <div className="stats-grid">
              <div className="card stat-card">
                <span className="stat-label">Database Stocks</span>
                <span className="stat-value">{loadingStocks ? '...' : stocks.length}</span>
                <span className="stat-delta positive">
                  <span>✔</span> Online
                </span>
              </div>
              <div className="card stat-card">
                <span className="stat-label">Active Strategies</span>
                <span className="stat-value">{loadingStrategies ? '...' : strategies.length}</span>
                <span className="stat-delta positive">
                  <span>✔</span> Dynamic Formula Evaluation
                </span>
              </div>
              <div className="card stat-card">
                <span className="stat-label">Backtest Executes</span>
                <span className="stat-value">{loadingBacktests ? '...' : backtests.length}</span>
                <span className="stat-delta positive">
                  <span>✔</span> Performance Logged
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
              {/* Recent Runs */}
              <div className="card">
                <h3 style={{ marginBottom: '1.25rem', color: '#fff' }}>Recent Backtest Executions</h3>
                {loadingBacktests ? (
                  <div className="spinner-container"><div className="spinner"></div></div>
                ) : backtests.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted)' }}>No backtest runs found. Head to the Backtest Lab to run one.</p>
                ) : (
                  <div className="table-container">
                    <table className="glass-table">
                      <thead>
                        <tr>
                          <th>Run ID</th>
                          <th>Strategy</th>
                          <th>Stock</th>
                          <th>Period</th>
                          <th>Total Return</th>
                          <th>Sharpe</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {backtests.slice(0, 5).map(run => (
                          <tr key={run.id}>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>#{run.id}</td>
                            <td>{getStrategyNameById(run.strategy_id)}</td>
                            <td>{run.execute_on}</td>
                            <td style={{ fontSize: '0.85rem' }}>{run.start_date} to {run.end_date}</td>
                            <td style={{ fontWeight: 'bold', color: run.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                              {formatPercent(run.total_return)}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>{run.sharpe_ratio.toFixed(2)}</td>
                            <td>
                              <button onClick={() => { viewBacktestDetails(run.id); setActiveTab('history'); }} className="btn" style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Quick Actions */}
              <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <h3 style={{ color: '#fff' }}>Quick Actions</h3>
                <button onClick={() => setActiveTab('backtest')} className="btn btn-primary" style={{ width: '100%' }}>
                  Launch Backtester
                </button>
                <button onClick={() => setActiveTab('strategies')} className="btn" style={{ width: '100%' }}>
                  Manage Strategies
                </button>
                <button onClick={() => setActiveTab('stocks')} className="btn" style={{ width: '100%' }}>
                  Fetch Stock Data
                </button>
                <div style={{ marginTop: '1.5rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', padding: '1rem' }}>
                  <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: '1.4' }}>
                    <strong>Note:</strong> Quantara uses <code>asteval</code> for mathematical parsing, enabling safe custom columns and indicators to execute inside Postgres without arbitrary code execution risk.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== WATCHLIST (STOCKS) VIEW ==================== */}
        {activeTab === 'stocks' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">Watchlist Data Lab</h1>
              <p className="page-subtitle">Fetch and display daily historical price bars from Yahoo Finance.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
              {/* Fetch Form */}
              <div className="card" style={{ height: 'fit-content' }}>
                <h3 style={{ marginBottom: '1.5rem', color: '#fff' }}>Fetch Historical Price bars</h3>
                <form onSubmit={handleFetchStock}>
                  <div className="form-group">
                    <label className="form-label">Ticker Symbol</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      placeholder="e.g. AAPL, SPY, TSLA"
                      value={stockTicker}
                      onChange={(e) => setStockTicker(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Start Date</label>
                    <input 
                      type="date" 
                      className="input-field"
                      value={stockStart}
                      onChange={(e) => setStockStart(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">End Date</label>
                    <input 
                      type="date" 
                      className="input-field"
                      value={stockEnd}
                      onChange={(e) => setStockEnd(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Data Interval</label>
                    <select 
                      className="select-field"
                      value={stockInterval}
                      onChange={(e) => setStockInterval(e.target.value)}
                    >
                      <option value="1d">1 Day</option>
                      <option value="1wk">1 Week</option>
                      <option value="1mo">1 Month</option>
                    </select>
                  </div>

                  <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={isSubmittingStock}>
                    {isSubmittingStock ? (
                      <>
                        <div className="spinner" style={{ width: '16px', height: '16px', borderThickness: '2px' }}></div>
                        Fetching bars...
                      </>
                    ) : 'Fetch and Save Ticker'}
                  </button>
                </form>
              </div>

              {/* Stocks Table */}
              <div className="card">
                <h3 style={{ marginBottom: '1.25rem', color: '#fff' }}>Tracked Tickers</h3>
                {loadingStocks ? (
                  <div className="spinner-container"><div className="spinner"></div></div>
                ) : stocks.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted)' }}>No stock data downloaded yet.</p>
                ) : (
                  <div className="table-container">
                    <table className="glass-table">
                      <thead>
                        <tr>
                          <th>Ticker</th>
                          <th>Company / Index Name</th>
                          <th>Market Segment</th>
                          <th>Database Added Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stocks.map(stock => (
                          <tr key={stock.ticker}>
                            <td style={{ fontWeight: 'bold', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>{stock.ticker}</td>
                            <td>{stock.name || 'Stock Data'}</td>
                            <td>{stock.market || 'USD Equity'}</td>
                            <td style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                              {stock.added_at ? new Date(stock.added_at).toLocaleString() : 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================== STRATEGY LAB VIEW ==================== */}
        {activeTab === 'strategies' && (
          <StrategyLab
            strategies={strategies}
            fetchStrategies={fetchStrategies}
            indicatorsMeta={indicatorsMeta}
            expandPreset={expandPreset}
            showToast={showToast}
          />
        )}

        {/* ==================== BACKTEST LAB VIEW ==================== */}
        {activeTab === 'backtest' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">Backtest Lab</h1>
              <p className="page-subtitle">Configure trading risk parameters and evaluate strategy performance indicators.</p>
            </header>

            {/* Backtester Setup Form */}
            <div className="card" style={{ marginBottom: '2rem' }}>
              <h3 style={{ marginBottom: '1.5rem', color: '#fff' }}>Configure Backtest Run</h3>
              <form onSubmit={handleExecuteBacktest}>
                <div className="input-row">
                  <div className="form-group">
                    <label className="form-label">Strategy</label>
                    <select 
                      className="select-field"
                      value={btStrategy}
                      onChange={(e) => setBtStrategy(e.target.value)}
                    >
                      {strategies.map(s => (
                        <option key={s.name} value={s.name}>{s.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Ticker Symbol</label>
                    <select 
                      className="select-field"
                      value={btTicker}
                      onChange={(e) => setBtTicker(e.target.value)}
                    >
                      {stocks.map(s => (
                        <option key={s.ticker} value={s.ticker}>{s.ticker} ({s.name || 'Stock Data'})</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Start Date</label>
                    <input 
                      type="date" 
                      className="input-field"
                      value={btStart}
                      onChange={(e) => setBtStart(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">End Date</label>
                    <input 
                      type="date" 
                      className="input-field"
                      value={btEnd}
                      onChange={(e) => setBtEnd(e.target.value)}
                    />
                  </div>
                </div>

                <div className="input-row">
                  <div className="form-group">
                    <label className="form-label">Initial Capital ($)</label>
                    <input 
                      type="number" 
                      className="input-field"
                      value={btCapital}
                      onChange={(e) => setBtCapital(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Trade Cooldown (Days)</label>
                    <input 
                      type="number" 
                      className="input-field"
                      value={btCooldown}
                      onChange={(e) => setBtCooldown(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Stop Loss (%)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 5 for 5%"
                      value={btStopLoss}
                      onChange={(e) => setBtStopLoss(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Take Profit (%)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 10 for 10%"
                      value={btTakeProfit}
                      onChange={(e) => setBtTakeProfit(e.target.value)}
                    />
                  </div>
                </div>

                <div className="input-row">
                  <div className="form-group">
                    <label className="form-label">Trading Mode</label>
                    <select 
                      className="select-field"
                      value={btMode}
                      onChange={(e) => setBtMode(e.target.value)}
                    >
                      <option value="long">Long Only</option>
                      <option value="short">Short Only</option>
                      <option value="both">Long and Short</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Confirm Buy Bar count</label>
                    <input 
                      type="number" 
                      className="input-field"
                      value={btConfirmBuy}
                      onChange={(e) => setBtConfirmBuy(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Confirm Sell Bar count</label>
                    <input 
                      type="number" 
                      className="input-field"
                      value={btConfirmSell}
                      onChange={(e) => setBtConfirmSell(e.target.value)}
                    />
                  </div>

                  <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                    <div>
                      <label className="form-label">Position Sizing</label>
                      <select 
                        className="select-field"
                        value={btPositionSize}
                        onChange={(e) => setBtPositionSize(e.target.value)}
                      >
                        <option value="all">All Capital</option>
                        <option value="fixed">Fixed shares</option>
                        <option value="pct">Percent size</option>
                      </select>
                    </div>
                    {btPositionSize !== 'all' && (
                      <div>
                        <label className="form-label">Value</label>
                        <input 
                          type="number" 
                          className="input-field"
                          placeholder={btPositionSize === 'fixed' ? 'shares' : '%'}
                          value={btPositionVal}
                          onChange={(e) => setBtPositionVal(e.target.value)}
                        />
                      </div>
                    )}
                  </div>
                </div>

                <div className="input-row">
                  <div className="form-group">
                    <label className="form-label">Transaction Costs (%)</label>
                    <input 
                      type="number" 
                      step="0.01"
                      className="input-field"
                      placeholder="e.g. 0.1 for 0.1% fee"
                      value={btTxCost}
                      onChange={(e) => setBtTxCost(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Slippage (%)</label>
                    <input 
                      type="number" 
                      step="0.01"
                      className="input-field"
                      placeholder="e.g. 0.05 for 0.05% slippage"
                      value={btSlippage}
                      onChange={(e) => setBtSlippage(e.target.value)}
                    />
                  </div>
                  
                  <div style={{ gridColumn: 'span 2', display: 'flex', alignItems: 'end', justifyContent: 'flex-end' }}>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%', height: '42px' }} disabled={isSubmittingBacktest}>
                      {isSubmittingBacktest ? 'Simulating Trades...' : 'Execute Backtest'}
                    </button>
                  </div>
                </div>
              </form>
            </div>

            {/* Backtester Results Showcase */}
            {isSubmittingBacktest && (
              <div className="card spinner-container" style={{ flexDirection: 'column', gap: '1rem' }}>
                <div className="spinner"></div>
                <p style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>Simulating historical transactions via ASTeval engine...</p>
              </div>
            )}

            {!isSubmittingBacktest && currentBacktestResult && (
              <div className="card" style={{ animation: 'slide-in 0.3s ease-out forwards' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                  <h3 style={{ color: '#fff' }}>Backtest Simulation Result</h3>
                  <span style={{ fontSize: '0.85rem', color: 'var(--color-text-dim)' }}>
                    Run ID: <strong style={{ color: 'var(--accent-cyan)' }}>#{currentBacktestResult.id}</strong> executed at {new Date(currentBacktestResult.run_at).toLocaleTimeString()}
                  </span>
                </div>

                {/* Return Stats Row */}
                <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                  <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <span className="stat-label">Total Return</span>
                    <span className="stat-value" style={{ color: currentBacktestResult.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                      {formatPercent(currentBacktestResult.total_return)}
                    </span>
                  </div>
                  <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <span className="stat-label">Sharpe Ratio</span>
                    <span className="stat-value">{currentBacktestResult.sharpe_ratio.toFixed(2)}</span>
                  </div>
                  <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <span className="stat-label">Max Drawdown</span>
                    <span className="stat-value" style={{ color: 'var(--color-red)' }}>
                      {formatPercent(currentBacktestResult.max_drawdown)}
                    </span>
                  </div>
                  <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <span className="stat-label">Win Rate</span>
                    <span className="stat-value">{formatPercent(currentBacktestResult.win_rate)}</span>
                  </div>
                  <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <span className="stat-label">Total Trades</span>
                    <span className="stat-value">{currentBacktestResult.total_trades}</span>
                  </div>
                </div>

                {/* Equity Curve Overlay Chart */}
                <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Equity curve overlay vs Buy-and-Hold</h4>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)' }}>
                  <EquityChart 
                    equityCurve={currentBacktestResult.equity_curve} 
                    benchmarkCurve={currentBacktestResult.benchmark_curve || []}
                    tradeLog={currentBacktestResult.trade_log} 
                  />
                </div>

                {/* Transaction Log Table */}
                <h4 style={{ color: '#fff', marginTop: '2rem', marginBottom: '1rem' }}>Transaction History Log</h4>
                {currentBacktestResult.trade_log.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>No trades executed during this backtest timeframe.</p>
                ) : (
                  <div>
                    <div className="table-container">
                      <table className="glass-table">
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Transaction Type</th>
                            <th>Share price</th>
                            <th>Quantity</th>
                            <th>Total Cost</th>
                            <th>Portfolio cash</th>
                            <th>Reason Trigger</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentBacktestResult.trade_log
                            .slice((tradeLogPage - 1) * tradesPerPage, tradeLogPage * tradesPerPage)
                            .map((trade, idx) => (
                              <tr key={idx}>
                                <td>{trade.date}</td>
                                <td style={{ fontWeight: '600', color: trade.type === 'buy' || trade.type === 'cover' ? 'var(--color-green)' : 'var(--color-red)' }}>
                                  {trade.type.toUpperCase()}
                                </td>
                                <td style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(trade.price)}</td>
                                <td style={{ fontFamily: 'var(--font-mono)' }}>{trade.shares.toFixed(2)}</td>
                                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-dim)' }}>{formatCurrency(trade.cost || 0)}</td>
                                <td style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(trade.cash_after)}</td>
                                <td>
                                  <span className="pill" style={{
                                    borderColor: trade.reason === 'stop_loss' || trade.reason === 'take_profit' ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.08)',
                                    color: trade.reason === 'stop_loss' || trade.reason === 'take_profit' ? 'var(--color-red)' : 'var(--color-text-muted)'
                                  }}>
                                    {trade.reason.toUpperCase()}
                                  </span>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {currentBacktestResult.trade_log.length > tradesPerPage && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                          Showing {(tradeLogPage - 1) * tradesPerPage + 1} - {Math.min(tradeLogPage * tradesPerPage, currentBacktestResult.trade_log.length)} of {currentBacktestResult.trade_log.length} trades
                        </span>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button 
                            disabled={tradeLogPage === 1} 
                            onClick={() => setTradeLogPage(prev => prev - 1)}
                            className="btn" 
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                          >
                            Prev
                          </button>
                          <button 
                            disabled={tradeLogPage >= Math.ceil(currentBacktestResult.trade_log.length / tradesPerPage)} 
                            onClick={() => setTradeLogPage(prev => prev + 1)}
                            className="btn" 
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                          >
                            Next
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ==================== COMPARE RUNS VIEW ==================== */}
        {activeTab === 'compare' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">Strategy Comparison Lab</h1>
              <p className="page-subtitle">Select multiple backtest runs to overlay and compare their equity performance curves.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
              {/* Runs Selection Panel */}
              <div className="card" style={{ height: 'fit-content' }}>
                <h3 style={{ marginBottom: '1.25rem', color: '#fff' }}>Select Backtest Runs</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>Select 2 or more runs to generate the comparison chart.</p>
                
                {loadingBacktests ? (
                  <div className="spinner-container"><div className="spinner"></div></div>
                ) : backtests.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted)' }}>No historical runs found.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '450px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                    {backtests.map(run => (
                      <label 
                        key={run.id} 
                        className="card" 
                        style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: '1rem', 
                          padding: '0.75rem 1rem', 
                          cursor: 'pointer',
                          borderColor: selectedCompareIds.includes(run.id) ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.08)',
                          background: selectedCompareIds.includes(run.id) ? 'rgba(6,182,212,0.05)' : 'var(--bg-card)'
                        }}
                      >
                        <input 
                          type="checkbox" 
                          checked={selectedCompareIds.includes(run.id)}
                          onChange={() => handleCompareToggle(run.id)}
                          style={{ accentColor: 'var(--accent-cyan)', width: '16px', height: '16px' }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                            <span style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#fff' }}>Run #{run.id}</span>
                            <span style={{ color: run.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)', fontWeight: 'bold', fontSize: '0.9rem' }}>
                              {formatPercent(run.total_return)}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {getStrategyNameById(run.strategy_id)} on {run.execute_on}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Comparison Results Chart */}
              <div className="card">
                <h3 style={{ marginBottom: '1.5rem', color: '#fff' }}>Equity Comparison Overlay</h3>
                
                {selectedCompareIds.length < 2 ? (
                  <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-dim)', textAlign: 'center', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                    Select at least 2 runs from the left panel to display comparison line overlay.
                  </div>
                ) : loadingComparison ? (
                  <div className="spinner-container"><div className="spinner"></div></div>
                ) : (
                  <div>
                    {/* Stats Comparison Summary */}
                    <div className="table-container" style={{ marginBottom: '2rem' }}>
                      <table className="glass-table">
                        <thead>
                          <tr>
                            <th>Run</th>
                            <th>Strategy</th>
                            <th>Stock</th>
                            <th>Initial Capital</th>
                            <th>ROI</th>
                            <th>Sharpe</th>
                            <th>Max Drawdown</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparisonDetails.map(run => (
                            <tr key={run.id}>
                              <td style={{ fontWeight: 'bold', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>#{run.id}</td>
                              <td>{getStrategyNameById(run.strategy_id)}</td>
                              <td>{run.execute_on}</td>
                              <td style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(run.initial_capital)}</td>
                              <td style={{ fontWeight: 'bold', color: run.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                                {formatPercent(run.total_return)}
                              </td>
                              <td style={{ fontFamily: 'var(--font-mono)' }}>{run.sharpe_ratio.toFixed(2)}</td>
                              <td style={{ color: 'var(--color-red)' }}>{formatPercent(run.max_drawdown)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Chart Overlay */}
                    <div style={{ width: '100%', height: '400px', marginTop: '1rem' }}>
                      {comparisonChartData.length === 0 ? (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7280' }}>
                          Processing timeline alignment...
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={comparisonChartData} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                            <XAxis 
                              dataKey="date" 
                              stroke="#6b7280" 
                              fontSize={11}
                              tickLine={false}
                              axisLine={false}
                            />
                            <YAxis 
                              stroke="#6b7280" 
                              fontSize={11}
                              tickLine={false}
                              axisLine={false}
                              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                              domain={['auto', 'auto']}
                            />
                            <Tooltip 
                              contentStyle={{
                                background: 'rgba(16, 24, 40, 0.95)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                padding: '0.75rem 1rem',
                                borderRadius: '8px',
                                boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
                              }}
                              labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                            />
                            <Legend verticalAlign="top" height={36} />
                            {comparisonDetails.map((run, idx) => {
                              const strategyName = strategies.find(s => s.id === run.strategy_id)?.name || `Strategy ${run.strategy_id}`;
                              const label = `Run #${run.id} (${strategyName} on ${run.execute_on})`;
                              const colors = ['#06b6d4', '#8b5cf6', '#10b981', '#f97316', '#eab308', '#ef4444'];
                              const strokeColor = colors[idx % colors.length];
                              return (
                                <Line 
                                  key={run.id}
                                  name={label}
                                  type="monotone" 
                                  dataKey={label} 
                                  stroke={strokeColor} 
                                  strokeWidth={2.5} 
                                  dot={false}
                                  activeDot={{ r: 4 }}
                                />
                              );
                            })}
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================== HISTORY VIEW ==================== */}
        {activeTab === 'history' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">Backtest History</h1>
              <p className="page-subtitle">View and audit all historical trading strategies executed on tracked assets.</p>
            </header>

            <div className="card">
              <h3 style={{ marginBottom: '1.25rem', color: '#fff' }}>Historical Runs Log</h3>
              {loadingBacktests ? (
                <div className="spinner-container"><div className="spinner"></div></div>
              ) : backtests.length === 0 ? (
                <p style={{ color: 'var(--color-text-muted)' }}>No historical logs recorded. Execute backtests in Backtest Lab.</p>
              ) : (
                <div className="table-container">
                  <table className="glass-table">
                    <thead>
                      <tr>
                        <th>Run ID</th>
                        <th>Execution Date</th>
                        <th>Strategy</th>
                        <th>Stock Asset</th>
                        <th>Return (%)</th>
                        <th>Sharpe Ratio</th>
                        <th>Max DD (%)</th>
                        <th>Win Rate (%)</th>
                        <th>Trades</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {backtests.map(run => (
                        <tr key={run.id}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>#{run.id}</td>
                          <td style={{ fontSize: '0.85rem' }}>{run.run_at ? new Date(run.run_at).toLocaleString() : 'N/A'}</td>
                          <td>{getStrategyNameById(run.strategy_id)}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '600' }}>{run.execute_on}</td>
                          <td style={{ fontWeight: 'bold', color: run.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                            {formatPercent(run.total_return)}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)' }}>{run.sharpe_ratio.toFixed(2)}</td>
                          <td style={{ color: 'var(--color-red)' }}>{formatPercent(run.max_drawdown)}</td>
                          <td>{run.win_rate.toFixed(1)}%</td>
                          <td>{run.total_trades}</td>
                          <td>
                            <button onClick={() => viewBacktestDetails(run.id)} className="btn btn-primary" style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Run Details Modal Overlay */}
            {detailedRun && (
              <div className="modal-overlay" onClick={() => setDetailedRun(null)}>
                <div className="card modal-content" style={{ maxWidth: '850px', width: '95%' }} onClick={(e) => e.stopPropagation()}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                    <h3 style={{ color: '#fff' }}>
                      Backtest Details: Run #{detailedRun.id}
                    </h3>
                    <button onClick={() => setDetailedRun(null)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', borderRadius: '50%', width: '30px', height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      &times;
                    </button>
                  </div>

                  <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                    <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem' }}>
                      <span className="stat-label">Return</span>
                      <span className="stat-value" style={{ color: detailedRun.total_return >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                        {formatPercent(detailedRun.total_return)}
                      </span>
                    </div>
                    <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem' }}>
                      <span className="stat-label">Sharpe Ratio</span>
                      <span className="stat-value">{detailedRun.sharpe_ratio.toFixed(2)}</span>
                    </div>
                    <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem' }}>
                      <span className="stat-label">Max Drawdown</span>
                      <span className="stat-value" style={{ color: 'var(--color-red)' }}>
                        {formatPercent(detailedRun.max_drawdown)}
                      </span>
                    </div>
                    <div className="card stat-card" style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem' }}>
                      <span className="stat-label">Win Rate</span>
                      <span className="stat-value">{detailedRun.win_rate.toFixed(1)}%</span>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                    <div>
                      <p><strong>Strategy:</strong> {getStrategyNameById(detailedRun.strategy_id)}</p>
                      <p><strong>Stock Symbol:</strong> {detailedRun.execute_on}</p>
                      <p><strong>Execution Time:</strong> {new Date(detailedRun.run_at).toLocaleString()}</p>
                    </div>
                    <div>
                      <p><strong>Start Date:</strong> {detailedRun.start_date}</p>
                      <p><strong>End Date:</strong> {detailedRun.end_date}</p>
                      <p><strong>Initial Capital:</strong> {formatCurrency(detailedRun.initial_capital)}</p>
                    </div>
                  </div>

                  <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Equity Curve Performance Chart</h4>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)', marginBottom: '1.5rem' }}>
                    <EquityChart 
                      equityCurve={detailedRun.equity_curve} 
                      benchmarkCurve={detailedRun.benchmark_curve || []}
                      tradeLog={detailedRun.trade_log} 
                    />
                  </div>

                  <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Trade Action Log ({detailedRun.trade_log.length})</h4>
                  <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                    <table className="glass-table" style={{ fontSize: '0.85rem' }}>
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Type</th>
                          <th>Price</th>
                          <th>Shares</th>
                          <th>Cost</th>
                          <th>Cash After</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detailedRun.trade_log.map((trade, idx) => (
                          <tr key={idx}>
                            <td>{trade.date}</td>
                            <td style={{ fontWeight: '600', color: trade.type === 'buy' || trade.type === 'cover' ? 'var(--color-green)' : 'var(--color-red)' }}>
                              {trade.type.toUpperCase()}
                            </td>
                            <td>{formatCurrency(trade.price)}</td>
                            <td>{trade.shares.toFixed(2)}</td>
                            <td>{formatCurrency(trade.cost || 0)}</td>
                            <td>{formatCurrency(trade.cash_after)}</td>
                            <td>{trade.reason.toUpperCase()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
