import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import Dashboard from "../src/pages/Dashboard";
import { listJobs } from "../src/api/jobs";
import { mockJobs } from "./MockJobs";

vi.mock("../src/api/jobs", () => ({
    listJobs: vi.fn(),
    deleteJob: vi.fn(),
}));

const listJobsMock = vi.mocked(listJobs);

describe("Dashboard", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("loads jobs and renders calculated dashboard metrics", async () => {
        listJobsMock.mockResolvedValue(mockJobs);

        render(<Dashboard />);

        await waitFor(() => {
            expect(listJobsMock).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByLabelText(/stats card for total jobs/i)).toHaveTextContent("5");
        expect(screen.getByLabelText(/stats card for applied/i)).toHaveTextContent("4");
        expect(screen.getByLabelText(/stats card for interviewing/i)).toHaveTextContent("1");
        expect(screen.getByLabelText(/stats card for offers/i)).toHaveTextContent("0");
        expect(screen.getByLabelText(/stats card for rejected/i)).toHaveTextContent("0");
    });
});
