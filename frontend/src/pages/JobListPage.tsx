import { useEffect, useState } from "react";
import type { Job } from "../types/job";
import { listJobs, deleteJob } from "../api/jobs";
import Modal from "../components/Modal";
import JobTable from "../components/JobTable";
import JobForm from "../components/JobForm";
import UploadJobsModal from "../components/UploadJobsModal";


export default function JobListPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [refreshKey, setRefreshKey] = useState(0);
    const [showModal, setShowModal] = useState(false);
    const [editingJob, setEditingJob] = useState<Job | null>(null);
    const [showUploadModal, setShowUploadModal] = useState(false);

    // Load all jobs
    useEffect(() => {
        async function loadJobs() {
            const res = await listJobs();
            setJobs(res);
        }
        loadJobs();
    }, [refreshKey]);

    return(
        <div className="min-h-screen w-full overflow-visible space-y-3 p-4 bg-gray-50">
            <div 
                className="flex gap-2 mb-4"
            >
                {/*Add Job Button*/}
                <button 
                    onClick={() => setShowModal(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                    Add Job
                </button>

                {/* Add multiple jobs with CSV/JSON */}
          
                <button
                    onClick={() => setShowUploadModal(true)}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >                   
                    Upload File
                </button>
            </div>
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

            {showUploadModal && (
                <Modal onClose={() => setShowUploadModal(false)}>
                    <UploadJobsModal
                        onClose={() => setShowUploadModal(false)}
                        onUploaded={() => setRefreshKey((k) => k + 1)}
                    />
                </Modal>
            )}
        </div>
    )
}