import React, { useState } from "react";
import { createJob } from "../api/jobs";
import type { JobCreate, JobStatus } from "../types/job";

type Props = {
    onJobAdded?: () => void; 
};

const STATUSES: JobStatus[] = ["saved", "applied", "interview", "offer", "rejected"];

export default function JobForm({ onJobAdded }: Props){
    const [title, setTitle] = useState("");
    const [company, setCompany] = useState("");
    const [location, setLocation] = useState("");
    const [status, setStatus] = useState<JobStatus>("applied");
    const [applicationDate, setApplicationDate] = useState<string>("");
    const [followUpDate, setFollowUpDate] = useState<string>("");
    const [jobLink, setJobLink] = useState<string>("");
    const [jobDescription, setJobDescription] = useState<string>("");
    const [jobBoardId, setJobBoardId] = useState<string>("");
    const [source, setSource] = useState<string>("");
    const [notes, setNotes] = useState<string>("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null> (null);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError(null);

        if(!title.trim() || !company.trim() || !location.trim()){
            setError("Must specify Title, Company and Location.");
            return;
        }

        const payload: JobCreate = {
            title,
            company,
            location,
            status,
            applied_date: applicationDate || null,
            follow_up_date: followUpDate || null,
            job_link: jobLink || null,
            job_description: jobDescription || null,
            job_board_id: jobBoardId || null,
            source: source || null,
            notes: notes || null,
        };

        try {
            setSubmitting(true);
            await createJob(payload);
            //Reset fields
            setTitle("");
            setCompany("");
            setLocation("");
            setStatus("applied");
            setApplicationDate("");
            setFollowUpDate("");
            setJobLink("");
            setJobBoardId("");
            setSource("");
            setNotes("");
            onJobAdded?.();
        } catch (err) {
            setError("Failed to create job. Please try again.")
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-2x1 bg-white rounded-x1 shadow p-6 space-y-6">
            <div>
                <h2 className="text-x1 font-semibold">Add Job</h2>
                <p className="text-sm text-gray-500">Enter job details you want to track.</p>
            </div> 
            {error && (
                <div className="rounded-md border border-red-300 bg-red-50 p-3 text-red-700 text-sm">
                    {error}
                </div>
            )}
            <div className="grid grid-cols-1 md:gird-cols-2 gap-4">
                {/* Title */}
                <div className="flex flex-col">
                    <label htmlFor="title" className="text-sm font-medium text-gray-700">Title *</label>
                    <input 
                        id="title"
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="Software Engineer"
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>
                
                {/* Company */}
                <div className="flex flex-col">
                    <label htmlFor="company" className="text-sm font-medium text-gray-700">Company *</label>
                    <input
                        id="company"
                        type="text"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        placeholder="Acme Corp"
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Location */}
                <div className="flex flex-col">
                    <label htmlFor="location" className="text-sm font-medium text-gray-700">Location *</label>
                    <input
                        id="company"
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        placeholder="Remote | Pittsburgh,PA"
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Status */}
                <div className="flex flex-col">
                    <label htmlFor="status" className="text-sm font-medium text-gray-700">Status *</label>
                    <select
                        id="status"
                        value={status}
                        onChange={(e) => setStatus(e.target.value as JobStatus)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                        {STATUSES.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
         
                    </select>
                    
                </div>

                {/* Application Date */}
                <div className="flex flex-col">
                    <label htmlFor="application_date" className="text-sm font-medium text-gray-700">Applied Date *</label>
                    <input
                        id="application_date"
                        type="date"
                        value={applicationDate}
                        onChange={(e) => setApplicationDate(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Follow-Up Date */}
                <div className="flex flex-col">
                    <label htmlFor="follow_up_date" className="text-sm font-medium text-gray-700">Follow-Up Date *</label>
                    <input
                        id="follow_up_date"
                        type="date"
                        value={followUpDate}
                        onChange={(e) => setFollowUpDate(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Job Link */}
                <div className="flex flex-col">
                    <label htmlFor="job_link" className="text-sm font-medium text-gray-700">Job Link *</label>
                    <input
                        id="job_link"
                        type="string"
                        value={jobLink}
                        onChange={(e) => setJobLink(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Job Description */}
                <div className="flex flex-col">
                    <label htmlFor="job_description" className="text-sm font-medium text-gray-700">Job Description * </label>
                    <input
                        id="job_description"
                        type="string"
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Job Board ID */}
                <div className="flex flex-col">
                    <label htmlFor="job_board_id" className="text-sm font-medium text-gray-700">Job Board ID *</label>
                    <input
                        id="job_board_id"
                        type="string"
                        value={jobBoardId}
                        onChange={(e) => setJobBoardId(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>
                
                {/* Source */}
                <div className="flex flex-col">
                    <label htmlFor="source" className="text-sm font-medium text-gray-700">Source *</label>
                    <input
                        id="source"
                        type="string"
                        value={source}
                        onChange={(e) => setSource(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                {/* Notes */}
                <div className="flex flex-col">
                    <label htmlFor="notes" className="text-sm font-medium text-gray-700">Notes *</label>
                    <input
                        id="notes"
                        type="string"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>
            </div>
            {/* Actions */}
            <div className="flex items-center gap-3">
                <button
                    type="submit"
                    disabled={submitting}
                    className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                >
                    {submitting ? "Saving..." : "Save Job"}
                </button>
                <button
                    type="button"
                    onClick={() => {
                        setTitle(""); setCompany(""); setLocation(""); setStatus("applied"); setApplicationDate(""); setFollowUpDate(""); setJobLink(""); setJobDescription(""); setJobBoardId(""); setSource("");
                    }}
                    className="rounded-lg border px-4 py-2 text-gray-700 hover:bg-gray-50"
                >
                    Reset
                </button>
            </div>
        </form>
    )
}
