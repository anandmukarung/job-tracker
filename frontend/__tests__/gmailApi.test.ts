import { beforeEach, describe, expect, test, vi } from "vitest";

import {
    commitGmailImport,
    getGmailAuthUrl,
    getGmailImportPreview,
    getGmailStatus,
    startGmailImportPreview,
} from "../src/api/gmail";

const { getMock, postMock } = vi.hoisted(() => ({
    getMock: vi.fn(),
    postMock: vi.fn(),
}));

vi.mock("../src/api/client", () => ({
    api: {
        get: getMock,
        post: postMock,
    },
}));

describe("gmail api", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("getGmailStatus fetches gmail status", async () => {
        getMock.mockResolvedValue({ data: { authorized: true, token_expired: false } });

        const result = await getGmailStatus();

        expect(getMock).toHaveBeenCalledWith("/gmail/status");
        expect(result).toEqual({ authorized: true, token_expired: false });
    });

    test("getGmailAuthUrl requests oauth url with frontend redirect", async () => {
        getMock.mockResolvedValue({ data: { auth_url: "http://example.com/oauth" } });

        const result = await getGmailAuthUrl("http://127.0.0.1:5173/jobs");

        expect(getMock).toHaveBeenCalledWith("/gmail/auth/url", {
            params: { frontend_redirect: "http://127.0.0.1:5173/jobs" },
        });
        expect(result).toBe("http://example.com/oauth");
    });

    test("startGmailImportPreview sends date params", async () => {
        postMock.mockResolvedValue({ data: { session: { id: 1 } } });

        const result = await startGmailImportPreview("2025-01-01", "2025-01-31");

        expect(postMock).toHaveBeenCalledWith(
            "/gmail/import/preview",
            null,
            {
                params: {
                    start_date: "2025-01-01",
                    end_date: "2025-01-31",
                },
                timeout: 120000,
            },
        );
        expect(result).toEqual({ session: { id: 1 } });
    });

    test("getGmailImportPreview fetches preview results", async () => {
        getMock.mockResolvedValue({
            data: {
                session: {
                    id: 1,
                    start_date: "2025-01-01",
                    end_date: "2025-01-31",
                    status: "completed",
                    total_emails: 0,
                    new_items: 0,
                    cached_items: 0,
                    cache_hit: false,
                    imported_items: 0,
                    skipped_items: 0,
                    failed_items: 0,
                    error_message: null,
                    created_at: "2025-01-31T00:00:00Z",
                    updated_at: "2025-01-31T00:00:00Z",
                },
                count: 0,
                jobs: [],
            },
        });

        const result = await getGmailImportPreview(1);

        expect(getMock).toHaveBeenCalledWith("/gmail/import/preview/1", {
            timeout: 120000,
        });
        expect(result.count).toBe(0);
    });

    test("commitGmailImport posts import selections", async () => {
        const payload = {
            session_id: 12,
            items: [
                {
                    gmail_message_id: "gmail-1",
                    action: "create" as const,
                    target_job_id: null,
                    job_draft: { title: "Backend Engineer", company: "OpenAI", location: "Remote" },
                    update_items: null,
                },
            ],
        };
        postMock.mockResolvedValue({ data: { session: { id: 12 }, results: [] } });

        const result = await commitGmailImport(payload);

        expect(postMock).toHaveBeenCalledWith("/gmail/import/commit", payload);
        expect(result).toEqual({ session: { id: 12 }, results: [] });
    });
});
