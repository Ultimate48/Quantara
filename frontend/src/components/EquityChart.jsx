import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceDot
} from 'recharts';

export default function EquityChart({ equityCurve = [], benchmarkCurve = [], tradeLog = [] }) {
  // Merge data by date using memoization and O(N) lookups to prevent lag on re-renders
  const chartData = useMemo(() => {
    // Index benchmark by date for O(1) retrieval
    const benchmarkMap = {};
    if (Array.isArray(benchmarkCurve)) {
      benchmarkCurve.forEach(b => {
        if (b && b.date) {
          benchmarkMap[b.date] = b.value;
        }
      });
    }

    // Index trade log by date for O(1) retrieval
    const tradeMap = {};
    if (Array.isArray(tradeLog)) {
      tradeLog.forEach(t => {
        if (t && t.date) {
          if (!tradeMap[t.date]) {
            tradeMap[t.date] = [];
          }
          tradeMap[t.date].push(t);
        }
      });
    }

    return equityCurve.map(eq => {
      return {
        date: eq.date,
        strategy: eq.value,
        benchmark: benchmarkMap[eq.date] !== undefined ? benchmarkMap[eq.date] : null,
        trades: tradeMap[eq.date] || null
      };
    });
  }, [equityCurve, benchmarkCurve, tradeLog]);

  // Custom Dot Renderer to show Buy/Sell/Short/Cover markers on the Strategy Line
  const CustomDot = (props) => {
    const { cx, cy, payload } = props;
    if (!payload.trades) return null;
    
    // Determine primary trade type on this day
    const mainTrade = payload.trades[0];
    const type = mainTrade.type;
    
    let color = '#10b981'; // Green for Buy/Cover
    let symbol = '▲';
    let label = 'Buy';

    if (type === 'sell') {
      color = '#ef4444'; // Red for Sell
      symbol = '▼';
      label = 'Sell';
    } else if (type === 'short') {
      color = '#f97316'; // Orange for Short
      symbol = '▼';
      label = 'Short';
    } else if (type === 'cover') {
      color = '#eab308'; // Yellow for Cover
      symbol = '▲';
      label = 'Cover';
    }

    return (
      <g key={`dot-${payload.date}`}>
        <circle cx={cx} cy={cy} r={6} fill={color} stroke="#fff" strokeWidth={1} />
        <text 
          x={cx} 
          y={type === 'sell' || type === 'short' ? cy + 18 : cy - 10} 
          textAnchor="middle" 
          fill={color} 
          fontSize="10px" 
          fontWeight="bold"
          fontFamily="sans-serif"
        >
          {label}
        </text>
      </g>
    );
  };

  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div style={{
          background: 'rgba(16, 24, 40, 0.95)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          backdropFilter: 'blur(8px)'
        }}>
          <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#9ca3af', fontWeight: 'bold' }}>{label}</p>
          {payload.map((p, idx) => (
            <p key={idx} style={{ margin: '0.25rem 0', fontSize: '0.95rem', color: p.color }}>
              {p.name === 'strategy' ? 'Strategy' : 'Benchmark'}: <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{formatCurrency(p.value)}</span>
            </p>
          ))}
          {data.trades && (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.8rem', color: '#9ca3af', fontWeight: 600 }}>Trades executed:</p>
              {data.trades.map((t, idx) => {
                let color = '#10b981';
                if (t.type === 'sell') color = '#ef4444';
                if (t.type === 'short') color = '#f97316';
                if (t.type === 'cover') color = '#eab308';
                return (
                  <p key={idx} style={{ margin: '0.15rem 0', fontSize: '0.85rem', color }}>
                    {t.type.toUpperCase()} {t.shares.toFixed(1)} shrs @ {formatCurrency(t.price)}
                    {t.reason && t.reason !== 'signal' && ` (${t.reason})`}
                  </p>
                );
              })}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: '400px', margin: '1rem 0' }}>
      {chartData.length === 0 ? (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7280' }}>
          No equity data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
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
            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="top" height={36} />
            <Line 
              name="strategy"
              type="monotone" 
              dataKey="strategy" 
              stroke="#06b6d4" 
              strokeWidth={2.5} 
              dot={<CustomDot />}
              activeDot={{ r: 6, fill: '#06b6d4', stroke: '#fff', strokeWidth: 1 }}
            />
            {benchmarkCurve.length > 0 && (
              <Line 
                name="benchmark"
                type="monotone" 
                dataKey="benchmark" 
                stroke="#6b7280" 
                strokeDasharray="4 4"
                strokeWidth={1.5} 
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
