import React from 'react';
import './ProfileModal.css';

interface Props {
  isOpen: boolean;
  prompt: string;
  toolName: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const PermissionModal: React.FC<Props> = ({
  isOpen,
  prompt,
  toolName,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="modal-header">
          <h3>⚠️ Confirmation Required</h3>
        </div>
        <div className="modal-body">
          <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.5' }}>
            {prompt || `Are you sure you want to execute action '${toolName}'?`}
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn-primary" style={{ background: '#ef4444' }} onClick={onConfirm}>
            Yes, Confirm
          </button>
        </div>
      </div>
    </div>
  );
};
