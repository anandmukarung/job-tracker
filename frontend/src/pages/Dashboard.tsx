import { useEffect, useState } from "react";
import { deleteJob, listJobs } from "../api/jobs";
import type { Job } from "../types/job";
import JobForm from "../components/JobForm";
import Modal from "../components/Modal";
import JobTable from "../components/JobTable";
import DashboardMetrics from "../components/DashboardMetrics";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);

  useEffect(() => {
    async function loadJobs() {
      const data = await listJobs();
      setJobs(data);
    }
    loadJobs();
  }, [refreshKey]);

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