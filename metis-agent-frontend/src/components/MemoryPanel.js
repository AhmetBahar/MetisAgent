import React from 'react';

const MemoryPanel = ({ isOpen, onClose, memories = [] }) => {
  return (
    <div className={`memory-panel ${isOpen ? 'open' : ''}`}>
      <div className="memory-header">
        <h2>Memory</h2>
        <button onClick={onClose}>×</button>
      </div>
      <div className="memory-content">
        {memories.length === 0 ? (
          <p>No memories stored yet.</p>
        ) : (
          <ul className="memory-list">
            {memories.map((memory, index) => (
              <li key={index} className="memory-item">
                {memory.content}
                <span className="memory-date">{memory.date}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default MemoryPanel;