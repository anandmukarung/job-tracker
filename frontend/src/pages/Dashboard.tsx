import { useEffect, useState } from "react";
import { deleteJob, listJobs } from "../api/jobs";
import type { Job } from "../types/job";
import JobForm from "../components/JobForm";
import Modal from "../components/Modal";
import JobTable from "../components/JobTable";

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
    <div className="min-h-screen w-full bg-gray-50 p-4">
        <h1 className="text-2xl font-bold mb-4">Job Tracker</h1>
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
                    onCreated={() => {
                        setRefreshKey((k) => k + 1);
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
                    onCreated={() => {
                        setEditingJob(null);
                        setRefreshKey((k) => k + 1)
                    }}
                />
            </Modal>
        }
    </div>
  );
}