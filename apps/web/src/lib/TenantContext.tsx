/**
 * TenantContext — resolves the first tenant the logged-in identity belongs to
 * and makes tenantId + termId available throughout the app.
 * Also exposes the last-generated timetable version ID so pages can share it.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api/client';

interface TenantState {
  tenantId: string;
  termId: string;
  tenantName: string;
  loading: boolean;
  error: string | null;
  /** Most-recently generated version ID — set by GeneratePage, read by PublishPage */
  lastVersionId: string;
  setLastVersionId: (id: string) => void;
}

const TenantContext = createContext<TenantState>({
  tenantId: '',
  termId: '',
  tenantName: '',
  loading: true,
  error: null,
  lastVersionId: '',
  setLastVersionId: () => {},
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenantId, setTenantId] = useState('');
  const [termId, setTermId] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastVersionId, setLastVersionId] = useState('');

  useEffect(() => {
    api.users.getTenants()
      .then(res => {
        if (res.tenants.length === 0) {
          setError('No tenant found for this user. Run seed_demo.py first.');
          return;
        }
        const first = res.tenants[0];
        setTenantId(first.id);
        setTenantName(first.name);
        // Fetch the term for this tenant
        return api.terms.getFirst(first.id);
      })
      .then(term => {
        if (term) setTermId(term.id);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <TenantContext.Provider value={{ tenantId, termId, tenantName, loading, error, lastVersionId, setLastVersionId }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  return useContext(TenantContext);
}
