import { beforeEach, describe, expect, test, vi } from "vitest";

import { mockJobs } from "./MockJobs";
import { createJob, createJobsBatch, deleteJob, listJobs, searchJobs, updateJob } from "../src/api/jobs";

const { getMock, postMock, putMock, deleteMock } = vi.hoisted(() => ({
    getMock: vi.fn(),
    postMock: vi.fn(),
    putMock: vi.fn(),
    deleteMock: vi.fn(),
}));

vi.mock("../src/api/client", () => ({
    api: {
        get: getMock,
        post: postMock,
        put: putMock,
        delete: deleteMock,
    },
}));

describe("jobs api", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("listJobs fetches jobs list", async () => {
        getMock.mockResolvedValue({ data: mockJobs });

        const result = await listJobs();

        expect(getMock).toHaveBeenCalledWith("/jobs/");
        expect(result).toEqual(mockJobs);
    });

    test("createJob posts a new job payload", async () => {
        const payload = {
            title: "ML Engineer",
            company: "OpenAI",
            location: "Remote",
            status: "Applied" as const,
            applied_date: "2025-01-01",
            follow_up_date: null,
            job_link: null,
            job_description: null,
            resume_path: null,
            job_board_id: null,
            source: "Gmail",
            notes: null,
        };
        postMock.mockResolvedValue({ data: mockJobs[0] });

        const result = await createJob(payload);

        expect(postMock).toHaveBeenCalledWith("/jobs/", payload);
        expect(result).toEqual(mockJobs[0]);
    });

    test("updateJob puts updates to the job endpoint", async () => {
        const payload = { status: "Interview" as const };
        putMock.mockResolvedValue({ data: mockJobs[1] });

        const result = await updateJob(mockJobs[1].id, payload);

        expect(putMock).toHaveBeenCalledWith(`/jobs/${mockJobs[1].id}`, payload);
        expect(result).toEqual(mockJobs[1]);
    });

    test("deleteJob deletes the job endpoint", async () => {
        deleteMock.mockResolvedValue({});

        await deleteJob(mockJobs[0].id);

        expect(deleteMock).toHaveBeenCalledWith(`/jobs/${mockJobs[0].id}`);
    });

    test("searchJobs forwards query params", async () => {
        getMock.mockResolvedValue({ data: [mockJobs[0]] });
        const params = { company: "OpenAI", sort_by: "applied_date", sort_desc: false };

        const result = await searchJobs(params);

        expect(getMock).toHaveBeenCalledWith("/jobs/search", { params });
        expect(result).toEqual([mockJobs[0]]);
    });

    test("createJobsBatch posts all jobs", async () => {
        const payload = [
            {
                title: "Backend Engineer",
                company: "OpenAI",
                location: "Remote",
                status: "Applied" as const,
                applied_date: "2025-01-01",
                follow_up_date: null,
                job_link: null,
                job_description: null,
                resume_path: null,
                job_board_id: null,
                source: "CSV",
                notes: null,
            },
        ];
        postMock.mockResolvedValue({ data: mockJobs });

        const result = await createJobsBatch(payload);

        expect(postMock).toHaveBeenCalledWith("/jobs/batch", payload);
        expect(result).toEqual(mockJobs);
    });
});
