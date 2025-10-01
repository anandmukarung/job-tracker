import { useEffect, useState } from "react";
import { listJobs } from "../api/jobs";
import type { Job } from "../types/job";
import JobForm from "../components/JobForm";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [refreshkey, setRefreshKey] = useState(0);

  useEffect(() => {
    async function loadJobs() {
      const data = await listJobs();
      setJobs(data);
    }
    loadJobs();
  }, [refreshkey]);

  return (
    <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Job Tracker</h1>

        {/* Job Form */}
        <JobForm onJobAdded={() => setRefreshKey(refreshkey + 1)} />

        {/* Jobs List*/}
        <table className="min-w-full bg-white rounded shadow">
        <thead>
            <tr className="bg-gray-100">
            <th className="px-4 py-2 text-left">Job Title</th>
            <th className="px-4 py-2 text-left">Company</th>
            <th className="px-4 py-2 text-left">Location</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-left">Date Applied</th>
            <th className="px-4 py-2 text-left">Job Link</th>
            </tr>
        </thead>
        <tbody>
            {jobs.length === 0 ? (
            <tr>
                <td colSpan={3} className="px-4 py-2 text-gray-500 italic text-center">
                No jobs found
                </td>
            </tr>
            ) : (
            jobs.map(job => (
                <tr key={job.id} className="border-t">
                <td className="px-4 py-2">{job.title}</td>
                <td className="px-4 py-2">{job.company}</td>
                <td className="px-4 py-2">{job.location}</td>
                <td className="px-4 py-2">{job.status}</td>
                <td className="px-4 py-2">{job.applied_date}</td>
                <td className="px-4 py-2">{job.job_link}</td>
                </tr>
            ))
            )}
        </tbody>
        </table>
    </div>
  );
}