import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { CompanyListItem } from '../api/client';

export default function Dashboard() {
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState<'ok' | 'error'>('ok');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState('');

  const load = () => {
    api.listCompanies().then(setCompanies).catch(() => setCompanies([]));
  };

  useEffect(() => {
    Promise.all([
      api.health().then(() => setApiStatus('ok')).catch(() => setApiStatus('error')),
      api.listCompanies().then(setCompanies).catch(() => setCompanies([])),
    ]).finally(() => setLoading(false));
  }, []);

  const handleImport = async () => {
    setImporting(true);
    setImportResult('');
    try {
      const res = await api.importSamples();
      setImportResult(`Imported ${res.processed} files (${res.failed} failed)`);
      load();
    } catch (e) {
      setImportResult(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const totalRevenue = companies.reduce((sum, c) => sum + c.total_revenue, 0);
  const totalContacts = companies.reduce((sum, c) => sum + c.contact_count, 0);

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Customer intelligence overview — Phase 1 prototype</p>
      </div>

      {apiStatus === 'error' && (
        <div className="error-banner">
          Backend API is not reachable. Start services with <code>docker compose up</code>.
        </div>
      )}

      <div className="card-grid">
        <div className="stat-card">
          <div className="label">Companies</div>
          <div className="value">{loading ? '—' : companies.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Contacts</div>
          <div className="value">{loading ? '—' : totalContacts}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Revenue</div>
          <div className="value">{loading ? '—' : `€${totalRevenue.toLocaleString()}`}</div>
        </div>
        <div className="stat-card">
          <div className="label">API Status</div>
          <div className="value" style={{ fontSize: '1.2rem', color: apiStatus === 'ok' ? '#16a34a' : '#dc2626' }}>
            {apiStatus === 'ok' ? 'Online' : 'Offline'}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Import Client Samples</h3>
        <p style={{ color: '#64748b' }}>
          Import all files from the <code>samples/</code> folder into the CRM database.
        </p>
        <button className="btn btn-primary" onClick={handleImport} disabled={importing}>
          {importing ? 'Importing...' : 'Import Samples'}
        </button>
        {importResult && (
          <p style={{ marginTop: '0.75rem', color: importResult.includes('failed') && !importResult.includes('0 failed') ? '#991b1b' : '#166534' }}>
            {importResult}
          </p>
        )}
      </div>

      {!loading && companies.length > 0 && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>Recent Companies</h3>
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Country</th>
                <th>Contacts</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {companies.slice(0, 5).map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/companies/${c.id}`} className="link">{c.name}</Link></td>
                  <td>{c.country || '—'}</td>
                  <td>{c.contact_count}</td>
                  <td>€{c.total_revenue.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
