import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  commitGmailImport,
  getGmailAuthUrl,
  getGmailImportPreview,
  getGmailStatus,
  startGmailImportPreview,
} from "../api/gmail";
import { searchCompanies, searchJobPostings } from "../api/jobs";
import type { CompanySuggestion, Job, JobPostingSuggestion } from "../types/job";
import type {
  GmailImportAction,
  GmailImportItemSelection,
  GmailImportPreviewResponse,
  GmailJobDraft,
  GmailParsedMessageReview,
  GmailUpdateItems,
} from "../types/gmail";

const PREVIEW_POLL_INTERVAL_MS = 250;
const PREVIEW_POLL_TIMEOUT_MS = 180000;
const PREVIEW_TIMEOUT_MESSAGE =
  "Gmail import preview timed out while waiting for results. The preview may still be processing; please try again in a moment.";

type ReviewState = {
  include: boolean;
  action: GmailImportAction;
  targetJobId: number | null;
  selectedPostingId: number | null;
  jobDraft: GmailJobDraft | null;
  updateItems: GmailUpdateItems | null;
  showSnippet: boolean;
  showBody: boolean;
};

const today = new Date().toISOString().slice(0, 10);
const defaultStart = new Date(Date.now() - 1000 * 60 * 60 * 24 * 90).toISOString().slice(0, 10);

function buildFallbackDraft(review: GmailParsedMessageReview): GmailJobDraft | null {
  if (review.job_draft) {
    return { ...review.job_draft };
  }
  if (!review.update_items) {
    return null;
  }
  return {
    title: review.update_items.title ?? "",
    company: review.update_items.company ?? "",
    location: "Unknown",
    applied_date: review.update_items.follow_up_date ?? null,
    follow_up_date: review.update_items.follow_up_date ?? null,
    status: review.update_items.status ?? "Applied",
    source: "Gmail",
    notes: review.update_items.notes ?? "Created from Gmail update. Review before saving.",
    gmail_thread_id: review.update_items.gmail_thread_id ?? review.thread_id ?? null,
  };
}

function buildEmptyDraft(review: GmailParsedMessageReview): GmailJobDraft {
  return {
    title: "",
    company: "",
    location: "Unknown",
    applied_date: review.date ? review.date.slice(0, 10) : null,
    follow_up_date: review.date ? review.date.slice(0, 10) : null,
    status: review.classification.label === "UNKNOWN" ? "Applied" : (review.update_items?.status ?? "Applied"),
    source: "Gmail",
    notes: "Imported from Gmail. Review before saving.",
    gmail_thread_id: review.thread_id ?? null,
  };
}

function initialStateForReview(review: GmailParsedMessageReview): ReviewState {
  const defaultAction =
    review.selected_action ??
    (review.update_items && !review.best_match ? "create" : review.job_draft ? "create" : review.update_items ? "update" : "skip");
  return {
    include: !review.already_processed,
    action: defaultAction,
    targetJobId: review.best_match?.job_id ?? null,
    selectedPostingId: null,
    jobDraft: buildFallbackDraft(review) ?? (defaultAction === "create" ? buildEmptyDraft(review) : null),
    updateItems: review.update_items ? { ...review.update_items } : null,
    showSnippet: false,
    showBody: false,
  };
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error) && (error.code === "ECONNABORTED" || error.message.toLowerCase().includes("timeout"))) {
    return PREVIEW_TIMEOUT_MESSAGE;
  }
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  if (error instanceof Error) {
    if (error.message === "__gmail_preview_poll_timeout__") {
      return PREVIEW_TIMEOUT_MESSAGE;
    }
    if (error.message.startsWith("Failed to fetch Gmail import preview")) {
      return error.message;
    }
    if (error.message.startsWith("Failed to import selected Gmail items")) {
      return error.message;
    }
  }
  return fallback;
}

export default function GmailImportModal({
  onClose,
  onImported,
  jobs,
}: {
  onClose: () => void;
  onImported: () => void;
  jobs: Job[];
}) {
  const [gmailStatus, setGmailStatus] = useState<{
    authorized: boolean;
    message?: string;
    token_expired?: boolean;
    requires_reauth?: boolean;
  } | null>(null);
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(today);
  const [preview, setPreview] = useState<GmailImportPreviewResponse | null>(null);
  const [reviewStates, setReviewStates] = useState<Record<string, ReviewState>>({});
  const [companySuggestions, setCompanySuggestions] = useState<Record<string, CompanySuggestion[]>>({});
  const [postingSuggestions, setPostingSuggestions] = useState<Record<string, JobPostingSuggestion[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [importing, setImporting] = useState(false);

  const previewJobs = preview?.jobs ?? [];

  useEffect(() => {
    void loadStatus();
  }, []);

  async function loadStatus() {
    setLoadingStatus(true);
    setError(null);
    try {
      const status = await getGmailStatus();
      setGmailStatus(status);
    } catch (loadError) {
      setError(getErrorMessage(loadError, "Failed to load Gmail connection status."));
    } finally {
      setLoadingStatus(false);
    }
  }

  async function handleConnectGmail() {
    setError(null);
    try {
      const authUrl = await getGmailAuthUrl(`${window.location.origin}/jobs`);
      window.location.assign(authUrl);
    } catch (connectError) {
      setError(getErrorMessage(connectError, "Failed to start Gmail authorization."));
    }
  }

  async function pollForPreview(sessionId: number): Promise<GmailImportPreviewResponse> {
    const deadline = Date.now() + PREVIEW_POLL_TIMEOUT_MS;

    while (Date.now() < deadline) {
      const response = await getGmailImportPreview(sessionId);
      console.log("Gmail import preview poll response", response);
      if (response.session.status === "completed") {
        return response;
      }
      if (response.session.status === "failed") {
        throw new Error(response.session.error_message ?? "Failed to fetch Gmail import preview.");
      }
      await new Promise((resolve) => window.setTimeout(resolve, PREVIEW_POLL_INTERVAL_MS));
    }

    throw new Error("__gmail_preview_poll_timeout__");
  }

  async function handleFetchPreview() {
    if (!startDate || !endDate) {
      setError("Choose both a start date and an end date.");
      return;
    }
    setFetching(true);
    setError(null);
    try {
      setPreview(null);
      const startResponse = await startGmailImportPreview(startDate, endDate);
      console.log("Started Gmail import preview", startResponse);
      const response = await pollForPreview(startResponse.session.id);
      setPreview(response);
      setReviewStates(
        Object.fromEntries(response.jobs.map((job) => [job.gmail_message_id, initialStateForReview(job)])),
      );
      await Promise.all(
        response.jobs.map(async (job) => {
          const company = job.job_draft?.company ?? job.update_items?.company ?? "";
          if (company) {
            await loadCompanySuggestions(job.gmail_message_id, company);
            await loadPostingSuggestions(job.gmail_message_id, company);
          }
        }),
      );
    } catch (fetchError) {
      console.error("Failed to fetch Gmail import preview", fetchError);
      setError(getErrorMessage(fetchError, "Failed to fetch Gmail import preview."));
    } finally {
      setFetching(false);
    }
  }

  function updateReviewState(messageId: string, updater: (current: ReviewState) => ReviewState) {
    setReviewStates((current) => ({
      ...current,
      [messageId]: updater(current[messageId]),
    }));
  }

  async function loadCompanySuggestions(messageId: string, query: string) {
    if (!query.trim()) {
      setCompanySuggestions((current) => ({ ...current, [messageId]: [] }));
      return;
    }
    const suggestions = await searchCompanies(query);
    setCompanySuggestions((current) => ({ ...current, [messageId]: suggestions }));
  }

  async function loadPostingSuggestions(messageId: string, company: string, query = "") {
    if (!company.trim()) {
      setPostingSuggestions((current) => ({ ...current, [messageId]: [] }));
      return;
    }
    const suggestions = await searchJobPostings(company, query);
    setPostingSuggestions((current) => ({ ...current, [messageId]: suggestions }));
  }

  const selectedCount = useMemo(
    () => Object.values(reviewStates).filter((state) => state.include && state.action !== "skip").length,
    [reviewStates],
  );

  async function handleImportSelected() {
    if (!preview) {
      return;
    }

    const items: GmailImportItemSelection[] = preview.jobs.map((job) => {
      const state = reviewStates[job.gmail_message_id];
      if (!state || !state.include) {
        return { gmail_message_id: job.gmail_message_id, action: "skip" as const };
      }
      return {
        gmail_message_id: job.gmail_message_id,
        action: state.action,
        target_job_id: state.action === "update" ? state.targetJobId : null,
        job_draft: state.action === "create" ? state.jobDraft : null,
        update_items: state.action === "update" ? state.updateItems : null,
      };
    });

    setImporting(true);
    setError(null);
    try {
      await commitGmailImport({
        session_id: preview.session.id,
        items,
      });
      onImported();
      onClose();
    } catch (importError) {
      console.error("Failed to import selected Gmail items", importError);
      setError(getErrorMessage(importError, "Failed to import selected Gmail items."));
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="w-full max-w-7xl rounded-2xl bg-white p-6 shadow-xl">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Import Gmail Jobs</h2>
          <p className="mt-1 text-sm text-gray-600">
            Preview likely job emails, expand to inspect the message, then choose whether each item should create or update a listing.
          </p>
        </div>
      </div>

      {loadingStatus ? (
        <p className="text-sm text-gray-600">Checking Gmail connection...</p>
      ) : gmailStatus?.authorized ? (
        <div className="mb-5 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Gmail connected{gmailStatus.token_expired ? ", token will refresh on use." : "."}
        </div>
      ) : (
        <div className="mb-5 rounded-xl border border-yellow-200 bg-yellow-50 p-4">
          <p className="text-sm text-yellow-900">
            {gmailStatus?.message ?? "Connect Gmail before importing job emails."}
          </p>
          <button
            type="button"
            onClick={handleConnectGmail}
            className="mt-3 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Connect Gmail
          </button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className="rounded-xl border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            className="rounded-xl border border-gray-300 px-3 py-2"
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleFetchPreview}
          disabled={!gmailStatus?.authorized || fetching}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          {fetching ? "Fetching..." : "Fetch Gmail jobs"}
        </button>
        {fetching && !preview ? <span className="text-sm text-gray-600">Preparing Gmail preview...</span> : null}
        {preview ? (
          <span className="text-sm text-gray-600">
            {preview.count} emails found, {selectedCount} selected, {preview.session.cached_items} cached
            {preview.session.cache_hit ? " from the date-range cache" : ""}
          </span>
        ) : null}
      </div>

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}

      {preview ? (
        <div className="mt-6 space-y-4">
          {previewJobs.map((job) => {
            const state = reviewStates[job.gmail_message_id];
            if (!state) {
              return null;
            }

            const compactCompany = state.jobDraft?.company ?? state.updateItems?.company ?? "Unknown company";
            const compactTitle = state.jobDraft?.title ?? state.updateItems?.title ?? "Unknown title";
            const itemCompanySuggestions = companySuggestions[job.gmail_message_id] ?? [];
            const itemPostingSuggestions = postingSuggestions[job.gmail_message_id] ?? [];
            const selectedPosting = itemPostingSuggestions.find((posting) => posting.id === state.selectedPostingId) ?? null;
            const matchingJobs = selectedPosting
              ? jobs.filter(
                  (existingJob) =>
                    existingJob.posting_id === selectedPosting.id ||
                    (existingJob.company === selectedPosting.company && existingJob.title === selectedPosting.title),
                )
              : [];

            return (
              <div key={job.gmail_message_id} className="rounded-2xl border border-gray-200 bg-gray-50 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                        {job.classification.label}
                      </span>
                      {job.already_processed ? (
                        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                          Already handled
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-3 text-xs uppercase tracking-wide text-gray-500">Sender</p>
                    <p className="text-sm font-medium text-gray-900">{job.from}</p>
                    <p className="mt-3 text-xs uppercase tracking-wide text-gray-500">Subject</p>
                    <p className="text-base font-medium text-gray-900">{job.subject}</p>
                    <p className="mt-3 text-xs uppercase tracking-wide text-gray-500">Snippet</p>
                    <p className="text-sm text-gray-700">{job.email_content.snippet || "No snippet available."}</p>
                    <p className="mt-3 text-xs text-gray-500">
                      Suggested posting: {compactCompany} · {compactTitle}
                    </p>
                  </div>

                  <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-4">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={state.include}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            include: event.target.checked,
                          }))
                        }
                      />
                      Include in import
                    </label>
                    <label className="mt-3 block text-sm text-gray-700">
                      Action
                      <select
                        value={state.action}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            action: event.target.value as GmailImportAction,
                            jobDraft:
                              event.target.value === "create"
                                ? current.jobDraft ?? buildFallbackDraft(job) ?? buildEmptyDraft(job)
                                : current.jobDraft,
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      >
                        <option value="skip">Skip</option>
                        <option value="create">Create job</option>
                        <option value="update">Update existing job</option>
                      </select>
                    </label>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      updateReviewState(job.gmail_message_id, (current) => ({
                        ...current,
                        showSnippet: !current.showSnippet,
                      }))
                    }
                    className="rounded-xl border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-white"
                  >
                    {state.showSnippet ? "Hide email" : "See email"}
                  </button>
                  {state.showSnippet ? (
                    <button
                      type="button"
                      onClick={() =>
                        updateReviewState(job.gmail_message_id, (current) => ({
                          ...current,
                          showBody: !current.showBody,
                        }))
                      }
                      className="rounded-xl border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-white"
                    >
                      {state.showBody ? "Hide full email" : "Expand full email"}
                    </button>
                  ) : null}
                </div>

                {state.showSnippet ? (
                  <div className="mt-4 rounded-2xl bg-white p-4">
                    <p className="text-sm text-gray-700">{job.email_content.snippet || "No snippet available."}</p>
                    {state.showBody ? (
                      <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-gray-800">
                        {job.email_content.body_text || "No email body available."}
                      </pre>
                    ) : null}
                  </div>
                ) : null}

                {state.action === "create" && state.jobDraft ? (
                  <div className="mt-4 grid gap-3 rounded-2xl border border-emerald-200 bg-white p-4 md:grid-cols-2">
                    <label className="text-sm text-gray-700">
                      Company
                      <input
                        value={state.jobDraft.company ?? ""}
                        onChange={async (event) => {
                          const value = event.target.value;
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            jobDraft: { ...current.jobDraft, company: value },
                          }));
                          await loadCompanySuggestions(job.gmail_message_id, value);
                        }}
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                      {itemCompanySuggestions.length > 0 ? (
                        <div className="mt-2 rounded-xl border border-gray-200 bg-gray-50 p-2">
                          {itemCompanySuggestions.map((suggestion) => (
                            <button
                              key={suggestion.company}
                              type="button"
                              className="block w-full rounded-lg px-2 py-1 text-left text-sm text-gray-700 hover:bg-white"
                              onClick={() =>
                                updateReviewState(job.gmail_message_id, (current) => ({
                                  ...current,
                                  jobDraft: { ...current.jobDraft, company: suggestion.company },
                                }))
                              }
                            >
                              {suggestion.company}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </label>
                    <label className="text-sm text-gray-700">
                      Title
                      <input
                        value={state.jobDraft.title ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            jobDraft: { ...current.jobDraft, title: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <label className="text-sm text-gray-700">
                      Applied date
                      <input
                        type="date"
                        value={state.jobDraft.applied_date ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            jobDraft: { ...current.jobDraft, applied_date: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <label className="text-sm text-gray-700">
                      Status / result
                      <input
                        value={state.jobDraft.status ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            jobDraft: { ...current.jobDraft, status: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                  </div>
                ) : null}

                {state.action === "update" && state.updateItems ? (
                  <div className="mt-4 grid gap-3 rounded-2xl border border-blue-200 bg-white p-4 md:grid-cols-2">
                    <label className="text-sm text-gray-700">
                      Company
                      <input
                        value={state.updateItems.company ?? ""}
                        onChange={async (event) => {
                          const value = event.target.value;
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            updateItems: { ...current.updateItems, company: value },
                          }));
                          await loadCompanySuggestions(job.gmail_message_id, value);
                          await loadPostingSuggestions(job.gmail_message_id, value);
                        }}
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                      {itemCompanySuggestions.length > 0 ? (
                        <div className="mt-2 rounded-xl border border-gray-200 bg-gray-50 p-2">
                          {itemCompanySuggestions.map((suggestion) => (
                            <button
                              key={suggestion.company}
                              type="button"
                              className="block w-full rounded-lg px-2 py-1 text-left text-sm text-gray-700 hover:bg-white"
                              onClick={async () => {
                                updateReviewState(job.gmail_message_id, (current) => ({
                                  ...current,
                                  updateItems: { ...current.updateItems, company: suggestion.company },
                                }));
                                await loadPostingSuggestions(job.gmail_message_id, suggestion.company);
                              }}
                            >
                              {suggestion.company}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </label>
                    <label className="text-sm text-gray-700">
                      Job posting
                      <select
                        value={state.selectedPostingId ?? ""}
                        onChange={(event) => {
                          const postingId = event.target.value ? Number(event.target.value) : null;
                          const posting = itemPostingSuggestions.find((entry) => entry.id === postingId) ?? null;
                          const relatedJobs = posting
                            ? jobs.filter(
                                (existingJob) =>
                                  existingJob.posting_id === posting.id ||
                                  (existingJob.company === posting.company && existingJob.title === posting.title),
                              )
                            : [];
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            selectedPostingId: postingId,
                            targetJobId: relatedJobs[0]?.id ?? null,
                          }));
                        }}
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      >
                        <option value="">Select a posting</option>
                        {itemPostingSuggestions.map((posting) => (
                          <option key={posting.id} value={posting.id}>
                            {posting.title}
                          </option>
                        ))}
                      </select>
                    </label>
                    {matchingJobs.length > 0 ? (
                      <label className="text-sm text-gray-700">
                        Existing job
                        <select
                          value={state.targetJobId ?? ""}
                          onChange={(event) =>
                            updateReviewState(job.gmail_message_id, (current) => ({
                              ...current,
                              targetJobId: event.target.value ? Number(event.target.value) : null,
                            }))
                          }
                          className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                        >
                          {matchingJobs.map((existingJob) => (
                            <option key={existingJob.id} value={existingJob.id}>
                              {existingJob.company} - {existingJob.title}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
                        No existing job is linked to this posting yet. Keeping this as an update will create a new partial job from the known fields.
                      </div>
                    )}
                    <label className="text-sm text-gray-700">
                      Title
                      <input
                        value={state.updateItems.title ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            updateItems: { ...current.updateItems, title: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <label className="text-sm text-gray-700">
                      Date
                      <input
                        type="date"
                        value={state.updateItems.follow_up_date ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            updateItems: { ...current.updateItems, follow_up_date: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <label className="text-sm text-gray-700">
                      Status / result
                      <input
                        value={state.updateItems.status ?? ""}
                        onChange={(event) =>
                          updateReviewState(job.gmail_message_id, (current) => ({
                            ...current,
                            updateItems: { ...current.updateItems, status: event.target.value },
                          }))
                        }
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"
                      />
                    </label>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="mt-6 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleImportSelected}
          disabled={!preview || importing}
          className="rounded-xl bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          {importing ? "Importing..." : "Import selected"}
        </button>
      </div>
    </div>
  );
}
