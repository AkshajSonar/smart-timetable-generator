const API_BASE = 'http://localhost:8000/api/v1';

export interface ExamSessionResult {
    id: string;
    exam_timetable_version_id: string;
    course_id: string;
    cohort_id: string;
    room_id: string;
    invigilator_staff_profile_id: string | null;
    slot_start: number;
}

export interface ExamGenerateResponse {
    success: boolean;
    version_id: string | null;
    error: string | null;
    sessions: ExamSessionResult[];
}

export const examClient = {
    async generateExams(tenantId: string, termId: string): Promise<ExamGenerateResponse> {
        const res = await fetch(`${API_BASE}/tenants/${tenantId}/exams/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ term_id: termId }),
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail?.error?.message || 'Failed to generate exam timetable');
        }
        return res.json();
    }
};
