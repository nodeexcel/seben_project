import { Fragment, useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type {
  CustomerAnalytics,
  InactiveClientAnalytics,
  ProductAnalytics,
} from '../api/client';

const REVENUE_YEARS = ['all', '2026', '2025', '2024', '2023', '2022'];

function formatMoney(value: number) {
  return `€${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function yearDateRange(year: string): { date_from?: string; date_to?: string } {
  if (year === 'all') return {};
  return { date_from: `${year}-01-01`, date_to: `${year}-12-31` };
}

export default function Analytics() {
  const [customers, setCustomers] = useState<CustomerAnalytics[]>([]);
  const [products, setProducts] = useState<ProductAnalytics[]>([]);
  const [inactive, setInactive] = useState<InactiveClientAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [inactiveLoading, setInactiveLoading] = useState(true);
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [productFilter, setProductFilter] = useState('');

  const [expandedProduct, setExpandedProduct] = useState<string | null>(null);
  const [expandedCompany, setExpandedCompany] = useState<number | null>(null);
  const [productBreakdown, setProductBreakdown] = useState<Record<string, CustomerAnalytics[]>>({});
  const [companyBreakdown, setCompanyBreakdown] = useState<Record<number, ProductAnalytics[]>>({});
  const [breakdownLoading, setBreakdownLoading] = useState<string | number | null>(null);

  const dateParams = yearDateRange(year);

  const load = useCallback(() => {
    setLoading(true);
    setExpandedProduct(null);
    setExpandedCompany(null);
    setProductBreakdown({});
    setCompanyBreakdown({});
    const params = {
      ...dateParams,
      product: productFilter || undefined,
    };
    Promise.all([
      api.customerAnalytics(params),
      api.productAnalytics(params),
    ])
      .then(([c, p]) => {
        setCustomers(c);
        setProducts(p);
      })
      .catch(() => {
        setCustomers([]);
        setProducts([]);
      })
      .finally(() => setLoading(false));
  }, [dateParams.date_from, dateParams.date_to, productFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setInactiveLoading(true);
    api
      .inactiveClients(6)
      .then(setInactive)
      .catch(() => setInactive([]))
      .finally(() => setInactiveLoading(false));
  }, []);

  const toggleProduct = async (productName: string) => {
    if (expandedProduct === productName) {
      setExpandedProduct(null);
      return;
    }
    setExpandedProduct(productName);
    setExpandedCompany(null);
    if (productBreakdown[productName]) return;

    setBreakdownLoading(productName);
    try {
      const rows = await api.customerAnalytics({
        ...dateParams,
        product: productName,
      });
      setProductBreakdown((prev) => ({ ...prev, [productName]: rows }));
    } catch {
      setProductBreakdown((prev) => ({ ...prev, [productName]: [] }));
    } finally {
      setBreakdownLoading(null);
    }
  };

  const toggleCompany = async (companyId: number) => {
    if (expandedCompany === companyId) {
      setExpandedCompany(null);
      return;
    }
    setExpandedCompany(companyId);
    setExpandedProduct(null);
    if (companyBreakdown[companyId]) return;

    setBreakdownLoading(companyId);
    try {
      const rows = await api.productAnalytics({
        ...dateParams,
        company_id: companyId,
      });
      setCompanyBreakdown((prev) => ({ ...prev, [companyId]: rows }));
    } catch {
      setCompanyBreakdown((prev) => ({ ...prev, [companyId]: [] }));
    } finally {
      setBreakdownLoading(null);
    }
  };

  const yearLabel = year === 'all' ? 'all time' : year;
  const totalRevenue = customers.reduce((sum, row) => sum + row.total_revenue, 0);
  const totalProductRevenue = products.reduce((sum, row) => sum + row.total_revenue, 0);

  return (
    <div>
      <div className="page-header">
        <h1>Purchase Analytics</h1>
        <p>Revenue and quantity by customer and product (all amounts in euros)</p>
      </div>

      <div className="search-bar">
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.875rem', color: '#64748b' }}>Year</span>
          <select
            value={year}
            onChange={(e) => setYear(e.target.value)}
            aria-label="Analytics year"
          >
            {REVENUE_YEARS.map((y) => (
              <option key={y} value={y}>
                {y === 'all' ? 'All time' : y}
              </option>
            ))}
          </select>
        </label>
        <input
          placeholder="Filter by product (e.g. gambero, orata)..."
          value={productFilter}
          onChange={(e) => setProductFilter(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <button className="btn btn-primary" onClick={load}>Apply Filters</button>
      </div>

      <div className="card-grid" style={{ marginBottom: '1rem' }}>
        <div className="stat-card">
          <div className="label">Customer revenue ({yearLabel})</div>
          <div className="value">{loading ? '—' : formatMoney(totalRevenue)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Product sales ({yearLabel})</div>
          <div className="value">{loading ? '—' : formatMoney(totalProductRevenue)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Active customers ({yearLabel})</div>
          <div className="value">{loading ? '—' : customers.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Products sold ({yearLabel})</div>
          <div className="value">{loading ? '—' : products.length}</div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Revenue by Customer ({yearLabel})</h3>
          <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.875rem' }}>
            Click a company to see revenue split by product.
          </p>
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : customers.length === 0 ? (
            <div className="empty-state">No matching purchases for these filters</div>
          ) : (
            <table>
              <thead>
                <tr><th>Company</th><th>Revenue</th><th>Qty</th><th>Orders</th></tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <Fragment key={c.company_id}>
                    <tr key={c.company_id}>
                      <td>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => toggleCompany(c.company_id)}
                          aria-expanded={expandedCompany === c.company_id}
                        >
                          {expandedCompany === c.company_id ? '▾ ' : '▸ '}
                          {c.company_name}
                        </button>
                        {' '}
                        <Link to={`/companies/${c.company_id}`} className="link" title="Open profile">
                          ↗
                        </Link>
                      </td>
                      <td>{formatMoney(c.total_revenue)}</td>
                      <td>{c.total_quantity.toLocaleString()}</td>
                      <td>{c.purchase_count}</td>
                    </tr>
                    {expandedCompany === c.company_id && (
                      <tr key={`${c.company_id}-breakdown`} className="breakdown-row">
                        <td colSpan={4}>
                          {breakdownLoading === c.company_id ? (
                            <div className="breakdown-panel">Loading product breakdown...</div>
                          ) : (companyBreakdown[c.company_id] ?? []).length === 0 ? (
                            <div className="breakdown-panel">No catalog products for this period</div>
                          ) : (
                            <table className="breakdown-table">
                              <thead>
                                <tr><th>Product</th><th>Revenue</th><th>Qty</th></tr>
                              </thead>
                              <tbody>
                                {(companyBreakdown[c.company_id] ?? []).map((row) => (
                                  <tr key={row.product_name}>
                                    <td>{row.product_name}</td>
                                    <td>{formatMoney(row.total_revenue)}</td>
                                    <td>{row.total_quantity.toLocaleString()}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Sales by Product ({yearLabel})</h3>
          <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.875rem' }}>
            Click a product to see revenue split by client.
          </p>
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : products.length === 0 ? (
            <div className="empty-state">No matching product data for these filters</div>
          ) : (
            <table>
              <thead>
                <tr><th>Product</th><th>Customers</th><th>Revenue</th><th>Qty</th></tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <Fragment key={p.product_name}>
                    <tr key={p.product_name}>
                      <td>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => toggleProduct(p.product_name)}
                          aria-expanded={expandedProduct === p.product_name}
                        >
                          {expandedProduct === p.product_name ? '▾ ' : '▸ '}
                          {p.product_name}
                        </button>
                      </td>
                      <td>{p.customer_count}</td>
                      <td>{formatMoney(p.total_revenue)}</td>
                      <td>{p.total_quantity.toLocaleString()}</td>
                    </tr>
                    {expandedProduct === p.product_name && (
                      <tr key={`${p.product_name}-breakdown`} className="breakdown-row">
                        <td colSpan={4}>
                          {breakdownLoading === p.product_name ? (
                            <div className="breakdown-panel">Loading client breakdown...</div>
                          ) : (productBreakdown[p.product_name] ?? []).length === 0 ? (
                            <div className="breakdown-panel">No client data for this period</div>
                          ) : (
                            <table className="breakdown-table">
                              <thead>
                                <tr><th>Company</th><th>Revenue</th><th>Qty</th><th>Orders</th></tr>
                              </thead>
                              <tbody>
                                {(productBreakdown[p.product_name] ?? []).map((row) => (
                                  <tr key={row.company_id}>
                                    <td>
                                      <Link to={`/companies/${row.company_id}`} className="link">
                                        {row.company_name}
                                      </Link>
                                    </td>
                                    <td>{formatMoney(row.total_revenue)}</td>
                                    <td>{row.total_quantity.toLocaleString()}</td>
                                    <td>{row.purchase_count}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Clients with no orders in the last 6 months</h3>
        <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.875rem' }}>
          Companies that have ordered before but have not purchased since{' '}
          {new Date(Date.now() - 6 * 30 * 24 * 60 * 60 * 1000).toLocaleDateString()}.
        </p>
        {inactiveLoading ? (
          <div className="empty-state">Loading...</div>
        ) : inactive.length === 0 ? (
          <div className="empty-state">No inactive clients found</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Last order</th>
                <th>Days since order</th>
                <th>Lifetime revenue</th>
                <th>Total orders</th>
              </tr>
            </thead>
            <tbody>
              {inactive.map((row) => (
                <tr key={row.company_id}>
                  <td>
                    <Link to={`/companies/${row.company_id}`} className="link">
                      {row.company_name}
                    </Link>
                  </td>
                  <td>{formatDate(row.last_purchase_date)}</td>
                  <td>{row.days_since_last_order ?? '—'}</td>
                  <td>{formatMoney(row.total_historical_revenue)}</td>
                  <td>{row.total_historical_orders}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
