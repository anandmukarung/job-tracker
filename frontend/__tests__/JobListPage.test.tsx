import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import JobListPage from "../src/pages/JobListPage";
import { deleteJob, listJobs } from "../src/api/jobs";
import { mockJobs } from "./MockJobs";

vi.mock("../src/api/jobs", () => ({
    listJobs: vi.fn(),
    deleteJob: vi.fn(),
}));

vi.mock("../src/components/Modal", () => ({
    default: ({ children }: { children: React.ReactNode }) => <div data-testid="modal">{children}</div>,
}));

vi.mock("../src/components/JobForm", () => ({
    default: ({
        initialData,
        onSubmitted,
        onCancel,
    }: {
        initialData?: { title?: string } | null;
        onSubmitted?: () => void;
        onCancel?: () => void;
    }) => (
        <div>
            <p>{initialData ? `Editing ${initialData.title}` : "Add job form"}</p>
            <button onClick={onSubmitted}>submit form</button>
            <button onClick={onCancel}>cancel form</button>
        </div>
    ),
}));

vi.mock("../src/components/UploadJobsModal", () => ({
    default: ({
        onClose,
        onUploaded,
    }: {
        onClose: () => void;
        onUploaded: () => void;
    }) => (
        <div>
            <p>Upload jobs modal</p>
            <button onClick={onUploaded}>finish upload</button>
            <button onClick={onClose}>close upload</button>
        </div>
    ),
}));

vi.mock("../src/components/GmailImportModal", () => ({
    default: ({
        onClose,
        onImported,
    }: {
        onClose: () => void;
        onImported: () => void;
    }) => (
        <div>
            <p>Gmail import modal</p>
            <button onClick={onImported}>finish gmail import</button>
            <button onClick={onClose}>close gmail import</button>
        </div>
    ),
}));

vi.mock("../src/components/JobTable", () => ({
    default: ({
        jobs,
        onEdit,
        onDelete,
    }: {
        jobs: Array<{ id: number; title: string }>;
        onEdit?: (job: { id: number; title: string }) => void;
        onDelete?: (jobId: number) => void;
    }) => (
        <div>
            <p>Rendered jobs: {jobs.length}</p>
            <button onClick={() => onEdit?.(jobs[0])}>edit first job</button>
            <button onClick={() => onDelete?.(jobs[0].id)}>delete first job</button>
        </div>
    ),
}));

const listJobsMock = vi.mocked(listJobs);
const deleteJobMock = vi.mocked(deleteJob);

describe("JobListPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        listJobsMock.mockResolvedValue(mockJobs);
    });

    test("loads jobs and opens the add-job modal", async () => {
        render(<JobListPage />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });
        expect(screen.getByText("Rendered jobs: 5")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /add job/i }));

        expect(screen.getByTestId("modal")).toBeInTheDocument();
        expect(screen.getByText("Add job form")).toBeInTheDocument();
    });

    test("refreshes the list after deleting a job", async () => {
        deleteJobMock.mockResolvedValue(undefined);

        render(<JobListPage />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });

        await userEvent.click(screen.getByRole("button", { name: /delete first job/i }));

        await waitFor(() => {
            expect(deleteJobMock).toHaveBeenCalledWith(mockJobs[0].id);
            expect(listJobsMock).toHaveBeenCalledTimes(2);
        });
    });

    test("opens edit mode with the selected job", async () => {
        render(<JobListPage />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });

        await userEvent.click(screen.getByRole("button", { name: /edit first job/i }));

        expect(screen.getByText(`Editing ${mockJobs[0].title}`)).toBeInTheDocument();
    });

    test("opens upload modal and refreshes after upload completes", async () => {
        render(<JobListPage />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });

        await userEvent.click(screen.getByRole("button", { name: /upload file/i }));
        expect(screen.getByText("Upload jobs modal")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /finish upload/i }));

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(2);
        });
    });

    test("opens gmail import modal and refreshes after import completes", async () => {
        render(<JobListPage />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });

        await userEvent.click(screen.getByRole("button", { name: /import gmail/i }));
        expect(screen.getByText("Gmail import modal")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /finish gmail import/i }));

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(2);
        });
    });
});
