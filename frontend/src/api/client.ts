const API_BASE = import.meta.env.VITE_API_URL || '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export interface CompanyListItem {
  id: number;
  name: string;
  country: string | null;
  product_category: string;
  first_interaction_date: string | null;
  last_interaction_date: string | null;
  contact_count: number;
  total_revenue: number;
  total_quantity: number;
}

export interface ContactBrief {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
}

export interface PurchaseBrief {
  id: number;
  product_name_raw: string | null;
  quantity: number | null;
  revenue: number | null;
  currency: string | null;
  purchase_date: string | null;
}

export interface CompanyDetail {
  id: number;
  name: string;
  country: string | null;
  product_category: string;
  first_interaction_date: string | null;
  last_interaction_date: string | null;
  ai_summary: string | null;
  notes: string | null;
  contacts: ContactBrief[];
  purchases: PurchaseBrief[];
  created_at: string;
  updated_at: string;
}

export interface ExtractionResult {
  source_type: string;
  filename: string;
  status: string;
  extracted: Record<string, unknown>;
  errors: string[];
}

export interface UploadResponse {
  document_id: number;
  filename: string;
  source_type: string;
  status: string;
  extraction: ExtractionResult | null;
}

export interface CustomerAnalytics {
  company_id: number;
  company_name: string;
  total_revenue: number;
  total_quantity: number;
  purchase_count: number;
}

export interface ProductAnalytics {
  product_name: string;
  customer_count: number;
  total_quantity: number;
  total_revenue: number;
}

export interface SupportedType {
  id: string;
  label: string;
  extensions: string[];
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listCompanies: (params?: { q?: string; product?: string; country?: string }) => {
    const search = new URLSearchParams();
    if (params?.q) search.set('q', params.q);
    if (params?.product) search.set('product', params.product);
    if (params?.country) search.set('country', params.country);
    const qs = search.toString();
    return request<CompanyListItem[]>(`/api/companies/${qs ? `?${qs}` : ''}`);
  },

  getCompany: (id: number) => request<CompanyDetail>(`/api/companies/${id}`),

  createCompany: (data: { name: string; country?: string; notes?: string }) =>
    request<CompanyDetail>('/api/companies/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  uploadFile: (file: File, sourceType?: string, persist = false) => {
    const form = new FormData();
    form.append('file', file);
    if (sourceType) form.append('source_type', sourceType);
    form.append('persist', String(persist));
    return request<UploadResponse>('/api/upload/', { method: 'POST', body: form });
  },

  supportedTypes: () =>
    request<{ types: SupportedType[] }>('/api/upload/supported-types'),

  customerAnalytics: (params?: { date_from?: string; date_to?: string }) => {
    const search = new URLSearchParams();
    if (params?.date_from) search.set('date_from', params.date_from);
    if (params?.date_to) search.set('date_to', params.date_to);
    const qs = search.toString();
    return request<CustomerAnalytics[]>(`/api/analytics/customers${qs ? `?${qs}` : ''}`);
  },

  productAnalytics: (params?: { product?: string; date_from?: string; date_to?: string }) => {
    const search = new URLSearchParams();
    if (params?.product) search.set('product', params.product);
    if (params?.date_from) search.set('date_from', params.date_from);
    if (params?.date_to) search.set('date_to', params.date_to);
    const qs = search.toString();
    return request<ProductAnalytics[]>(`/api/analytics/products${qs ? `?${qs}` : ''}`);
  },
};
