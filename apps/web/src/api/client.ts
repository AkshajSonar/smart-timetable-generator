/**
 * Typed API client — all calls go through /api/v1/
 * Base URL defaults to the Vite dev proxy (same origin) or VITE_API_URL env var.
 */

let bearerToken: string | null = null;
export function setBearerToken(token: string | null) {
  bearerToken = token;
}
export function getBearerToken() {
  return bearerToken;
}

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };
  if (bearerToken) {
    headers['Authorization'] = `Bearer ${bearerToken}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface Assignment {
  id: string;
  staff_profile_id: string;
  course_id: string;
  cohort_id: string;
  batch_id?: string | null;
  room_id: string;
  slot_start: number;
  slot_span: number;
}

export interface TimetableVersion {
  id: string;
  tenant_id: string;
  state: string;
  version_no: number;
  approved_by: string | null;
  assignments: Assignment[];
}

export interface GenerateResponse {
  timetable_version_id: string;
  status: string;
  violations: { h_code: string; message: string }[];
}

export interface Cohort {
  id: string;
  tenant_id: string;
  name: string;
  type: string;
}

export interface LoadVerificationItem {
  id: string;
  name: string;
  required_hours: number;
  scheduled_hours: number;
  difference: number;
}

export interface LoadVerificationReport {
  faculty_load: LoadVerificationItem[];
  cohort_load: LoadVerificationItem[];
}

export interface Student {
  id: string;
  identity_id: string | null;
  external_student_code: string;
  cohort_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
}

// ── API calls ────────────────────────────────────────────────────────────────

export const api = {
  cohorts: {
    list: (tenantId: string) =>
      request<PaginatedResponse<Cohort>>(`/api/v1/tenants/${tenantId}/cohorts?limit=100`),
  },
  students: {
    list: (tenantId: string) =>
      request<PaginatedResponse<Student>>(`/api/v1/tenants/${tenantId}/students?limit=500`),
    getTimetable: (tenantId: string, studentId: string, versionId: string) =>
      request<Assignment[]>(`/api/v1/tenants/${tenantId}/students/${studentId}/timetable?versionId=${versionId}`),
  },
  timetables: {
    generate: (tenantId: string) =>
      request<GenerateResponse>(`/api/v1/tenants/${tenantId}/timetables/generate`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    get: (tenantId: string, versionId: string) =>
      request<TimetableVersion>(`/api/v1/tenants/${tenantId}/timetables/${versionId}`),
    approve: (tenantId: string, versionId: string, versionNo: number) =>
      request(`/api/v1/tenants/${tenantId}/timetables/${versionId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ version_no: versionNo }),
      }),
    publish: (tenantId: string, versionId: string, versionNo: number) =>
      request(`/api/v1/tenants/${tenantId}/timetables/${versionId}/publish`, {
        method: 'POST',
        body: JSON.stringify({ version_no: versionNo }),
      }),
  },
  rules: {
    parse: (tenantId: string, rawInputText: string) =>
      request<any>(`/api/v1/tenants/${tenantId}/rules/parse`, {
        method: 'POST',
        body: JSON.stringify({ raw_input_text: rawInputText }),
      }),
    confirm: (tenantId: string, ruleId: string) =>
      request(`/api/v1/tenants/${tenantId}/rules/${ruleId}/confirm`, {
        method: 'POST',
      }),
    create: (tenantId: string, data: any) =>
      request(`/api/v1/tenants/${tenantId}/rules`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  staff: {
    list: (tenantId: string) =>
      request<PaginatedResponse<any>>(`/api/v1/tenants/${tenantId}/staff-profiles?limit=500`),
    getTimetable: (tenantId: string, staffId: string) =>
      request<Assignment[]>(`/api/v1/tenants/${tenantId}/staff-profiles/${staffId}/timetable`),
  },
  reports: {
    getVerification: (tenantId: string, versionId: string) =>
      request<LoadVerificationReport>(`/api/v1/tenants/${tenantId}/reports/verification?version_id=${versionId}`),
  },
  users: {
    getTenants: () =>
      request<{ tenants: { id: string; name: string }[] }>(`/api/v1/me/tenants`),
  }
};
