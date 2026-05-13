import { useEffect, useState } from "react";
import { listJobs } from "../api/jobs";
import type { Job } from "../types/job";
import DashboardMetrics from "../components/DashboardMetrics";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    async function loadJobs() {
      const data = await listJobs();
      setJobs(data);
    }
    loadJobs();
  }, []);

  return (
    <div className="min-h-screen w-full bg-gray-50 p-4 overflow-visible">
        {/*Dashboard Metrics*/}
        <DashboardMetrics
            total={jobs.length}
            applied={jobs.filter((j) => j.status === "Applied").length}
            interviewing={jobs.filter((j) => j.status === "Interview").length}
            offers={jobs.filter((j) => j.status === "Offer").length}
            rejected={jobs.filter((j) => j.status === "Rejected").length}
        />

    </div>
  );
}
