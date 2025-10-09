import { api } from "./client";
import type { Job, JobCreate, JobUpdate } from "../types/job";

// Get all jobs
export async function listJobs(): Promise<Job[]> {
    const res = await api.get<Job[]>("/jobs/");
    return res.data;
}

// Create a new job
export async function createJob(payload: JobCreate): Promise<Job> {
    const res = await api.post<Job>("/jobs/", payload);
    return res.data;
}

// Update a job
export async function updateJob(id: number, payload: JobUpdate): Promise<Job> {
    const res = await api.put<Job>(`/jobs/${id}`, payload);
    return res.data;
}

// Delete a job
export async function deleteJob(id: number): Promise<void> {
    await api.delete(`/jobs/${id}`);
}

// Search specific job
export async function searchJobs(params:{
    company?: string;
    title?: string;
    location?: string;
    status?: string;
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_desc?: boolean;
}): Promise<Job[]> {
   const res = await api.get<Job[]>("/jobs/search",{params});
   return res.data;
}

// Add multiple jobs
export async function createJobsBatch(jobs: JobCreate[]) {
    const res = await api.post<Job[]>("/jobs/batch", jobs);
    return res.data;
}