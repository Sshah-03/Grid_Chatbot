import { apiRequest } from "./client";
import type { FetchRun, FetchRunDetail } from "../types";

export function aggregateSample(token: string, urls: string[]) {
  return apiRequest<{
    run_id: string;
    correlation_id: string;
    status: string;
    duration_ms: number;
    results: FetchRunDetail["results"];
  }>(
    "/integrations/aggregate-sample",
    { method: "POST", body: JSON.stringify({ urls }) },
    token
  );
}

export function listFetchRuns(token: string) {
  return apiRequest<{ items: FetchRun[]; total: number }>("/integrations/fetch-runs", {}, token);
}

export function getFetchRun(token: string, id: string) {
  return apiRequest<FetchRunDetail>(`/integrations/fetch-runs/${id}`, {}, token);
}
