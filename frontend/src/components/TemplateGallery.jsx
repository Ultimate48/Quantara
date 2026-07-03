import React from 'react';

/**
 * TemplateGallery — Displays pre-built strategy templates as a filterable card grid.
 * Users can browse by category and clone any template into the strategy builder.
 */

const CATEGORIES = ['All', 'Trend Following', 'Mean Reversion', 'Momentum', 'Volatility'];

const CATEGORY_CLASS_MAP = {
  'Trend Following': 'trend',
  'Mean Reversion': 'reversion',
  'Momentum': 'momentum',
  'Volatility': 'volatility',
};

export default function TemplateGallery({ templates, onUseTemplate, showToast }) {
  const [filter, setFilter] = React.useState('All');

  const filtered = filter === 'All'
    ? templates
    : templates.filter(t => t.category === filter);

  const handleUse = (template) => {
    onUseTemplate(template);
    showToast(`Template "${template.name}" loaded. Customize and save your strategy.`, 'success');
  };

  return (
    <div className="mode-panel">
      {/* Category Filter Pills */}
      <div className="template-filters">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`filter-pill ${filter === cat ? 'active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Template Cards Grid */}
      {filtered.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)' }}>No templates found for this category.</p>
      ) : (
        <div className="template-grid">
          {filtered.map(template => (
            <div key={template.id} className="template-card" onClick={() => handleUse(template)}>
              <div className="template-card-header">
                <span className="template-card-name">{template.name}</span>
                <span className={`category-badge ${CATEGORY_CLASS_MAP[template.category] || ''}`}>
                  {template.category}
                </span>
              </div>

              <p className="template-card-desc">{template.description}</p>

              <div className="template-card-tags">
                {template.tags.map(tag => (
                  <span key={tag} className="template-tag">{tag}</span>
                ))}
              </div>

              <div className="template-card-action">
                <button
                  className="btn btn-primary"
                  style={{ padding: '0.35rem 1rem', fontSize: '0.8rem' }}
                  onClick={(e) => { e.stopPropagation(); handleUse(template); }}
                >
                  Use Template
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
