import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { SupportedType, UploadResponse } from '../api/client';

export default function Upload() {
  const [types, setTypes] = useState<SupportedType[]>([]);
  const [sourceType, setSourceType] = useState('');
  const [persist, setPersist] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.supportedTypes().then((r) => setTypes(r.types)).catch(() => {});
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.uploadFile(file, sourceType || undefined, persist);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }, [sourceType, persist]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div>
      <div className="page-header">
        <h1>Upload & Extract</h1>
        <p>Test data extraction on sample files — preview mode by default</p>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <label>
            Source type (optional — auto-detected):
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              style={{ marginLeft: '0.5rem', padding: '0.5rem', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            >
              <option value="">Auto-detect</option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.label} ({t.extensions.join(', ')})</option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input type="checkbox" checked={persist} onChange={(e) => setPersist(e.target.checked)} />
            Save to database (persist)
          </label>
        </div>
      </div>

      <div
        className={`upload-zone ${dragging ? 'dragover' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        {loading ? (
          <p>Processing file...</p>
        ) : (
          <>
            <p style={{ fontSize: '1.1rem', margin: '0 0 0.5rem' }}>
              Drop a file here or click to browse
            </p>
            <p style={{ color: '#64748b', margin: 0, fontSize: '0.9rem' }}>
              WhatsApp (.txt) · Contacts (.vcf, .csv) · Email (.eml, .mbox) · Invoices (.pdf)
            </p>
          </>
        )}
      </div>

      {error && <div className="error-banner" style={{ marginTop: '1rem' }}>{error}</div>}

      {result && (
        <div className="extraction-preview">
          <div className={result.status.includes('failed') ? 'error-banner' : 'success-banner'}>
            <strong>{result.filename}</strong> — {result.source_type} — Status: {result.status}
          </div>

          {result.extraction?.errors && result.extraction.errors.length > 0 && (
            <div className="error-banner">
              <strong>Warnings:</strong>
              <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
                {result.extraction.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="card">
            <h3 style={{ marginTop: 0 }}>Extracted Data</h3>
            <pre>{JSON.stringify(result.extraction?.extracted ?? {}, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
