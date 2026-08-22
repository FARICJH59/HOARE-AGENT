'use client';

import { useState } from 'react';

export default function OrchestratePage() {
  const [intent, setIntent] = useState('');
  const [submitted, setSubmitted] = useState(false);

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h1>HOARE Orchestration</h1>
      <p>Phase 31 intent-to-orchestration boundary.</p>
      <textarea
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        placeholder="Describe the workload or change you want HOARE to plan."
        rows={8}
        style={{ width: '100%', padding: 12 }}
      />
      <button
        type="button"
        onClick={() => setSubmitted(Boolean(intent.trim()))}
        style={{ marginTop: 12, padding: '10px 16px' }}
      >
        Compile Intent
      </button>
      {submitted && <p role="status">Intent accepted for Phase 31 planning.</p>}
    </main>
  );
}
