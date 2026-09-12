/**
 * Typed API client — all calls go through /api/v1/
 * Base URL defaults to the Vite dev proxy (same origin) or VITE_API_URL env var.
 */

let bearerToken: string | null = localStorage.getItem('schedulr_token');
export function setBearerToken(token: string | null) {
  bearerToken = token;
  if (token) localStorage.setItem('schedulr_token', token);
  else localStorage.removeItem('schedulr_token');
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
    const err = new Error(body?.error?.message ?? `HTTP ${res.status}`);
    (err as any).details = body?.error?.details;
    (err as any).code = body?.error?.code;
    throw err;
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

export interface AcademicTerm {
  id: string;
  tenant_id: string;
  name: string;
  start_date: string;
  end_date: string;
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

export interface Department {
  id: string;
  tenant_id: string;
  name: string;
}

export interface Room {
  id: string;
  tenant_id: string;
  campus_id: string | null;
  name: string;
  type: string;
  capacity: number;
  equipment_tags: string[];
  accessible: boolean;
}

export interface Course {
  id: string;
  tenant_id: string;
  department_id: string;
  name: string;
  type: 'core' | 'elective' | 'lab';
  credit_value: number;
  hours_per_week: number;
  block_size: number;
}

export interface StaffProfile {
  id: string;
  tenant_id: string;
  identity_id: string;
  employment_type: 'full_time' | 'part_time' | 'visiting';
  workload_cap_week: number;
  workload_cap_day: number;
  roles: string[];
  full_name?: string;
  email?: string;
}

export interface PeriodTemplate {
  id: string;
  tenant_id: string;
  weekday: number;
  period_index: number;
  start_time: string;
  end_time: string;
  shift: string;
}

export interface Rule {
  id: string;
  tenant_id: string;
  rule_type: string;
  scope: string;
  target_id: string | null;
  threshold: number | null;
  unit: string | null;
  polarity: string | null;
  weight: number | null;
  source: 'structured' | 'nl';
  raw_input_text: string | null;
  status: 'pending_confirmation' | 'confirmed';
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
    generate: (tenantId: string, termId: string) =>
      request<GenerateResponse>(`/api/v1/tenants/${tenantId}/timetables/generate`, {
        method: 'POST',
        body: JSON.stringify({ term_id: termId }),
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
    edit: (tenantId: string, versionId: string, data: { assignment_id: string; slot_start?: number; staff_profile_id?: string; room_id?: string; version_no: number }) =>
      request<{ assignment_id: string; new_version_no: number }>(`/api/v1/tenants/${tenantId}/timetables/${versionId}/edit`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    exportUrl: (tenantId: string, versionId: string, format: 'csv' | 'ics' | 'pdf') =>
      `${BASE}/api/v1/tenants/${tenantId}/timetables/${versionId}/export?format=${format}`,
  },
  rules: {
    parse: (tenantId: string, rawInputText: string) =>
      request<any>(`/api/v1/tenants/${tenantId}/rules/parse`, {
        method: 'POST',
        body: JSON.stringify({ text: rawInputText }),
      }),
    confirm: (tenantId: string, ruleId: string) =>
      request(`/api/v1/tenants/${tenantId}/rules/${ruleId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    create: (tenantId: string, data: any) =>
      request(`/api/v1/tenants/${tenantId}/rules`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  staff: {
    list: (tenantId: string) =>
      request<PaginatedResponse<StaffProfile>>(`/api/v1/tenants/${tenantId}/staff-profiles?limit=500`),
    create: (tenantId: string, data: Partial<StaffProfile>) =>
      request<StaffProfile>(`/api/v1/tenants/${tenantId}/staff-profiles`, { method: 'POST', body: JSON.stringify(data) }),
    getTimetable: (tenantId: string, staffId: string, versionId?: string) => {
      const qs = versionId ? `?version_id=${versionId}` : '';
      return request<Assignment[]>(`/api/v1/tenants/${tenantId}/staff-profiles/${staffId}/timetable${qs}`);
    },
  },
  courses: {
    list: (tenantId: string) =>
      request<PaginatedResponse<Course>>(`/api/v1/tenants/${tenantId}/courses?limit=500`),
    create: (tenantId: string, data: Partial<Course>) =>
      request<Course>(`/api/v1/tenants/${tenantId}/courses`, { method: 'POST', body: JSON.stringify(data) }),
  },
  rooms: {
    list: (tenantId: string) =>
      request<PaginatedResponse<Room>>(`/api/v1/tenants/${tenantId}/rooms?limit=500`),
    create: (tenantId: string, data: Partial<Room>) =>
      request<Room>(`/api/v1/tenants/${tenantId}/rooms`, { method: 'POST', body: JSON.stringify(data) }),
  },
  departments: {
    list: (tenantId: string) =>
      request<PaginatedResponse<Department>>(`/api/v1/tenants/${tenantId}/departments?limit=500`),
    create: (tenantId: string, data: Partial<Department>) =>
      request<Department>(`/api/v1/tenants/${tenantId}/departments`, { method: 'POST', body: JSON.stringify(data) }),
  },
  terms: {
    list: (tenantId: string) =>
      request<PaginatedResponse<AcademicTerm>>(`/api/v1/tenants/${tenantId}/terms?limit=10`),
    getFirst: async (tenantId: string) => {
      const res = await request<PaginatedResponse<AcademicTerm>>(`/api/v1/tenants/${tenantId}/terms?limit=1`);
      return res.items[0] || null;
    },
  },
  periodTemplates: {
    list: (tenantId: string) =>
      request<PaginatedResponse<PeriodTemplate>>(`/api/v1/tenants/${tenantId}/period-templates?limit=100`),
  },
  rules: {
    list: (tenantId: string) =>
      request<Rule[]>(`/api/v1/tenants/${tenantId}/rules`),
    parse: (tenantId: string, text: string) =>
      request<any>(`/api/v1/tenants/${tenantId}/rules/parse`, { method: 'POST', body: JSON.stringify({ text }) }),
    confirm: (tenantId: string, ruleId: string, data: any) =>
      request<Rule>(`/api/v1/tenants/${tenantId}/rules/${ruleId}/confirm`, { method: 'POST', body: JSON.stringify(data) }),
    create: (tenantId: string, data: Partial<Rule>) =>
      request<Rule>(`/api/v1/tenants/${tenantId}/rules`, { method: 'POST', body: JSON.stringify(data) }),
    delete: (tenantId: string, ruleId: string) =>
      request<void>(`/api/v1/tenants/${tenantId}/rules/${ruleId}`, { method: 'DELETE' }),
  },
  reports: {
    getVerification: (tenantId: string, versionId: string) =>
      request<LoadVerificationReport>(`/api/v1/tenants/${tenantId}/reports/verification?version_id=${versionId}`),
    getRoomUtilization: (tenantId: string, versionId: string) =>
      request<any>(`/api/v1/tenants/${tenantId}/reports/room-utilization?version_id=${versionId}`),
  },
  users: {
    getTenants: () =>
      request<{ tenants: { id: string; name: string }[] }>(`/api/v1/me/tenants`),
  },
  substitutions: {
    list: (tenantId: string) => 
      request<{ items: any[] }>(`/api/v1/tenants/${tenantId}/substitutions`),
    suggest: (tenantId: string, data: { absent_staff_profile_id: string; assignment_id: string; date: string; version_no: number }) =>
      request<{ substitution_id: string; candidates: { staff_profile_id: string; current_load: number }[] }>(`/api/v1/tenants/${tenantId}/substitutions`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    confirm: (tenantId: string, substitutionId: string, data: { substitute_staff_profile_id: string; version_no: number }) =>
      request<{ substitution_id: string; new_version_no: number }>(`/api/v1/tenants/${tenantId}/substitutions/${substitutionId}/confirm`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  import: {
    faculty: (tenantId: string, rows: any[]) =>
      request<{ success_count: number; errors: any[] }>(`/api/v1/tenants/${tenantId}/import/faculty`, {
        method: 'POST',
        body: JSON.stringify({ rows }),
      }),
    courses: (tenantId: string, rows: any[]) =>
      request<{ success_count: number; errors: any[] }>(`/api/v1/tenants/${tenantId}/import/courses`, {
        method: 'POST',
        body: JSON.stringify({ rows }),
      }),
    rooms: (tenantId: string, rows: any[]) =>
      request<{ success_count: number; errors: any[] }>(`/api/v1/tenants/${tenantId}/import/rooms`, {
        method: 'POST',
        body: JSON.stringify({ rows }),
      }),
    enrollments: (tenantId: string, rows: any[]) =>
      request<{ success_count: number; errors: any[] }>(`/api/v1/tenants/${tenantId}/import/enrollment`, {
        method: 'POST',
        body: JSON.stringify({ rows }),
      }),
  },
  notifications: {
    list: (tenantId: string) =>
      request<PaginatedResponse<any>>(`/api/v1/tenants/${tenantId}/notifications`),
    markRead: (tenantId: string, notificationId: string) =>
      request<{ status: string }>(`/api/v1/tenants/${tenantId}/notifications/${notificationId}/read`, { method: 'PUT' }),
    getPreferences: (tenantId: string) =>
      request<{ email: boolean; push: boolean; sms: boolean }>(`/api/v1/tenants/${tenantId}/notifications/preferences`),
    updatePreferences: (tenantId: string, data: { email: boolean; push: boolean; sms: boolean }) =>
      request<{ email: boolean; push: boolean; sms: boolean }>(`/api/v1/tenants/${tenantId}/notifications/preferences`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
};
