import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { CompanyDetail } from '../api/client';

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    api.getCompany(Number(id))
      .then(setCompany)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="empty-state">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!company) return <div className="empty-state">Company not found</div>;

  return (
    <div>
      <div className="page-header">
        <Link to="/companies" className="link">← Back to Companies</Link>
        <h1>{company.name}</h1>
        <p>{company.country || 'Country not set'} · {company.product_category}</p>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Profile</h3>
          <table>
            <tbody>
              <tr><td><strong>First Interaction</strong></td><td>{company.first_interaction_date || '—'}</td></tr>
              <tr><td><strong>Last Interaction</strong></td><td>{company.last_interaction_date || '—'}</td></tr>
              <tr><td><strong>Notes</strong></td><td>{company.notes || '—'}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>AI Summary</h3>
          {company.ai_summary ? (
            <p>{company.ai_summary}</p>
          ) : (
            <p style={{ color: '#64748b' }}>No summary yet. Requires OpenAI API key (Milestone 4).</p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Contacts ({company.contacts.length})</h3>
        {company.contacts.length === 0 ? (
          <p style={{ color: '#64748b' }}>No contacts linked yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Phone</th></tr>
            </thead>
            <tbody>
              {company.contacts.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.email || '—'}</td>
                  <td>{c.phone || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Purchase History ({company.purchases.length})</h3>
        {company.purchases.length === 0 ? (
          <p style={{ color: '#64748b' }}>No purchases recorded yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Product</th><th>Qty</th><th>Revenue</th><th>Date</th></tr>
            </thead>
            <tbody>
              {company.purchases.map((p) => (
                <tr key={p.id}>
                  <td>{p.product_name_raw || '—'}</td>
                  <td>{p.quantity ?? '—'}</td>
                  <td>{p.revenue != null ? `$${p.revenue.toLocaleString()}` : '—'}</td>
                  <td>{p.purchase_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
