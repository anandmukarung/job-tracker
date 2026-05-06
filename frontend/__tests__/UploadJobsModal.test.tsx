import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import UploadJobsModal from "../src/components/UploadJobsModal";
import { createJobsBatch } from "../src/api/jobs";
import Papa from "papaparse";

vi.mock("../src/api/jobs", () => ({
    createJobsBatch: vi.fn(),
}));

vi.mock("papaparse", () => ({
    default: {
        parse: vi.fn(),
    },
}));

const createJobsBatchMock = vi.mocked(createJobsBatch);
const parseMock = vi.mocked(Papa.parse);

describe("UploadJobsModal", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("shows an error when csv headers are missing required fields", async () => {
        parseMock.mockImplementation((_file, config) => {
            config.complete?.({
                data: [],
                meta: { fields: ["title", "company"] },
            } as never);
        });

        const { container } = render(<UploadJobsModal onClose={vi.fn()} onUploaded={vi.fn()} />);

        const file = new File(["title,company\nEngineer,OpenAI"], "jobs.csv", {
            type: "text/csv",
        });
        const input = container.querySelector('input[type="file"]');

        expect(input).not.toBeNull();
        fireEvent.change(input!, {
            target: { files: [file] },
        });

        expect(await screen.findByText(/missing required columns: location/i)).toBeInTheDocument();
    });

    test("parses valid csv files, previews jobs, and uploads them", async () => {
        const jobs = [
            { title: "Software Engineer", company: "OpenAI", location: "Remote", status: "Applied" },
        ];

        parseMock.mockImplementation((_file, config) => {
            config.complete?.({
                data: jobs,
                meta: { fields: ["title", "company", "location", "status"] },
            } as never);
        });
        createJobsBatchMock.mockResolvedValue([]);

        const onClose = vi.fn();
        const onUploaded = vi.fn();

        const { container } = render(<UploadJobsModal onClose={onClose} onUploaded={onUploaded} />);

        const file = new File(["title,company,location,status"], "jobs.csv", {
            type: "text/csv",
        });
        const input = container.querySelector('input[type="file"]');
        expect(input).not.toBeNull();
        fireEvent.change(input!, {
            target: { files: [file] },
        });

        expect(await screen.findByText("Software Engineer")).toBeInTheDocument();
        expect(screen.getByText("OpenAI")).toBeInTheDocument();
        expect(screen.getByText("Remote")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /upload/i }));

        await waitFor(() => {
            expect(createJobsBatchMock).toHaveBeenCalledWith(jobs);
        });
        expect(onUploaded).toHaveBeenCalled();
        expect(onClose).toHaveBeenCalled();
    });

    test("parses valid json files and uploads them", async () => {
        const jobs = [{ title: "Frontend Engineer", company: "OpenAI", location: "NYC" }];
        createJobsBatchMock.mockResolvedValue([]);

        const onClose = vi.fn();
        const onUploaded = vi.fn();

        const { container } = render(<UploadJobsModal onClose={onClose} onUploaded={onUploaded} />);

        const file = new File([JSON.stringify(jobs)], "jobs.json", {
            type: "application/json",
        });
        Object.defineProperty(file, "text", {
            value: vi.fn().mockResolvedValue(JSON.stringify(jobs)),
        });
        const input = container.querySelector('input[type="file"]');
        expect(input).not.toBeNull();

        fireEvent.change(input!, {
            target: { files: [file] },
        });

        expect(await screen.findByText("Frontend Engineer")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /upload/i }));

        await waitFor(() => {
            expect(createJobsBatchMock).toHaveBeenCalledWith(jobs);
        });
        expect(onUploaded).toHaveBeenCalled();
        expect(onClose).toHaveBeenCalled();
    });

    test("shows an error when upload fails", async () => {
        const jobs = [{ title: "Frontend Engineer", company: "OpenAI", location: "NYC" }];
        createJobsBatchMock.mockRejectedValue(new Error("upload failed"));

        const { container } = render(<UploadJobsModal onClose={vi.fn()} onUploaded={vi.fn()} />);

        const file = new File([JSON.stringify(jobs)], "jobs.json", {
            type: "application/json",
        });
        Object.defineProperty(file, "text", {
            value: vi.fn().mockResolvedValue(JSON.stringify(jobs)),
        });
        const input = container.querySelector('input[type="file"]');
        expect(input).not.toBeNull();

        fireEvent.change(input!, {
            target: { files: [file] },
        });

        await screen.findByText("Frontend Engineer");
        await userEvent.click(screen.getByRole("button", { name: /upload/i }));

        expect(await screen.findByText(/failed to upload jobs/i)).toBeInTheDocument();
    });
});
