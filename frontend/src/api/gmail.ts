import { api } from "./client";
import type {
  GmailImportCommitRequest,
  GmailImportCommitResponse,
  GmailImportPreviewResponse,
  GmailImportPreviewStartResponse,
  GmailStatusResponse,
} from "../types/gmail";

export async function getGmailStatus(): Promise<GmailStatusResponse> {
  const res = await api.get<GmailStatusResponse>("/gmail/status");
  return res.data;
}

export async function getGmailAuthUrl(frontendRedirect: string): Promise<string> {
  const res = await api.get<{ auth_url: string }>("/gmail/auth/url", {
    params: { frontend_redirect: frontendRedirect },
  });
  return res.data.auth_url;
}

export async function startGmailImportPreview(
  startDate: string,
  endDate: string,
): Promise<GmailImportPreviewStartResponse> {
  const res = await api.post<GmailImportPreviewStartResponse>(
    "/gmail/import/preview",
    null,
    {
      params: {
        start_date: startDate,
        end_date: endDate,
      },
      timeout: 120000,
    },
  );
  return res.data;
}

export async function getGmailImportPreview(sessionId: number): Promise<GmailImportPreviewResponse> {
  const res = await api.get<GmailImportPreviewResponse>(`/gmail/import/preview/${sessionId}`, {
    timeout: 120000,
  });
  return res.data;
}

export async function commitGmailImport(
  payload: GmailImportCommitRequest,
): Promise<GmailImportCommitResponse> {
  const res = await api.post<GmailImportCommitResponse>("/gmail/import/commit", payload);
  return res.data;
}
