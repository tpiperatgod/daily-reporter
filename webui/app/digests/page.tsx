export default function DigestsPage() {
  return (
    <div>
      <h1 style={{
        fontSize: 'var(--md-font-size-h2)',
        fontWeight: 'var(--md-font-weight-bold)',
        color: 'var(--md-color-text-primary)',
        marginBottom: 'var(--md-spacing-xl)'
      }}>
        Digests
      </h1>
      <div style={{
        padding: 'var(--md-spacing-xl)',
        backgroundColor: 'var(--md-color-surface)',
        border: 'var(--md-border-default) solid var(--md-color-border)',
        borderRadius: 'var(--md-radius-md)',
        boxShadow: 'var(--md-shadow-card)'
      }}>
        <p style={{
          fontSize: 'var(--md-font-size-body)',
          color: 'var(--md-color-text-secondary)'
        }}>
          Digest archive coming soon...
        </p>
      </div>
    </div>
  );
}
