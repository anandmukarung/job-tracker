import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { AxiosError } from "axios";

import GmailImportModal from "../src/components/GmailImportModal";
import {
    commitGmailImport,
    getGmailAuthUrl,
    getGmailImportPreview,
    getGmailStatus,
    startGmailImportPreview,
} from "../src/api/gmail";
import { searchCompanies, searchJobPostings } from "../src/api/jobs";
import { mockJobs } from "./MockJobs";

vi.mock("../src/api/gmail", () => ({
    getGmailStatus: vi.fn(),
    getGmailAuthUrl: vi.fn(),
    startGmailImportPreview: vi.fn(),
    getGmailImportPreview: vi.fn(),
    commitGmailImport: vi.fn(),
}));
vi.mock("../src/api/jobs", () => ({
    searchCompanies: vi.fn(),
    searchJobPostings: vi.fn(),
}));

const getGmailStatusMock = vi.mocked(getGmailStatus);
const getGmailAuthUrlMock = vi.mocked(getGmailAuthUrl);
const startGmailImportPreviewMock = vi.mocked(startGmailImportPreview);
const getGmailImportPreviewMock = vi.mocked(getGmailImportPreview);
const commitGmailImportMock = vi.mocked(commitGmailImport);
const searchCompaniesMock = vi.mocked(searchCompanies);
const searchJobPostingsMock = vi.mocked(searchJobPostings);

describe("GmailImportModal", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getGmailStatusMock.mockResolvedValue({ authorized: true });
        searchCompaniesMock.mockResolvedValue([{ company: "Company" }, { company: "OpenAI" }]);
        searchJobPostingsMock.mockResolvedValue([{ id: 100, company: "OpenAI", title: "Backend Engineer", normalized_company: "openai", normalized_title: "backend engineer" }]);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    test("shows connect gmail when unauthorized", async () => {
        getGmailStatusMock.mockResolvedValue({ authorized: false, message: "No credentials found." });
        getGmailAuthUrlMock.mockResolvedValue("http://example.com/oauth");

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText("No credentials found.")).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /connect gmail/i }));

        await waitFor(() => {
            expect(getGmailAuthUrlMock).toHaveBeenCalled();
        });
    });

    test("shows status load error when gmail status request fails", async () => {
        getGmailStatusMock.mockRejectedValue(new Error("status failed"));

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText("Failed to load Gmail connection status.")).toBeInTheDocument();
    });

    test("fetches preview results and expands email content", async () => {
        startGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 1,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "queued",
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
        });
        getGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 1,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 0,
                skipped_items: 0,
                failed_items: 0,
                error_message: null,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            count: 1,
            jobs: [
                {
                    gmail_message_id: "gmail-1",
                    thread_id: "thread-1",
                    from: "recruiter@company.com",
                    subject: "Application received",
                    date: "2025-01-15T12:00:00Z",
                    source: "company_email",
                    email_content: {
                        snippet: "Thank you for applying.",
                        body_text: "Thank you for applying for the Backend Engineer position.",
                        from_email: "recruiter@company.com",
                        from_domain: "company.com",
                    },
                    classification: {
                        label: "NEW_APPLICATION",
                        confidence: 0.9,
                        reasons: ["confirmation_phrase"],
                    },
                    job_draft: {
                        title: "Backend Engineer",
                        company: "Company",
                        location: "Remote",
                        applied_date: "2025-01-15",
                        status: "Applied",
                        source: "Gmail",
                    },
                    update_items: null,
                    extraction_candidates: {
                        title: [],
                        company: [],
                        location: [],
                        identifiers: { gmail_thread_id: [] },
                    },
                    match_candidates: [],
                    best_match: null,
                    import_item_id: 11,
                    import_status: "pending",
                    selected_action: "create",
                    linked_job_id: null,
                    already_processed: false,
                    needs_review: true,
                },
            ],
        });

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));

        expect(await screen.findByText(/Suggested posting: Company · Backend Engineer/)).toBeInTheDocument();
        expect(screen.getByText("recruiter@company.com")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /see email/i }));
        expect(screen.getAllByText("Thank you for applying.")).toHaveLength(2);

        await userEvent.click(screen.getByRole("button", { name: /expand full email/i }));
        expect(screen.getByText(/Backend Engineer position/)).toBeInTheDocument();
    });

    test("shows backend preview error detail when fetch fails", async () => {
        const error = new AxiosError("preview failed");
        error.response = {
            data: { detail: "Failed to fetch Gmail import preview: gmail unreachable" },
            status: 500,
            statusText: "Internal Server Error",
            headers: {},
            config: {} as never,
        };
        startGmailImportPreviewMock.mockRejectedValue(error);

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));

        expect(
            await screen.findByText("Failed to fetch Gmail import preview: gmail unreachable"),
        ).toBeInTheDocument();
    });

    test("shows timeout-specific preview error message", async () => {
        const error = new AxiosError("timeout of 120000ms exceeded", "ECONNABORTED");
        startGmailImportPreviewMock.mockRejectedValue(error);

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));

        expect(
            await screen.findByText(
                "Gmail import preview timed out while waiting for results. The preview may still be processing; please try again in a moment.",
            ),
        ).toBeInTheDocument();
    });

    test("imports selected gmail items", async () => {
        startGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 3,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "queued",
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
        });
        getGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 3,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 0,
                skipped_items: 0,
                failed_items: 0,
                error_message: null,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            count: 1,
            jobs: [
                {
                    gmail_message_id: "gmail-2",
                    thread_id: "thread-2",
                    from: "recruiter@company.com",
                    subject: "Application received",
                    date: "2025-01-15T12:00:00Z",
                    source: "company_email",
                    email_content: {
                        snippet: "Thank you for applying.",
                        body_text: "Thank you for applying for the Backend Engineer position.",
                        from_email: "recruiter@company.com",
                        from_domain: "company.com",
                    },
                    classification: {
                        label: "NEW_APPLICATION",
                        confidence: 0.9,
                        reasons: ["confirmation_phrase"],
                    },
                    job_draft: {
                        title: "Backend Engineer",
                        company: "Company",
                        location: "Remote",
                        applied_date: "2025-01-15",
                        status: "Applied",
                        source: "Gmail",
                    },
                    update_items: null,
                    extraction_candidates: {
                        title: [],
                        company: [],
                        location: [],
                        identifiers: { gmail_thread_id: [] },
                    },
                    match_candidates: [],
                    best_match: null,
                    import_item_id: 12,
                    import_status: "pending",
                    selected_action: "create",
                    linked_job_id: null,
                    already_processed: false,
                    needs_review: true,
                },
            ],
        });
        commitGmailImportMock.mockResolvedValue({
            session: {
                id: 3,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 1,
                skipped_items: 0,
                failed_items: 0,
                error_message: null,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            results: [],
        });
        const onImported = vi.fn();
        const onClose = vi.fn();

        render(<GmailImportModal jobs={mockJobs} onClose={onClose} onImported={onImported} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));
        expect(await screen.findByText(/Suggested posting: Company · Backend Engineer/)).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /import selected/i }));

        await waitFor(() => {
            expect(commitGmailImportMock).toHaveBeenCalled();
            expect(onImported).toHaveBeenCalled();
            expect(onClose).toHaveBeenCalled();
        });
    });

    test("submits update imports with selected target job and edited values", async () => {
        searchJobPostingsMock.mockResolvedValue([
            {
                id: 100,
                company: mockJobs[0].company,
                title: mockJobs[0].title,
                normalized_company: "openai",
                normalized_title: "software engineer",
            },
        ]);
        startGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 7,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "queued",
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
        });
        getGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 7,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 0,
                skipped_items: 0,
                failed_items: 0,
                error_message: null,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            count: 1,
            jobs: [
                {
                    gmail_message_id: "gmail-update-1",
                    thread_id: "thread-7",
                    from: "recruiter@company.com",
                    subject: "Interview scheduled",
                    date: "2025-01-15T12:00:00Z",
                    source: "company_email",
                    email_content: {
                        snippet: "Interview scheduled.",
                        body_text: "Your interview has been scheduled.",
                        from_email: "recruiter@company.com",
                        from_domain: "company.com",
                    },
                    classification: {
                        label: "INTERVIEW",
                        confidence: 0.9,
                        reasons: ["interview_phrase"],
                    },
                    job_draft: null,
                    update_items: {
                        status: "Interview",
                        follow_up_date: "2025-01-16",
                        company: mockJobs[0].company,
                        title: mockJobs[0].title,
                        notes: "Imported update",
                    },
                    extraction_candidates: {
                        title: [],
                        company: [],
                        location: [],
                        identifiers: { gmail_thread_id: [] },
                    },
                    match_candidates: [],
                    best_match: { job_id: mockJobs[0].id, company: mockJobs[0].company, title: mockJobs[0].title, status: mockJobs[0].status, match_level: "company_title", match_score: 0.84, match_reasons: ["matched_company", "matched_title"], requires_review: false },
                    import_item_id: 15,
                    import_status: "pending",
                    selected_action: "update",
                    linked_job_id: null,
                    already_processed: false,
                    needs_review: true,
                },
            ],
        });
        commitGmailImportMock.mockResolvedValue({
            session: {
                id: 7,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 1,
                skipped_items: 0,
                failed_items: 0,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            results: [],
        });

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));

        const selects = screen.getAllByRole("combobox");
        await userEvent.selectOptions(selects[1], "100");
        const statusInput = screen.getByDisplayValue("Interview");
        await userEvent.clear(statusInput);
        await userEvent.type(statusInput, "Offer");

        await userEvent.click(screen.getByRole("button", { name: /import selected/i }));

        await waitFor(() => {
            expect(commitGmailImportMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    session_id: 7,
                    items: [
                        expect.objectContaining({
                            gmail_message_id: "gmail-update-1",
                            action: "update",
                            target_job_id: mockJobs[0].id,
                            update_items: expect.objectContaining({
                                status: "Offer",
                            }),
                        }),
                    ],
                }),
            );
        });
    });

    test("shows processing state while polling preview", async () => {
        startGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 20,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "queued",
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
        });
        getGmailImportPreviewMock
            .mockResolvedValueOnce({
                session: {
                    id: 20,
                    start_date: "2025-01-01",
                    end_date: "2025-01-31",
                    status: "processing",
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
            })
            .mockResolvedValueOnce({
                session: {
                    id: 20,
                    start_date: "2025-01-01",
                    end_date: "2025-01-31",
                    status: "completed",
                    total_emails: 1,
                    new_items: 1,
                    cached_items: 0,
                    cache_hit: false,
                    imported_items: 0,
                    skipped_items: 0,
                    failed_items: 0,
                    error_message: null,
                    created_at: "2025-01-31T00:00:00Z",
                    updated_at: "2025-01-31T00:00:00Z",
                },
                count: 1,
                jobs: [
                    {
                        gmail_message_id: "gmail-processing-1",
                        thread_id: "thread-processing-1",
                        from: "recruiter@company.com",
                        subject: "Application received",
                        date: "2025-01-15T12:00:00Z",
                        source: "company_email",
                        email_content: {
                            snippet: "Thank you for applying.",
                            body_text: "Thank you for applying for the Backend Engineer position.",
                            from_email: "recruiter@company.com",
                            from_domain: "company.com",
                        },
                        classification: {
                            label: "NEW_APPLICATION",
                            confidence: 0.9,
                            reasons: ["confirmation_phrase"],
                        },
                        job_draft: {
                            title: "Backend Engineer",
                            company: "Company",
                            location: "Remote",
                            applied_date: "2025-01-15",
                            status: "Applied",
                            source: "Gmail",
                        },
                        update_items: null,
                        extraction_candidates: {
                            title: [],
                            company: [],
                            location: [],
                            identifiers: { gmail_thread_id: [] },
                        },
                        match_candidates: [],
                        best_match: null,
                        import_item_id: 30,
                        import_status: "pending",
                        selected_action: "create",
                        linked_job_id: null,
                        already_processed: false,
                        needs_review: true,
                    },
                ],
            });

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));

        expect(screen.getByText("Preparing Gmail preview...")).toBeInTheDocument();
        expect(await screen.findByText(/Suggested posting: Company · Backend Engineer/)).toBeInTheDocument();
    });

    test("shows create fields for unknown emails without existing suggestions", async () => {
        searchCompaniesMock.mockResolvedValue([]);
        startGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 40,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "queued",
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
        });
        getGmailImportPreviewMock.mockResolvedValue({
            session: {
                id: 40,
                start_date: "2025-01-01",
                end_date: "2025-01-31",
                status: "completed",
                total_emails: 1,
                new_items: 1,
                cached_items: 0,
                cache_hit: false,
                imported_items: 0,
                skipped_items: 0,
                failed_items: 0,
                error_message: null,
                created_at: "2025-01-31T00:00:00Z",
                updated_at: "2025-01-31T00:00:00Z",
            },
            count: 1,
            jobs: [
                {
                    gmail_message_id: "gmail-unknown-1",
                    thread_id: "thread-unknown-1",
                    from: "someone@company.com",
                    subject: "Checking in",
                    date: "2025-01-15T12:00:00Z",
                    source: "unknown",
                    email_content: {
                        snippet: "Quick note.",
                        body_text: "Quick note about your application.",
                        from_email: "someone@company.com",
                        from_domain: "company.com",
                    },
                    classification: {
                        label: "UNKNOWN",
                        confidence: 0.4,
                        reasons: ["uncertain_signal"],
                    },
                    job_draft: null,
                    update_items: null,
                    extraction_candidates: {
                        title: [],
                        company: [],
                        location: [],
                        identifiers: { gmail_thread_id: [] },
                    },
                    match_candidates: [],
                    best_match: null,
                    import_item_id: 41,
                    import_status: "pending",
                    selected_action: "skip",
                    linked_job_id: null,
                    already_processed: false,
                    needs_review: true,
                },
            ],
        });

        render(<GmailImportModal jobs={mockJobs} onClose={vi.fn()} onImported={vi.fn()} />);

        expect(await screen.findByText(/gmail connected/i)).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /fetch gmail jobs/i }));
        const actionSelect = screen.getAllByRole("combobox")[0];
        await userEvent.selectOptions(actionSelect, "create");

        expect(await screen.findByLabelText("Company")).toBeInTheDocument();
        expect(screen.getByLabelText("Title")).toBeInTheDocument();
        expect(screen.getByLabelText("Applied date")).toBeInTheDocument();
        expect(screen.getByLabelText("Status / result")).toBeInTheDocument();
    });
});
