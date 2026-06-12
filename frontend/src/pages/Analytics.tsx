import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { CustomerAnalytics, ProductAnalytics } from '../api/client';

export default function Analytics() {
  const [customers, setCustomers] = useState<CustomerAnalytics[]>([]);
  const [products, setProducts] = useState<ProductAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [productFilter, setProductFilter] = useState('');

  const load = () => {
    setLoading(true);
    const params = {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };
    Promise.all([
      api.customerAnalytics(params),
      api.productAnalytics({ ...params, product: productFilter || undefined }),
    ])
      .then(([c, p]) => { setCustomers(c); setProducts(p); })
      .catch(() => { setCustomers([]); setProducts([]); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Purchase Analytics</h1>
        <p>Revenue and quantity by customer and product</p>
      </div>

      <div className="search-bar">
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <input
          placeholder="Filter by product..."
          value={productFilter}
          onChange={(e) => setProductFilter(e.target.value)}
        />
        <button className="btn btn-primary" onClick={load}>Apply Filters</button>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Revenue by Customer</h3>
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : customers.length === 0 ? (
            <div className="empty-state">No purchase data yet</div>
          ) : (
            <table>
              <thead>
                <tr><th>Company</th><th>Revenue</th><th>Qty</th><th>Orders</th></tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.company_id}>
                    <td>{c.company_name}</td>
                    <td>${c.total_revenue.toLocaleString()}</td>
                    <td>{c.total_quantity.toLocaleString()}</td>
                    <td>{c.purchase_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Sales by Product</h3>
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : products.length === 0 ? (
            <div className="empty-state">No product data yet</div>
          ) : (
            <table>
              <thead>
                <tr><th>Product</th><th>Customers</th><th>Revenue</th><th>Qty</th></tr>
              </thead>
              <tbody>
                {products.map((p, i) => (
                  <tr key={i}>
                    <td>{p.product_name}</td>
                    <td>{p.customer_count}</td>
                    <td>${p.total_revenue.toLocaleString()}</td>
                    <td>{p.total_quantity.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
