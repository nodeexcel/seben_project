import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { CompanyListItem, CustomerAnalytics } from '../api/client';

const REVENUE_YEARS = ['2026', '2025', '2024', '2023', '2022'];

export default function Dashboard() {
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [yearAnalytics, setYearAnalytics] = useState<CustomerAnalytics[]>([]);
  const [revenueYear, setRevenueYear] = useState(String(new Date().getFullYear()));
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState<'ok' | 'error'>('ok');

  useEffect(() => {
    Promise.all([
      api.health().then(() => setApiStatus('ok')).catch(() => setApiStatus('error')),
      api.listCompanies().then(setCompanies).catch(() => setCompanies([])),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api
      .customerAnalytics({
        date_from: `${revenueYear}-01-01`,
        date_to: `${revenueYear}-12-31`,
      })
      .then(setYearAnalytics)
      .catch(() => setYearAnalytics([]));
  }, [revenueYear]);

  const totalRevenue = yearAnalytics.reduce((sum, row) => sum + row.total_revenue, 0);
  const revenueByCompany = new Map(yearAnalytics.map((row) => [row.company_id, row.total_revenue]));
  const totalContacts = companies.reduce((sum, c) => sum + c.contact_count, 0);

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Customer intelligence overview</p>
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
          <div className="label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <span>Revenue ({revenueYear})</span>
            <select
              value={revenueYear}
              onChange={(e) => setRevenueYear(e.target.value)}
              aria-label="Revenue year"
              style={{ fontSize: '0.75rem', padding: '0.15rem 0.35rem' }}
            >
              {REVENUE_YEARS.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div className="value">{loading ? '—' : `€${totalRevenue.toLocaleString()}`}</div>
        </div>
        <div className="stat-card">
          <div className="label">API Status</div>
          <div className="value" style={{ fontSize: '1.2rem', color: apiStatus === 'ok' ? '#16a34a' : '#dc2626' }}>
            {apiStatus === 'ok' ? 'Online' : 'Offline'}
          </div>
        </div>
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
                <th>Revenue ({revenueYear})</th>
              </tr>
            </thead>
            <tbody>
              {companies.slice(0, 5).map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/companies/${c.id}`} className="link">{c.name}</Link></td>
                  <td>{c.country || '—'}</td>
                  <td>{c.contact_count}</td>
                  <td>€{(revenueByCompany.get(c.id) ?? 0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
