import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type {
  CompanyDetail,
  CompanyListItem,
  ContactBrief,
  InteractionBrief,
  MergeCandidate,
} from '../api/client';

const emptyContact = { name: '', email: '', phone: '' };
const CATEGORIES = ['Fresh', 'Frozen', 'Both', 'Unknown'] as const;

function formatDateTime(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const companyId = Number(id);

  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [interactions, setInteractions] = useState<InteractionBrief[]>([]);
  const [mergeCandidates, setMergeCandidates] = useState<MergeCandidate[]>([]);
  const [mergeSearch, setMergeSearch] = useState('');
  const [mergeResults, setMergeResults] = useState<CompanyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);

  const [editingProfile, setEditingProfile] = useState(false);
  const [profileDraft, setProfileDraft] = useState({
    country: '',
    product_category: 'Unknown',
    notes: '',
  });

  const [editingContactId, setEditingContactId] = useState<number | null>(null);
  const [contactDraft, setContactDraft] = useState(emptyContact);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState(emptyContact);

  const loadCompany = useCallback(async () => {
    if (!id) return;
    setError('');
    const [data, timeline, candidates] = await Promise.all([
      api.getCompany(companyId),
      api.getInteractions(companyId),
      api.getMergeCandidates(companyId),
    ]);
    setCompany(data);
    setInteractions(timeline);
    setMergeCandidates(candidates);
    setProfileDraft({
      country: data.country || '',
      product_category: data.product_category || 'Unknown',
      notes: data.notes || '',
    });
  }, [id, companyId]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    loadCompany()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, loadCompany]);

  const runAction = async (action: () => Promise<void>) => {
    setActionError('');
    setSaving(true);
    try {
      await action();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setSaving(false);
    }
  };

  const saveProfile = () =>
    runAction(async () => {
      const updated = await api.updateCompany(companyId, {
        country: profileDraft.country.trim() || null,
        product_category: profileDraft.product_category,
        notes: profileDraft.notes.trim() || null,
      });
      setCompany(updated);
      setProfileDraft({
        country: updated.country || '',
        product_category: updated.product_category || 'Unknown',
        notes: updated.notes || '',
      });
      setEditingProfile(false);
    });

  const startEditContact = (contact: ContactBrief) => {
    setEditingContactId(contact.id);
    setContactDraft({
      name: contact.name,
      email: contact.email || '',
      phone: contact.phone || '',
    });
    setShowAddContact(false);
  };

  const saveContact = () =>
    runAction(async () => {
      if (!contactDraft.name.trim()) throw new Error('Contact name is required');
      const updated = await api.updateContact(companyId, editingContactId!, {
        name: contactDraft.name.trim(),
        email: contactDraft.email.trim() || null,
        phone: contactDraft.phone.trim() || null,
      });
      setCompany(updated);
      setEditingContactId(null);
      setContactDraft(emptyContact);
    });

  const deleteContact = (contactId: number) => {
    if (!window.confirm('Delete this contact?')) return;
    runAction(async () => {
      const updated = await api.deleteContact(companyId, contactId);
      setCompany(updated);
      if (editingContactId === contactId) {
        setEditingContactId(null);
        setContactDraft(emptyContact);
      }
    });
  };

  const deleteCompany = () => {
    if (!company) return;
    if (company.purchase_count > 0) {
      window.alert(
        `This company has ${company.purchase_count} purchase record(s) from invoices and cannot be deleted. Use merge if it is a duplicate.`,
      );
      return;
    }
    if (
      !window.confirm(
        `Delete "${company.name}" and all its contacts, messages, and product interests? This cannot be undone.`,
      )
    ) {
      return;
    }
    runAction(async () => {
      await api.deleteCompany(companyId);
      navigate('/companies');
    });
  };

  const addContact = () =>
    runAction(async () => {
      if (!newContact.name.trim()) throw new Error('Contact name is required');
      const updated = await api.addContact(companyId, {
        name: newContact.name.trim(),
        email: newContact.email.trim() || undefined,
        phone: newContact.phone.trim() || undefined,
      });
      setCompany(updated);
      setNewContact(emptyContact);
      setShowAddContact(false);
    });

  const searchMergeTargets = () =>
    runAction(async () => {
      if (!mergeSearch.trim()) {
        setMergeResults([]);
        return;
      }
      const results = await api.listCompanies({ q: mergeSearch.trim() });
      setMergeResults(results.filter((item) => item.id !== companyId));
    });

  const mergeDuplicate = (duplicateId: number, duplicateName: string) => {
    if (!window.confirm(`Merge "${duplicateName}" into "${company?.name}"? This cannot be undone.`)) return;
    runAction(async () => {
      const updated = await api.mergeCompany(companyId, duplicateId);
      setCompany(updated);
      const candidates = await api.getMergeCandidates(companyId);
      setMergeCandidates(candidates);
      setMergeResults((items) => items.filter((item) => item.id !== duplicateId));
    });
  };

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

      {actionError && <div className="error-banner">{actionError}</div>}

      <div className="detail-grid">
        <div className="card">
          <div className="card-header-row">
            <h3>Profile</h3>
            {!editingProfile ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditingProfile(true)}>
                Edit profile
              </button>
            ) : (
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={saveProfile}>
                  Save
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={saving}
                  onClick={() => {
                    setProfileDraft({
                      country: company.country || '',
                      product_category: company.product_category || 'Unknown',
                      notes: company.notes || '',
                    });
                    setEditingProfile(false);
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
          {editingProfile ? (
            <div>
              <div className="form-field">
                <label>Country</label>
                <input
                  value={profileDraft.country}
                  onChange={(e) => setProfileDraft({ ...profileDraft, country: e.target.value })}
                  placeholder="e.g. Italy"
                />
              </div>
              <div className="form-field">
                <label>Product category</label>
                <select
                  value={profileDraft.product_category}
                  onChange={(e) => setProfileDraft({ ...profileDraft, product_category: e.target.value })}
                  style={{ padding: '0.6rem 0.75rem', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label>Notes</label>
                <textarea
                  value={profileDraft.notes}
                  onChange={(e) => setProfileDraft({ ...profileDraft, notes: e.target.value })}
                  placeholder="Add notes about this customer..."
                />
              </div>
            </div>
          ) : (
            <table>
              <tbody>
                <tr><td><strong>Country</strong></td><td>{company.country || '—'}</td></tr>
                <tr><td><strong>Category</strong></td><td>{company.product_category}</td></tr>
                <tr><td><strong>First Interaction</strong></td><td>{company.first_interaction_date || '—'}</td></tr>
                <tr><td><strong>Last Interaction</strong></td><td>{company.last_interaction_date || '—'}</td></tr>
                <tr>
                  <td><strong>Notes</strong></td>
                  <td>{company.notes || <span style={{ color: '#64748b' }}>No notes yet</span>}</td>
                </tr>
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Product Interests ({company.product_interests?.length ?? 0})</h3>
          {!company.product_interests?.length ? (
            <p style={{ color: '#64748b' }}>No product interests detected yet.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Product</th><th>Source</th></tr>
              </thead>
              <tbody>
                {company.product_interests.map((p) => (
                  <tr key={p.id}>
                    <td>{p.product_name_raw || '—'}</td>
                    <td>{p.source || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Communication Timeline ({interactions.length})</h3>
        {interactions.length === 0 ? (
          <p style={{ color: '#64748b' }}>No WhatsApp or email messages linked yet.</p>
        ) : (
          <div className="timeline-list">
            {interactions.map((item) => (
              <div key={item.id} className="timeline-item">
                <div className="timeline-meta">
                  <span className="timeline-type">{item.interaction_type}</span>
                  <span>{formatDateTime(item.interaction_date)}</span>
                  {item.sender && <span>From: {item.sender}</span>}
                </div>
                {item.subject && <strong>{item.subject}</strong>}
                <p className="timeline-content">{item.content || '—'}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="card-header-row">
          <h3>Contacts ({company.contacts.length})</h3>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => {
              setShowAddContact((v) => !v);
              setEditingContactId(null);
              setNewContact(emptyContact);
            }}
          >
            {showAddContact ? 'Cancel' : 'Add contact'}
          </button>
        </div>

        {showAddContact && (
          <div style={{ marginBottom: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
            <div className="form-field">
              <label>Name *</label>
              <input value={newContact.name} onChange={(e) => setNewContact({ ...newContact, name: e.target.value })} />
            </div>
            <div className="form-field">
              <label>Email</label>
              <input type="email" value={newContact.email} onChange={(e) => setNewContact({ ...newContact, email: e.target.value })} />
            </div>
            <div className="form-field">
              <label>Phone</label>
              <input value={newContact.phone} onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })} />
            </div>
            <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={addContact}>
              Save contact
            </button>
          </div>
        )}

        {company.contacts.length === 0 ? (
          <p style={{ color: '#64748b' }}>No contacts linked yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Phone</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {company.contacts.map((c) => (
                <tr key={c.id}>
                  {editingContactId === c.id ? (
                    <>
                      <td><input className="inline-input" value={contactDraft.name} onChange={(e) => setContactDraft({ ...contactDraft, name: e.target.value })} /></td>
                      <td><input className="inline-input" value={contactDraft.email} onChange={(e) => setContactDraft({ ...contactDraft, email: e.target.value })} /></td>
                      <td><input className="inline-input" value={contactDraft.phone} onChange={(e) => setContactDraft({ ...contactDraft, phone: e.target.value })} /></td>
                      <td className="action-cell">
                        <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={saveContact}>Save</button>
                        <button type="button" className="btn btn-secondary btn-sm" disabled={saving} onClick={() => { setEditingContactId(null); setContactDraft(emptyContact); }}>Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{c.name}</td>
                      <td>{c.email || '—'}</td>
                      <td>{c.phone || '—'}</td>
                      <td className="action-cell">
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => startEditContact(c)}>Edit</button>
                        <button type="button" className="btn btn-danger btn-sm" disabled={saving} onClick={() => deleteContact(c.id)}>Delete</button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Merge Duplicate Company</h3>
        <p style={{ color: '#64748b', marginTop: 0 }}>
          Move another company&apos;s contacts, purchases, and messages into <strong>{company.name}</strong>.
        </p>

        {mergeCandidates.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <strong>Suggested matches</strong>
            <div className="merge-list" style={{ marginTop: '0.5rem' }}>
              {mergeCandidates.map((candidate) => (
                <div key={candidate.id} className="merge-item">
                  <div className="merge-item-info">
                    <div>{candidate.name}</div>
                    <span>{candidate.score}% match · {candidate.contact_count} contacts · {candidate.purchase_count} purchases</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={saving}
                    onClick={() => mergeDuplicate(candidate.id, candidate.name)}
                  >
                    Merge here
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="search-bar" style={{ marginBottom: '0.75rem' }}>
          <input
            placeholder="Search company to merge..."
            value={mergeSearch}
            onChange={(e) => setMergeSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchMergeTargets()}
          />
          <button type="button" className="btn btn-secondary btn-sm" disabled={saving} onClick={searchMergeTargets}>
            Search
          </button>
        </div>

        {mergeResults.length > 0 && (
          <div className="merge-list">
            {mergeResults.map((item) => (
              <div key={item.id} className="merge-item">
                <div className="merge-item-info">
                  <div>{item.name}</div>
                  <span>{item.contact_count} contacts · €{item.total_revenue.toLocaleString()} revenue</span>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={saving}
                  onClick={() => mergeDuplicate(item.id, item.name)}
                >
                  Merge here
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>
          Purchase History ({company.purchase_count})
          {company.purchase_count > company.purchases.length && (
            <span style={{ color: '#64748b', fontSize: '0.85rem', fontWeight: 400 }}>
              {' '}· showing latest {company.purchases.length}
            </span>
          )}
        </h3>
        {company.purchases.length === 0 ? (
          <p style={{ color: '#64748b' }}>No purchases recorded yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Product</th><th>Qty</th><th>Revenue</th><th>Supplier</th><th>Date</th></tr>
            </thead>
            <tbody>
              {company.purchases.map((p) => (
                <tr key={p.id}>
                  <td>{p.product_name_raw || '—'}</td>
                  <td>{p.quantity ?? '—'}</td>
                  <td>{p.revenue != null ? `€${p.revenue.toLocaleString()}` : '—'}</td>
                  <td>{p.supplier_name || '—'}</td>
                  <td>{p.purchase_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card danger-zone" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Delete Company</h3>
        <p style={{ color: '#64748b', marginTop: 0 }}>
          Remove this company from the CRM. Use this for personal contacts or entries that should not be customers.
        </p>
        {company.purchase_count > 0 ? (
          <p style={{ color: '#b45309', marginBottom: '0.75rem' }}>
            This company has {company.purchase_count} purchase record(s) from invoices and cannot be deleted.
          </p>
        ) : null}
        <button
          type="button"
          className="btn btn-danger btn-sm"
          disabled={saving || company.purchase_count > 0}
          onClick={deleteCompany}
        >
          Delete company
        </button>
      </div>
    </div>
  );
}
