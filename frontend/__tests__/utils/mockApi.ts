// utils/mockApi.ts
import { vi } from "vitest";
import { mockJobs } from "../MockJobs";

export function setupMockApi() {
  // Mock the entire module exactly as imported by Dashboard
  vi.mock("../src/api/jobs.ts", () => ({
    listJobs: vi.fn().mockResolvedValue(mockJobs),
    createJob: vi.fn(),
    updateJob: vi.fn(),
    deleteJob: vi.fn(),
  }));

  // Return the actual mock functions for optional assertions
  const { listJobs, createJob, updateJob, deleteJob } =
    require("../src/api/jobs.ts");

  return { listJobs, createJob, updateJob, deleteJob };
}