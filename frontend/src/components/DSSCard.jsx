import React, { useState } from 'react';

export function DSSBadge({ level }) {
  const lvl = String(level || 'LOW').toUpperCase();
  const colors = {
    LOW: { bg: '#e6f4ea', text: '#137333', border: '#ceead6' },
    MODERATE: { bg: '#fef7e0', text: '#b06000', border: '#feefc3' },
    HIGH: { bg: '#feefe3', text: '#c5221f', border: '#fad2cf' },
    CRITICAL: { bg: '#fce8e6', text: '#a50e0e', border: '#f5c2c7' },
  };
  const conf = colors[lvl] || colors.LOW;

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: 'bold',
      backgroundColor: conf.bg,
      color: conf.text,
      border: `1px solid ${conf.border}`,
      letterSpacing: '0.5px'
    }}>
      ● {lvl}
    </span>
  );
}

export function DSSCard({ 
  assessment, 
  recommendation, 
  onAction, 
  onAskAi, 
  userRole = 'field_officer',
  title = "AI Role-Based Decision Support"
}) {
  const [notes, setNotes] = useState("");
  const [modifying, setModifying] = useState(false);
  const [actionDone, setActionDone] = useState(null);

  if (!assessment) return null;

  const score = assessment.priority_score ?? assessment.risk_score ?? 0;
  const level = assessment.risk_level || 'LOW';
  const reasons = assessment.reasons || [];
  const recText = recommendation?.recommendation || "Review record parameters.";
  const suggested = recommendation?.suggested_actions || [];

  const handleDecision = async (act) => {
    if (act === 'modify' && !modifying) {
      setModifying(true);
      return;
    }
    if (onAction) {
      const res = await onAction(act, notes);
      setActionDone({ action: act, message: res?.message || `Recommendation ${act}ed.` });
      setModifying(false);
    }
  };

  return (
    <div style={{
      border: '1px solid #dcdcdc',
      borderRadius: '8px',
      padding: '16px',
      backgroundColor: '#ffffff',
      boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      marginTop: '16px',
      marginBottom: '16px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '8px', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>🤖</span>
          <h4 style={{ margin: 0, fontSize: '15px', color: '#1a73e8' }}>{title}</h4>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 'bold' }}>Score: {score}/100</span>
          <DSSBadge level={level} />
        </div>
      </div>

      {/* AI Recommendation Banner */}
      <div style={{
        backgroundColor: '#f8f9fa',
        borderLeft: '4px solid #1a73e8',
        padding: '10px 12px',
        marginBottom: '12px',
        borderRadius: '0 4px 4px 0'
      }}>
        <div style={{ fontSize: '11px', color: '#5f6368', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px' }}>
          AI Recommendation (Human Authorization Required)
        </div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#202124', marginTop: '2px' }}>
          {recText}
        </div>
      </div>

      {/* Evidence & Key Factors */}
      {reasons.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#3c4043', marginBottom: '4px' }}>
            Supporting Evidence & Triggers:
          </div>
          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#5f6368' }}>
            {reasons.slice(0, 4).map((r, i) => (
              <li key={i} style={{ marginBottom: '2px' }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggested Next Steps */}
      {suggested.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#3c4043', marginBottom: '4px' }}>
            Actionable Next Steps:
          </div>
          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#137333' }}>
            {suggested.map((s, i) => (
              <li key={i} style={{ marginBottom: '2px' }}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Modify notes input */}
      {modifying && (
        <div style={{ marginTop: '8px', marginBottom: '12px' }}>
          <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#555' }}>Officer Notes / Custom Instruction:</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Specify reason for modification or override..."
            style={{ width: '100%', height: '50px', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid #ccc', marginTop: '4px' }}
          />
        </div>
      )}

      {/* Action Notification */}
      {actionDone && (
        <div style={{
          backgroundColor: '#e6f4ea',
          color: '#137333',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '12px',
          marginBottom: '10px',
          fontWeight: 500
        }}>
          ✓ {actionDone.message}
        </div>
      )}

      {/* Human In The Loop Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', borderTop: '1px solid #eee', paddingTop: '10px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!actionDone ? (
            <>
              <button
                onClick={() => handleDecision('accept')}
                style={{ backgroundColor: '#188038', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
              >
                ✓ Accept Recommendation
              </button>
              <button
                onClick={() => handleDecision('modify')}
                style={{ backgroundColor: '#f2994a', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
              >
                {modifying ? "Submit Modified Action" : "✎ Modify"}
              </button>
              <button
                onClick={() => handleDecision('reject')}
                style={{ backgroundColor: '#d93025', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
              >
                ✕ Reject
              </button>
            </>
          ) : (
            <span style={{ fontSize: '12px', color: '#666', fontStyle: 'italic' }}>Decision registered in audit trail.</span>
          )}
        </div>

        {onAskAi && (
          <button
            onClick={onAskAi}
            style={{ backgroundColor: '#f1f3f4', color: '#1a73e8', border: '1px solid #dadce0', padding: '6px 10px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
          >
            💬 Ask AI About This
          </button>
        )}
      </div>
    </div>
  );
}

export function AskAiModal({ isOpen, onClose, entityType, entityId, onAsk }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);

  if (!isOpen) return null;

  const safeEntityType = (entityType && typeof entityType === "string" ? entityType : "RECORD").toUpperCase();

  const quickQuestions = [
    "Why is this record high priority?",
    "What information is missing?",
    "Does this require on-site re-verification?",
    "Summarize this case"
  ];

  const handleQuery = async (q) => {
    const text = q || question;
    if (!text) return;
    setLoading(true);
    try {
      const res = await onAsk(entityType, entityId, text);
      setResponse(res);
    } catch (e) {
      setResponse({ summary: "Error retrieving explanation: " + e.message });
    }
    setLoading(false);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999
    }}>
      <div style={{
        backgroundColor: '#fff', borderRadius: '8px', width: '550px', maxHeight: '85vh', padding: '20px', display: 'flex', flexDirection: 'column', boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
          <h3 style={{ margin: 0, fontSize: '16px', color: '#1a73e8' }}>🤖 Ask AI About {safeEntityType} {entityId || ""}</h3>
          <button onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '18px', cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ marginTop: '12px', marginBottom: '8px' }}>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px', fontWeight: 600 }}>Quick Questions:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {quickQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => { setQuestion(q); handleQuery(q); }}
                style={{ fontSize: '11px', backgroundColor: '#f1f3f4', border: '1px solid #dadce0', borderRadius: '12px', padding: '4px 10px', cursor: 'pointer' }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type a question about this record..."
            style={{ flex: 1, padding: '8px', fontSize: '13px', borderRadius: '4px', border: '1px solid #ccc' }}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
          />
          <button
            onClick={() => handleQuery()}
            disabled={loading}
            style={{ backgroundColor: '#1a73e8', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: '4px', fontSize: '13px', cursor: 'pointer' }}
          >
            {loading ? "Analyzing..." : "Ask"}
          </button>
        </div>

        {response && (
          <div style={{
            marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #e8eaed', fontSize: '13px', lineHeight: '1.5', maxHeight: '250px', overflowY: 'auto'
          }}>
            <div style={{ fontWeight: 600, color: '#202124', marginBottom: '4px' }}>AI Explanation:</div>
            <p style={{ margin: 0, color: '#3c4043' }}>{response.summary}</p>
            {response.evidence && response.evidence.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: '11px', color: '#555' }}>Key Evidence:</span>
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', fontSize: '12px', color: '#555' }}>
                  {response.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
                </ul>
              </div>
            )}
            <div style={{ fontSize: '10px', color: '#888', marginTop: '8px', fontStyle: 'italic' }}>
              {response.disclaimer || "AI explains strictly verified parameters."}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
