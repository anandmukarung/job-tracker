import React, { useEffect, useState, } from "react";
import { createJob, updateJob} from "../api/jobs";
import type { Job, JobCreate, JobStatus} from "../types/job";

type JobFormProps = {
    initialData?: Job;
    onSubmitted?: () => void; 
};

const STATUSES: JobStatus[] = ["Saved", "Applied", "Interview", "Offer", "Rejected"];

export default function JobForm({ initialData, onSubmitted }: JobFormProps){

    const blankJOb: JobCreate = {
        title: "",
        company: "",
        location: "",
        status: "Saved",
        applied_date: null,
        follow_up_date: null,
        job_link: null,
        job_description: null,
        job_board_id: null,
        source: null,
        notes: null,
    };

    // State holds one job object
    const [job, setJob] = useState<JobCreate>(initialData || blankJOb);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null)

    // Sync when switching between add/edit
    useEffect(() => {
        if (initialData){
            setJob(initialData);
        } else {
            setJob(blankJOb);
        }
    }, [initialData]);

    // Generic Handler for input changes
    async function handleChange(
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) {
        const {name, value} = e.target;
        setJob((prev) => ({ 
            ...prev, 
            [name]: value || null,
        }));
    }
    
    // Submit Handler
    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        if (!job.title.trim() || !job.company.trim() || !job.location.trim()){
            setError("Must specify Title, Company and Location for job.")
            return;
        }

        if (job.applied_date && job.follow_up_date) {
            if (new Date(job.follow_up_date) < new Date(job.applied_date)){
                setError("Follow-up date cannot be before application date.")
                return;
            }
        }

        if (job.status == "Applied" && !job.applied_date?.trim()){
            setError("Please enter the date you applied for this position.")
            return;
        }
        try{
            setSubmitting(true);
            if (initialData) {
                await updateJob(initialData.id, job);
            } else {
                await createJob(job);
            }

            //Reset if creating new job;
            if (!initialData) setJob(blankJOb);
            onSubmitted?.();
        } catch (err){
            setError("Failed to save job. Please try again.");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <form onSubmit={handleSubmit} aria-label="job form" className="space-y-4">
            {error && <p className="text-red-600">{error}</p>}

            <input 
                aria-label="Job Title"
                type="text"
                name="title"
                value={job.title || ""}
                onChange={handleChange}
                placeholder="Job Title *"
                className="border px-3 py-2 rounded w-full"
            />

            <input
                aria-label="Company Name"
                type="text"
                name="company"
                value={job.company || ""}
                onChange={handleChange}
                placeholder="Company Name *"
                className="border px-3 py-2 rounded w-full"
            />

            <input 
                aria-label="Job Location"
                type="text"
                name="location"
                value={job.location || ""}
                onChange={handleChange}
                placeholder="Location *"
                className="border px-3 py-2 rounded w-full"
            />

            <select
                aria-label="Job Status"
                name="status"
                value={job.status}
                onChange={handleChange}
                className="border px-3 py-2 rounded w-full"
            >
                {STATUSES.map((s) => (
                    <option key={s} value={s}>
                        {s}
                    </option>
                ))}
            </select>
            
            <label htmlFor="application-date" className="block text-sm font-medium text-gray-700">
                Application Date
            </label>
            <input
                id="application-date"
                type="date"
                name="applied_date"
                value={job.applied_date || ""}
                onChange={handleChange}
                className="border px-3 py-2 rounded w-full"
            />
            
            <label htmlFor="follow-up-date" className="block text-sm font-medium text-gray-700">
                Follow-up Date
            </label>
            <input 
                id="follow-up-date"
                type="date"
                name="follow_up_date"
                value={job.follow_up_date || ""}
                onChange={handleChange}
                className="border px-3 py-2 rounded w-full"
            />

            <input 
                aria-label="Job Link"
                type="url"
                name="job_link"
                value={job.job_link || ""}
                placeholder="Job Link"
                onChange={handleChange}
                className="border px-3 py-2 rounded w-full"
            />

            <textarea
                aria-label="Job Description"
                name="job_description"
                value={job.job_description || ""}
                onChange={handleChange}
                placeholder="Job Description"
                className="border px-3 py-2 rounded w-full"
            />

            <input 
                aria-label="Job Board ID"
                type="text"
                name="job_board_id"
                value={job.job_board_id || ""}
                onChange={handleChange}
                placeholder="Job Board ID"
                className="border px-3 py-2 rounded w-full"
            />

            <input 
                aria-label="Job Source"
                type="text"
                name="source"
                value={job.source || ""}
                onChange={handleChange}
                placeholder="Job Source"
                className="border px-3 py-2 rounded w-full"
            />

            <textarea 
                aria-label="Job Notes"
                name="notes"
                value={job.notes || ""}
                onChange={handleChange}
                placeholder="Notes"
                className="border px-3 py-2 rounded w-full"
            />

            {/* Submit button */}
            <button
                type="submit"
                aria-label="submit"
                disabled={submitting}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
                {submitting ? "Saving..." : initialData? "Update Job" : "Add Job"}
            </button>
        </form>
        
    
    )
}