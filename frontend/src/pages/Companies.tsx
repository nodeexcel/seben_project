import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { CompanyListItem } from '../api/client';

function categoryBadge(category: string) {
  const cls =
    category === 'Fresh' ? 'badge-fresh' :
    category === 'Frozen' ? 'badge-frozen' :
    category === 'Both' ? 'badge-both' : 'badge-unknown';
  return <span className={`badge ${cls}`}>{category}</span>;
}

export default function Companies() {
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [product, setProduct] = useState('');
  const [country, setCountry] = useState('');
  const [category, setCategory] = useState('');

  const load = () => {
    setLoading(true);
    api.listCompanies({
      q: q || undefined,
      product: product || undefined,
      country: country || undefined,
      category: category || undefined,
    })
      .then(setCompanies)
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Companies</h1>
        <p>Search and filter customer profiles</p>
      </div>

      <div className="search-bar">
        <input
          placeholder="Search company or contact..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <input
          placeholder="Filter by product..."
          value={product}
          onChange={(e) => setProduct(e.target.value)}
        />
        <input
          placeholder="Filter by country..."
          value={country}
          onChange={(e) => setCountry(e.target.value)}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          <option value="Fresh">Fresh</option>
          <option value="Frozen">Frozen</option>
          <option value="Both">Both</option>
        </select>
        <button className="btn btn-primary" onClick={load}>Search</button>
      </div>

      <div className="card">
        {loading ? (
          <div className="empty-state">Loading...</div>
        ) : companies.length === 0 ? (
          <div className="empty-state">
            <p>No companies yet.</p>
            <p>Upload sample data via <Link to="/upload" className="link">Upload & Extract</Link> to get started.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Country</th>
                <th>Category</th>
                <th>Contacts</th>
                <th>Revenue</th>
                <th>Qty</th>
                <th>Last Interaction</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/companies/${c.id}`} className="link">{c.name}</Link></td>
                  <td>{c.country || '—'}</td>
                  <td>{categoryBadge(c.product_category)}</td>
                  <td>{c.contact_count}</td>
                  <td>€{c.total_revenue.toLocaleString()}</td>
                  <td>{c.total_quantity.toLocaleString()}</td>
                  <td>{c.last_interaction_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
