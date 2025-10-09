import React, { useState } from "react";
import { createJobsBatch } from "../api/jobs";
import Papa from "papaparse";

const REQUIRED_FIELDS = ["title", "company", "location"];
const OPTIONAL_FIELDS = [
    "status",
    "applied_date",
    "follow_up_date",
    "job_link",
    "job_description",
    "job_board_id",
    "source",
    "notes",
];
const VALID_FIELDS = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];


export default function UploadJobsModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void}) {
    const [jobs, setJobs] = useState<any[]>([]);
    const [error, setError] = useState<string | null>(null);

    async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;

        if (file.name.endsWith(".csv")){
            Papa.parse(file, {
                header: true,
                skipEmptyLines: true,
                complete: (results) => {
                    const { fields } = results.meta;
                    const validation = validateHeaders(fields as string[]);
                    if (validation.missing.length > 0) {
                        setError(`Missing required columns: ${validation.missing.join(", ")}`);
                        return;
                    }
                    if (validation.extra.length > 0) {
                        setError(`Unrecognized columns: ${validation.extra.join(", ")}`);
                        return;
                    }
                    setJobs(results.data);
                },
                error: (err) => setError(err.message),

            });
        } else if (file.name.endsWith(".json")){
            const text = await file.text();
            try {
                const data = JSON.parse(text);
                setJobs(data);
            } catch (err: any) {
                setError("Invalid JSON format");
            }
        } else {
            setError("Unsupported file type. Upload CSV or JSON");
        }
    }

    async function handleUpload() {
        if (jobs.length === 0) {
            setError("No jobs to upload");
            return;
        }
        try {
            await createJobsBatch(jobs);
            onUploaded();
            onClose();
        } catch {
            setError("Failed to upload jobs");
        }
         
    }

    // Check headers for missing or extra columns
    function validateHeaders(headers: string[]): { missing: string[]; extra: string[]} {
        const lowerHeaders = headers.map((h) => h.trim().toLowerCase());
        const missing = REQUIRED_FIELDS.filter((f) => !lowerHeaders.includes(f));
        const extra = lowerHeaders.filter((h) => !VALID_FIELDS.includes(h));
        return { missing, extra};
    }

    return(
        <div className="p-4 rounded-lg w-full max-w-2x1 mx-auto">
            <h2 className="text-xl font-semibold mb-4">Upload Jobs Batch File</h2>
            <input 
                type="file"
                accept=".csv,.json"
                onChange={handleFileChange}
                className="hover:bg-gray-200 mt-3 mb-2 p-2 rounded cursor-pointer"
            />

            {error && <p className="text-red-500 text-sm mb-2">{error}</p>}

            {jobs.length > 0 && (
                <div className="overflow-x-auto max-h-60 border rounded">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-100">
                            <tr>
                                {Object.keys(jobs[0].map((key) => (
                                    <th key={key} className="px-3 py-2 text-left">{key}</th>
                                )))}
                            </tr>
                        </thead>
                        <tbody>
                            {jobs.map((job, i) => (
                                <tr key={i} className="border-t hover-bg-gray-50">
                                    {Object.values(job).map((val, j) => (
                                        <td key={j} className="px-3 py-2 truncate max-w-[150px]">{String(val)}</td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            <div className="flex justify-end gap-2 mt-4">
                <button
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
                >
                    Cancel
                </button>
                <button
                    onClick={handleUpload}
                    disabled={jobs.length === 0}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                    Upload
                </button>
            </div>
        </div>
    )
}