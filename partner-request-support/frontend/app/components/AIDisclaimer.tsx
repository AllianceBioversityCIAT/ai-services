'use client';

export const AIDisclaimer = () => {
  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #FFFBF0 0%, #FFF9E6 100%)',
        border: '1px solid #FFE8A3',
        borderLeft: '4px solid var(--cgiar-yellow)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-sm) var(--space-md)',
        marginBottom: 'var(--space-lg)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-sm)',
      }}
    >
      <span style={{ fontSize: '1.25rem' }}>🤖</span>
      <p
        style={{
          fontSize: '0.73rem',
          color: 'var(--cgiar-navy)',
          lineHeight: 1.5,
          margin: 0,
        }}
      >
        <strong>AI-Powered Analysis:</strong> This tool uses artificial intelligence to match
        partner institutions with CGIAR's database and perform web verification. Results are
        automated suggestions that may require human validation.
      </p>
    </div>
  );
};
