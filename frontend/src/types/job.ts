export type JobStatus = "Applied" | "Interview" | "Offer" | "Rejected" | "Saved";

export interface Job {
    id: number;
    posting_id?: number | null;
    title: string;
    company: string;
    location: string;
    status: JobStatus;
    applied_date?: string | null;
    follow_up_date?: string | null;
    job_link?: string | null;
    job_description?: string | null;
    resume_path?: string | null;
    job_board_id?: string | null;
    source?: string | null;
    notes?: string | null;
    created_at: string;
    updated_at: string;
}

export type JobCreate = Omit<Job, "id" | "created_at" | "updated_at">;
export type JobUpdate = Partial<JobCreate>;

export interface CompanySuggestion {
    company: string;
}

export interface JobPostingSuggestion {
    id: number;
    company: string;
    title: string;
    normalized_company: string;
    normalized_title: string;
}
