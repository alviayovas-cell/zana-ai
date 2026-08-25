import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ChatResponse, BrainStatusResponse } from '../types/chat';
import './AiBrainPanel.css';

interface Props {
  onSendMessage: (text: string) => void;
}

const SAMPLE_COMMANDS = [
  'Play Believer',
  'Play relaxing music',
  'Next song',
  'Set volume to 50',
  "What's playing?",
  'Play Arijit Singh',
  'Who is Zana?',
];

export const AiBrainPanel: React.FC<Props> = ({ onSendMessage }) => {
  const [status, setStatus] = useState<BrainStatusResponse | null>(null);
  const [testInput, setTestInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastTelemetry, setLastTelemetry] = useState<ChatResponse | null>(null);
  const [executionTimeMs, setExecutionTimeMs] = useState<number | null>(null);

  // Load live AI Brain status on mount
  useEffect(() => {
    api.getBrainStatus()
      .then((res) => setStatus(res))
      .catch((err) => console.error('[AI-BRAIN] Status load error:', err));
  }, []);

  const handleRunTest = async (cmdToRun?: string) => {
    const query = (cmdToRun || testInput).trim();
    if (!query || isLoading) return;

    setIsLoading(true);
    setTestInput(query);
    const start = performance.now();

    try {
      // 1. Run live test through AI Brain test endpoint (to capture diagnostic telemetry)
      const res = await api.testBrain(query, 'dev-brain-panel');
      const elapsed = Math.round(performance.now() - start);
      setExecutionTimeMs(elapsed);
      setLastTelemetry(res);

      // 2. Also send message through main chat pipeline so audio plays / player responds!
      onSendMessage(query);
    } catch (err: any) {
      console.error('[AI-BRAIN] Test execution error:', err);
      setLastTelemetry({
        message: err.message || 'Execution error',
        status: 'error',
        timestamp: new Date().toISOString(),
        execution_status: 'failed',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="brain-panel-container" id="brain-panel">
      {/* Header */}
      <header className="brain-header">
        <div className="brain-header-title-group">
          <div className="brain-logo-icon">🧠</div>
          <div className="brain-title-text">
            <h2>Zana AI Brain</h2>
            <p>{status?.architecture || 'Phase 4 Intelligence & Orchestration Layer'}</p>
          </div>
        </div>
        <div className="brain-status-pill">
          <span className="brain-status-dot" />
          Status: ● Active
        </div>
      </header>

      {/* Modules Status Grid */}
      <div className="brain-modules-grid">
        <div className="module-card">
          <div className="module-info">
            <span className="module-icon">🎯</span>
            <span className="module-name">Intent Detection</span>
          </div>
          <span className="module-badge">✓ Active</span>
        </div>

        <div className="module-card">
          <div className="module-info">
            <span className="module-icon">💬</span>
            <span className="module-name">Context Awareness</span>
          </div>
          <span className="module-badge">✓ Active</span>
        </div>

        <div className="module-card">
          <div className="module-info">
            <span className="module-icon">🧠</span>
            <span className="module-name">Short/Long Memory</span>
          </div>
          <span className="module-badge">✓ Active</span>
        </div>

        <div className="module-card">
          <div className="module-info">
            <span className="module-icon">🔀</span>
            <span className="module-name">Tool Routing</span>
          </div>
          <span className="module-badge">✓ Active</span>
        </div>

        <div className="module-card">
          <div className="module-info">
            <span className="module-icon">📋</span>
            <span className="module-name">Task Planning</span>
          </div>
          <span className="module-badge">✓ Active</span>
        </div>
      </div>

      {/* Development & Live Test Interface */}
      <section className="brain-test-section">
        <h3 className="section-title">
          <span>⚡</span> AI Brain Live Test & Telemetry
        </h3>

        {/* Sample chips */}
        <div className="quick-chips">
          {SAMPLE_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              className="chip-btn"
              onClick={() => handleRunTest(cmd)}
              disabled={isLoading}
            >
              {cmd}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="test-input-row">
          <input
            type="text"
            className="test-input"
            placeholder='Type command to test AI Brain (e.g. "Play Believer", "Next song")'
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRunTest()}
            disabled={isLoading}
          />
          <button
            className="test-btn"
            onClick={() => handleRunTest()}
            disabled={isLoading || !testInput.trim()}
          >
            {isLoading ? 'Processing…' : 'Execute Test'}
          </button>
        </div>

        {/* Live Diagnostic Telemetry Output Box */}
        {lastTelemetry && (
          <div className="telemetry-box">
            <div className="telemetry-grid">
              <div className="telemetry-item">
                <div className="telemetry-label">Input</div>
                <div className="telemetry-value">{testInput || '—'}</div>
              </div>

              <div className="telemetry-item">
                <div className="telemetry-label">Intent Detected</div>
                <div className="telemetry-value">
                  {lastTelemetry.intent || 'GENERAL_CONVERSATION'}
                </div>
              </div>

              <div className="telemetry-item">
                <div className="telemetry-label">Confidence</div>
                <div className="telemetry-value">
                  {lastTelemetry.confidence !== undefined && lastTelemetry.confidence !== null
                    ? `${(lastTelemetry.confidence * 100).toFixed(0)}%`
                    : '100%'}
                </div>
              </div>

              <div className="telemetry-item">
                <div className="telemetry-label">Tool Selected</div>
                <div className="telemetry-value">
                  {lastTelemetry.tool || 'chat_response'}
                </div>
              </div>

              <div className="telemetry-item">
                <div className="telemetry-label">Arguments</div>
                <div className="telemetry-value">
                  {lastTelemetry.arguments
                    ? JSON.stringify(lastTelemetry.arguments)
                    : '{}'}
                </div>
              </div>

              <div className="telemetry-item">
                <div className="telemetry-label">Execution Status</div>
                <div className={`telemetry-value ${lastTelemetry.status === 'error' ? 'failed' : 'success'}`}>
                  {lastTelemetry.execution_status || lastTelemetry.status || 'success'}
                  {executionTimeMs !== null ? ` (${executionTimeMs}ms)` : ''}
                </div>
              </div>
            </div>

            <div className="telemetry-result-msg">
              <strong>Zana Output:</strong> {lastTelemetry.message}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
