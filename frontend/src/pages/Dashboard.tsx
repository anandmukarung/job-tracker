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
        <h1 className="text-2xl font-bold mb-4">Job Applications</h1>
        {/*Dashboard Metrics*/}
        <DashboardMetrics
            total={jobs.length}
            applied={jobs.filter((j) => j.status === "Applied").length}
            interviewing={jobs.filter((j) => j.status === "Interview").length}
            offers={jobs.filter((j) => j.status === "Offer").length}
            rejected={jobs.filter((j) => j.status === "Rejected").length}
        />

        {/*Add Job Button*/}
        <button 
            onClick={() => setShowModal(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
            Add Job
        </button>

        {/* Modal with Job Form*/}
        {showModal && (
            <Modal onClose={() => setShowModal(false)}>
                <JobForm
                    onSubmitted={() => {
                        setRefreshKey((k) => k + 1);
                        setShowModal(false);
                    }}
                    onCancel={() => {
                        setShowModal(false);
                    }}
                />
            </Modal>
        )}

        {/* Jobs List*/}
        <JobTable jobs={jobs} 
            onEdit={(job) => setEditingJob(job)}
            onDelete={ async (id) => {
                await deleteJob(id)
                setRefreshKey((k) => k + 1)
            }}
        />

        {/* Modal for Editing */}
        {editingJob && 
            <Modal onClose={() => setEditingJob(null)}>
                <JobForm
                    initialData={editingJob}
                    onSubmitted={() => {
                        setEditingJob(null);
                        setRefreshKey((k) => k + 1)
                    }}
                    onCancel={() =>{
                        setEditingJob(null);
                    }}
                />
            </Modal>
        }
    </div>
  );
}