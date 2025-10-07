import type { Job } from "../types/job";
import {PencilSquareIcon, TrashIcon} from "@heroicons/react/24/solid"

interface JobTableProps {
    jobs: Job[];
    onEdit?: (job: Job) => void;
    onDelete?: (jobId: number) => void;
}

export default function JobTable({ jobs, onEdit , onDelete}: JobTableProps) {
    if (jobs.length === 0){
        return <p className="text-gray-500 italic">No jobs found.</p>;
    }

    return(
        <div className="overflow-x-auto max-w-full rounded-lg shadow-md border border-gray-300">
            <table aria-label="Jobs List Table" className="min-w-full text-sm text-left">
                <thead aria-label="Jobs list table head" className="bg-gray-100 border border-gray-300 text-gray-700 uppercase text-xs">
                    <tr>
                        <th scope="column" className="px-4 py-2 text-left">Title</th>
                        <th scope="column" className="px-4 py-2 text-left">Company</th>
                        <th scope="column" className="px-4 py-2 text-left">Location</th>
                        <th scope="column" className="px-4 py-2 text-left">Status</th>
                        <th scope="column" className="px-4 py-2 text-left">Source</th>
                        <th scope="column" className="px-4 py-2 text-left">Applied Date</th>
                        <th scope="column" className="px-4 py-2 text-left">Actions</th>
                    </tr>
                </thead>
                <tbody aria-label="Jobs list table body" className="divide-y divide-gray-200">
                    {jobs.map((job) => (
                        <tr 
                            key={job.id}
                            aria-label={`job row for ${job.title} at ${job.company}`}
                            data-testid={`job-row-${job.id}`}
                            className="hover:bg-gray-50 transition-colors cursor pointer"
                        >
                            <td className="px-4 py-2">{job.title}</td>
                            <td className="px-4 py-2">{job.company}</td>
                            <td className="px-4 py-2">{job.location}</td>
                            <td className="px-4 py-2">{job.status}</td>
                            <td aria-label={`job link for ${job.title} at ${job.company}`}className="px-4 py-2">
                                {job.job_link ? (
                                    <a
                                        href={job.job_link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline"
                                    >
                                        {job.source || job.job_link}
                                    </a>
                                ) : (
                                    <span className="text-gray-400">{job.source || "N/A"}</span>
                                )}
                            </td>
                            <td className="px-4 py-2">{job.applied_date || "-/-/-" }</td>
                            <td className="px-4 py-2">
                                <button
                                    aria-label={`Edit ${job.title} at ${job.company}`}
                                    data-testid={`edit-${job.id}`}
                                    onClick={() => onEdit?.(job)}
                                    className="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600"
                                > 
                                    <PencilSquareIcon className="h-5 w-5" />
                                </button>
                                <button
                                    aria-label={`Delete ${job.title} at ${job.company}`}
                                    data-testid={`delete-${job.id}`}
                                    onClick={() => {
                                        if (window.confirm("Are you sure you want to delete this job record?")){
                                            onDelete?.(job.id);
                                        }
                                    }}
                                    className="p-2 text-red-600 hover:text-red-800"
                                >
                                    <TrashIcon className="h-5 w-5"/>
                                </button>
                            </td>

                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}