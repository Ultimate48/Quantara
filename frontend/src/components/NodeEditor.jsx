import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';

/**
 * NodeEditor — Simplified node-based visual strategy editor.
 * Drag nodes from palette → canvas, connect ports, configure parameters,
 * then compile the graph into columns[] + signal_rule.
 */

// ——— Node Type Definitions ———
const NODE_TYPES = {
  // Source nodes — output raw price data
  close:   { category: 'source', label: 'Close',   outputs: ['out'], inputs: [], params: [] },
  high:    { category: 'source', label: 'High',    outputs: ['out'], inputs: [], params: [] },
  low:     { category: 'source', label: 'Low',     outputs: ['out'], inputs: [], params: [] },
  open:    { category: 'source', label: 'Open',    outputs: ['out'], inputs: [], params: [] },
  volume:  { category: 'source', label: 'Volume',  outputs: ['out'], inputs: [], params: [] },
  constant:{ category: 'source', label: 'Constant',outputs: ['out'], inputs: [], params: [{ key: 'value', label: 'Value', default: '0' }] },

  // Operation nodes — transform data
  rolling_mean: { category: 'operation', label: 'Rolling Mean (SMA)', outputs: ['out'], inputs: ['in'],  params: [{ key: 'period', label: 'Period', default: '20' }] },
  ewm_mean:     { category: 'operation', label: 'EWM Mean (EMA)',    outputs: ['out'], inputs: ['in'],  params: [{ key: 'span', label: 'Span', default: '12' }] },
  diff:         { category: 'operation', label: 'Diff',              outputs: ['out'], inputs: ['in'],  params: [] },
  shift:        { category: 'operation', label: 'Shift',             outputs: ['out'], inputs: ['in'],  params: [{ key: 'periods', label: 'Periods', default: '1' }] },
  abs:          { category: 'operation', label: 'Abs',               outputs: ['out'], inputs: ['in'],  params: [] },
  rolling_std:  { category: 'operation', label: 'Rolling Std',       outputs: ['out'], inputs: ['in'],  params: [{ key: 'period', label: 'Period', default: '20' }] },
  add:          { category: 'operation', label: 'Add (+)',           outputs: ['out'], inputs: ['a', 'b'], params: [] },
  subtract:     { category: 'operation', label: 'Subtract (−)',     outputs: ['out'], inputs: ['a', 'b'], params: [] },
  multiply:     { category: 'operation', label: 'Multiply (×)',     outputs: ['out'], inputs: ['a', 'b'], params: [] },
  divide:       { category: 'operation', label: 'Divide (÷)',       outputs: ['out'], inputs: ['a', 'b'], params: [] },

  // Output nodes — named column output
  column_output: { category: 'output', label: 'Column Output', outputs: [], inputs: ['in'], params: [{ key: 'name', label: 'Name', default: 'my_col' }] },

  // Condition nodes — comparison
  compare: { category: 'condition', label: 'Compare', outputs: ['out'], inputs: ['left', 'right'], params: [{ key: 'op', label: 'Op', default: '>' }] },

  // Signal node — final output
  signal_out: { category: 'signal', label: 'Signal Output', outputs: [], inputs: ['buy_cond', 'sell_cond'], params: [] },
};

const PALETTE_GROUPS = [
  { label: 'Sources', category: 'source', types: ['close', 'high', 'low', 'open', 'volume', 'constant'] },
  { label: 'Operations', category: 'operation', types: ['rolling_mean', 'ewm_mean', 'diff', 'shift', 'abs', 'rolling_std', 'add', 'subtract', 'multiply', 'divide'] },
  { label: 'Outputs', category: 'output', types: ['column_output'] },
  { label: 'Logic', category: 'condition', types: ['compare'] },
  { label: 'Signal', category: 'signal', types: ['signal_out'] },
];

let nextNodeId = 1;

export default function NodeEditor({ stratCols, setStratCols, stratSignal, setStratSignal, showToast }) {
  const [nodes, setNodes] = useState([]);
  const [connections, setConnections] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [draggingNode, setDraggingNode] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [connecting, setConnecting] = useState(null); // { nodeId, portName, portType: 'output' }
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const canvasRef = useRef(null);

  // ——— Node CRUD ———

  const addNode = (typeName, x, y) => {
    const typeDef = NODE_TYPES[typeName];
    if (!typeDef) return;
    const paramValues = {};
    typeDef.params.forEach(p => { paramValues[p.key] = p.default; });
    const newNode = {
      id: `node_${nextNodeId++}`,
      type: typeName,
      x, y,
      params: paramValues,
    };
    setNodes(prev => [...prev, newNode]);
  };

  const deleteNode = (nodeId) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId));
    setConnections(prev => prev.filter(c => c.from.nodeId !== nodeId && c.to.nodeId !== nodeId));
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
  };

  const updateNodeParam = (nodeId, key, value) => {
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, params: { ...n.params, [key]: value } } : n));
  };

  // ——— Drag Nodes ———

  const handleNodeMouseDown = (e, nodeId) => {
    if (e.target.closest('.node-port') || e.target.closest('.node-delete') || e.target.closest('.node-param-input')) return;
    e.preventDefault();
    const node = nodes.find(n => n.id === nodeId);
    const rect = canvasRef.current.getBoundingClientRect();
    setDraggingNode(nodeId);
    setDragOffset({ x: e.clientX - rect.left - node.x, y: e.clientY - rect.top - node.y });
    setSelectedNodeId(nodeId);
  };

  const handleCanvasMouseMove = useCallback((e) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const rawX = e.clientX - rect.left;
    const rawY = e.clientY - rect.top;
    
    setMousePos({ x: rawX, y: rawY });
    
    if (draggingNode) {
      const x = Math.max(0, rawX - dragOffset.x);
      const y = Math.max(0, rawY - dragOffset.y);
      setNodes(prev => prev.map(n => n.id === draggingNode ? { ...n, x, y } : n));
    }
  }, [draggingNode, dragOffset]);

  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNode(null);
    setConnecting(null);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleCanvasMouseMove);
    window.addEventListener('mouseup', handleCanvasMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleCanvasMouseMove);
      window.removeEventListener('mouseup', handleCanvasMouseUp);
    };
  }, [handleCanvasMouseMove, handleCanvasMouseUp]);

  // ——— Port Connections ———

  const handlePortClick = (nodeId, portName, portType) => {
    if (!connecting) {
      setConnecting({ nodeId, portName, portType });
      return;
    }

    // Complete the connection
    let fromNode, toNode;
    if (connecting.portType === 'output' && portType === 'input') {
      fromNode = { nodeId: connecting.nodeId, port: connecting.portName };
      toNode = { nodeId, port: portName };
    } else if (connecting.portType === 'input' && portType === 'output') {
      fromNode = { nodeId, port: portName };
      toNode = { nodeId: connecting.nodeId, port: connecting.portName };
    } else {
      // invalid connection (e.g., output to output)
      setConnecting(null);
      return;
    }

    // Check same node
    if (fromNode.nodeId === toNode.nodeId) {
      setConnecting(null);
      return;
    }

    // Check for duplicate
    const exists = connections.some(c =>
      c.from.nodeId === fromNode.nodeId && c.from.port === fromNode.port &&
      c.to.nodeId === toNode.nodeId && c.to.port === toNode.port
    );
    
    if (!exists) {
      // Remove any existing connection to this input port
      setConnections(prev => [
        ...prev.filter(c => !(c.to.nodeId === toNode.nodeId && c.to.port === toNode.port)),
        { from: fromNode, to: toNode },
      ]);
      // (Optional) you can add a short subtle sound or leave this out to avoid spam,
      // but showing a tiny log helps debug if the state actually committed.
    }
    setConnecting(null);
  };

  // ——— Drop from Palette ———

  const handlePaletteDragStart = (e, typeName) => {
    e.dataTransfer.setData('nodeType', typeName);
  };

  const handleCanvasDrop = (e) => {
    e.preventDefault();
    const typeName = e.dataTransfer.getData('nodeType');
    if (!typeName) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - 60;
    const y = e.clientY - rect.top - 20;
    addNode(typeName, Math.max(0, x), Math.max(0, y));
  };

  const handleCanvasDragOver = (e) => {
    e.preventDefault();
  };

  // ——— Render Connections (SVG) ———

  const getPortPosition = useCallback((nodeId, portName, portType) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    const typeDef = NODE_TYPES[node.type];
    if (!typeDef) return { x: 0, y: 0 };

    // Node layout constants matching CSS
    const nodeWidth = 150; // min-width of .editor-node + some padding
    let height = 32; // node-header
    if (typeDef.params.length > 0) {
      height += 16 + typeDef.params.length * 28; // node-body padding + params
    }
    height += 15; // middle of node-ports container

    const y = node.y + height;
    
    // x positions: padding is 0.7rem (11px). Gap is 0.75rem (12px).
    // Port width is 12px.
    if (portType === 'output' || typeDef.outputs.includes(portName)) {
      const idx = typeDef.outputs.indexOf(portName);
      // Outputs are right-aligned
      const totalOutputs = typeDef.outputs.length;
      const x = node.x + nodeWidth - 11 - 6 - (totalOutputs - 1 - idx) * 24;
      return { x, y };
    } else {
      const idx = typeDef.inputs.indexOf(portName);
      // Inputs are left-aligned
      const x = node.x + 11 + 6 + idx * 24;
      return { x, y };
    }
  }, [nodes]);

  // ——— Compile Graph to Columns + Signal ———

  const compileGraph = () => {
    try {
      // Topologically sort and generate formulas
      const nodeMap = {};
      nodes.forEach(n => { nodeMap[n.id] = n; });

      // Build adjacency: for each node, what feeds into each input port
      const inputSources = {}; // { nodeId: { portName: sourceExpression } }
      nodes.forEach(n => { inputSources[n.id] = {}; });

      // Resolve a node's output expression
      const resolved = {};

      const resolve = (nodeId) => {
        if (resolved[nodeId]) return resolved[nodeId];
        const node = nodeMap[nodeId];
        if (!node) return null;
        const typeDef = NODE_TYPES[node.type];

        // Get input expressions
        const inputs = {};
        typeDef.inputs.forEach(inputPort => {
          const conn = connections.find(c => c.to.nodeId === nodeId && c.to.port === inputPort);
          if (conn) {
            inputs[inputPort] = resolve(conn.from.nodeId);
          }
        });

        let expr = null;
        switch (node.type) {
          case 'close': case 'high': case 'low': case 'open': case 'volume':
            expr = node.type;
            break;
          case 'constant':
            expr = node.params.value || '0';
            break;
          case 'rolling_mean':
            if (inputs.in) expr = `${inputs.in}.rolling(${node.params.period}).mean()`;
            break;
          case 'ewm_mean':
            if (inputs.in) expr = `${inputs.in}.ewm(span=${node.params.span}, adjust=False).mean()`;
            break;
          case 'rolling_std':
            if (inputs.in) expr = `${inputs.in}.rolling(${node.params.period}).std()`;
            break;
          case 'diff':
            if (inputs.in) expr = `${inputs.in}.diff()`;
            break;
          case 'shift':
            if (inputs.in) expr = `${inputs.in}.shift(${node.params.periods})`;
            break;
          case 'abs':
            if (inputs.in) expr = `(${inputs.in}).abs()`;
            break;
          case 'add':
            if (inputs.a && inputs.b) expr = `${inputs.a} + ${inputs.b}`;
            break;
          case 'subtract':
            if (inputs.a && inputs.b) expr = `${inputs.a} - ${inputs.b}`;
            break;
          case 'multiply':
            if (inputs.a && inputs.b) expr = `${inputs.a} * ${inputs.b}`;
            break;
          case 'divide':
            if (inputs.a && inputs.b) expr = `${inputs.a} / ${inputs.b}`;
            break;
          default:
            break;
        }

        resolved[nodeId] = expr;
        return expr;
      };

      // Collect column outputs
      const columns = [];
      const columnOutputNodes = nodes.filter(n => n.type === 'column_output');
      columnOutputNodes.forEach(node => {
        const conn = connections.find(c => c.to.nodeId === node.id && c.to.port === 'in');
        if (conn) {
          const formula = resolve(conn.from.nodeId);
          if (formula) {
            columns.push({ name: node.params.name || 'unnamed', formula });
          }
        }
      });

      // Collect signal output
      const signalNodes = nodes.filter(n => n.type === 'signal_out');
      let signalRule = 'True : 0';
      if (signalNodes.length > 0) {
        const sigNode = signalNodes[0];
        const parts = [];

        // buy_cond input
        const buyConn = connections.find(c => c.to.nodeId === sigNode.id && c.to.port === 'buy_cond');
        if (buyConn) {
          const buyNode = nodeMap[buyConn.from.nodeId];
          if (buyNode && buyNode.type === 'compare') {
            const leftConn = connections.find(c => c.to.nodeId === buyNode.id && c.to.port === 'left');
            const rightConn = connections.find(c => c.to.nodeId === buyNode.id && c.to.port === 'right');
            const leftExpr = leftConn ? resolve(leftConn.from.nodeId) : '0';
            const rightExpr = rightConn ? resolve(rightConn.from.nodeId) : '0';
            // Use column name if output exists
            const leftName = findColumnName(leftExpr, columns) || leftExpr;
            const rightName = findColumnName(rightExpr, columns) || rightExpr;
            parts.push(`${leftName} ${buyNode.params.op || '>'} ${rightName} : 1`);
          }
        }

        // sell_cond input
        const sellConn = connections.find(c => c.to.nodeId === sigNode.id && c.to.port === 'sell_cond');
        if (sellConn) {
          const sellNode = nodeMap[sellConn.from.nodeId];
          if (sellNode && sellNode.type === 'compare') {
            const leftConn = connections.find(c => c.to.nodeId === sellNode.id && c.to.port === 'left');
            const rightConn = connections.find(c => c.to.nodeId === sellNode.id && c.to.port === 'right');
            const leftExpr = leftConn ? resolve(leftConn.from.nodeId) : '0';
            const rightExpr = rightConn ? resolve(rightConn.from.nodeId) : '0';
            const leftName = findColumnName(leftExpr, columns) || leftExpr;
            const rightName = findColumnName(rightExpr, columns) || rightExpr;
            parts.push(`${leftName} ${sellNode.params.op || '<'} ${rightName} : -1`);
          }
        }

        parts.push('True : 0');
        signalRule = parts.join(', ');
      }

      if (columns.length === 0) {
        showToast('No Column Output nodes found. Add at least one to generate columns.', 'error');
        return;
      }

      setStratCols(columns);
      setStratSignal(signalRule);
      showToast(`Compiled ${columns.length} column(s) from node graph.`, 'success');
    } catch (err) {
      showToast(`Compile error: ${err.message}`, 'error');
    }
  };

  const clearCanvas = () => {
    setNodes([]);
    setConnections([]);
    setSelectedNodeId(null);
    nextNodeId = 1;
  };

  return (
    <div className="mode-panel">
      <div className="node-editor-container">
        {/* Palette */}
        <div className="node-palette">
          <div className="node-palette-title">Node Palette</div>
          {PALETTE_GROUPS.map(group => (
            <div key={group.label} className="node-palette-group">
              <div className="node-palette-group-label">{group.label}</div>
              {group.types.map(typeName => (
                <div
                  key={typeName}
                  className={`palette-node ${group.category}`}
                  draggable
                  onDragStart={(e) => handlePaletteDragStart(e, typeName)}
                >
                  {NODE_TYPES[typeName].label}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          className="node-canvas"
          onDrop={handleCanvasDrop}
          onDragOver={handleCanvasDragOver}
          onClick={() => setSelectedNodeId(null)}
        >
          {/* SVG Connection Lines */}
          <svg className="node-connections-svg">
            {connections.map((conn, i) => {
              const from = getPortPosition(conn.from.nodeId, conn.from.port, 'output');
              const to = getPortPosition(conn.to.nodeId, conn.to.port, 'input');
              const dx = Math.abs(to.x - from.x) * 0.5;
              const d = `M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${to.x - dx} ${to.y}, ${to.x} ${to.y}`;
              return <path key={i} className="node-connection-path" d={d} />;
            })}
            
            {/* Active Connecting Line */}
            {connecting && (
              <path 
                className="node-connection-path" 
                style={{ stroke: 'var(--accent-cyan)', strokeDasharray: '5,5' }}
                d={`M ${getPortPosition(connecting.nodeId, connecting.portName, connecting.portType).x} ${getPortPosition(connecting.nodeId, connecting.portName, connecting.portType).y} 
                    C ${getPortPosition(connecting.nodeId, connecting.portName, connecting.portType).x + 50} ${getPortPosition(connecting.nodeId, connecting.portName, connecting.portType).y}, 
                      ${mousePos.x - 50} ${mousePos.y}, 
                      ${mousePos.x} ${mousePos.y}`} 
              />
            )}
          </svg>

          {/* Node Cards */}
          {nodes.map(node => {
            const typeDef = NODE_TYPES[node.type];
            if (!typeDef) return null;
            return (
              <div
                key={node.id}
                className={`editor-node ${typeDef.category} ${selectedNodeId === node.id ? 'selected' : ''}`}
                style={{ left: node.x, top: node.y }}
                onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                onClick={(e) => { e.stopPropagation(); setSelectedNodeId(node.id); }}
              >
                <div className="node-header">
                  <span className="node-title">{typeDef.label}</span>
                  <button className="node-delete" onClick={(e) => { e.stopPropagation(); deleteNode(node.id); }}>✕</button>
                </div>

                {typeDef.params.length > 0 && (
                  <div className="node-body">
                    {typeDef.params.map(p => (
                      <div key={p.key} className="node-param">
                        <span className="node-param-label">{p.label}</span>
                        {p.key === 'op' ? (
                          <select
                            className="node-param-input"
                            style={{ width: '50px' }}
                            value={node.params[p.key] || p.default}
                            onChange={(e) => { e.stopPropagation(); updateNodeParam(node.id, p.key, e.target.value); }}
                            onMouseDown={(e) => e.stopPropagation()}
                          >
                            <option value=">">{'>'}</option>
                            <option value="<">{'<'}</option>
                            <option value=">=">{'>='}</option>
                            <option value="<=">{'<='}</option>
                            <option value="==">{'=='}</option>
                          </select>
                        ) : (
                          <input
                            className="node-param-input"
                            value={node.params[p.key] || ''}
                            onChange={(e) => updateNodeParam(node.id, p.key, e.target.value)}
                            onMouseDown={(e) => e.stopPropagation()}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Ports */}
                <div className="node-ports">
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    {typeDef.inputs.map(portName => (
                      <div key={portName} style={{ textAlign: 'center' }}>
                        <div
                          className="node-port input"
                          onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, portName, 'input'); }}
                          title={`Input: ${portName}`}
                          style={connecting ? { borderColor: 'var(--accent-cyan)', animation: 'pulse 1s infinite' } : {}}
                        />
                        <div className="node-port-label">{portName}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    {typeDef.outputs.map(portName => (
                      <div key={portName} style={{ textAlign: 'center' }}>
                        <div
                          className="node-port output"
                          onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, portName, 'output'); }}
                          title={`Output: ${portName}`}
                          style={connecting && connecting.nodeId === node.id ? { borderColor: 'var(--color-green)', background: 'var(--color-green)' } : {}}
                        />
                        <div className="node-port-label">{portName}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Empty State */}
          {nodes.length === 0 && (
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center', color: 'var(--color-text-dim)',
              pointerEvents: 'none',
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔗</div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Drag nodes from the palette</div>
              <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                Connect output ports → input ports, then click Compile
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <div className="node-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ color: 'var(--color-text-dim)', fontSize: '0.8rem' }}>
          Nodes: {nodes.length} | Connections: {connections.length}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn" onClick={clearCanvas} style={{ fontSize: '0.85rem' }}>
            Clear Canvas
          </button>
          <button type="button" className="btn btn-primary" onClick={compileGraph} style={{ fontSize: '0.85rem' }}>
            ⚡ Compile to Strategy
          </button>
        </div>
      </div>
    </div>
  );
}

/** Helper: find if an expression matches a generated column's formula, return the column name */
function findColumnName(expr, columns) {
  if (!expr) return null;
  const match = columns.find(c => c.formula === expr);
  return match ? match.name : null;
}
