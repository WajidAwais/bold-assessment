import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, fetchCandidates, fetchRecruiters, type Status } from "./api";
import { CandidateFilters } from "./CandidateFilters";
import { CandidateTable } from "./CandidateTable";
import { Pager } from "./Pager";
import { RecruiterSwitcher } from "./RecruiterSwitcher";
import { useDebouncedValue } from "./useDebouncedValue";

const SEARCH_DEBOUNCE_MS = 300;

// Client errors (401/403/422) won't fix themselves; only retry the rest.
function retryUnlessClientError(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export function App() {
  const recruiters = useQuery({ queryKey: ["recruiters"], queryFn: fetchRecruiters });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const recruiterId = selectedId ?? recruiters.data?.[0]?.id ?? null;

  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim(), SEARCH_DEBOUNCE_MS);
  const [status, setStatus] = useState<Status | null>(null);

  // The page belongs to one Recruiter, search and status. When any of them
  // changes, the stored page no longer applies and we're back on page 1, in
  // the same render, so no request for a stale page is ever made.
  const filtersKey = JSON.stringify([recruiterId, search, status]);
  const [pageState, setPageState] = useState({ filtersKey, page: 1 });
  if (pageState.filtersKey !== filtersKey) {
    // Store the reset too (React's "adjust state while rendering"), or going
    // back to earlier filters would bring back the page they were on.
    setPageState({ filtersKey, page: 1 });
  }
  const page = pageState.filtersKey === filtersKey ? pageState.page : 1;
  const setPage = (next: number) => setPageState({ filtersKey, page: next });

  const candidates = useQuery({
    // Every input is in the key, the Recruiter ID first, so one Recruiter's
    // cached rows are never shown to another.
    queryKey: ["candidates", recruiterId, { search, status, page }],
    queryFn: () => fetchCandidates(recruiterId!, { search, status, page }),
    enabled: recruiterId !== null,
    retry: retryUnlessClientError,
    // Keep the previous page on screen while the next loads, but only for the
    // same Recruiter: switching Recruiter shows a loading state, never their rows.
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === recruiterId ? previous : undefined,
  });

  return (
    <main>
      <h1>Candidates</h1>
      {recruiters.isPending && <p role="status">Loading recruiters…</p>}
      {recruiters.isError && (
        <p role="alert">Couldn't load recruiters: {recruiters.error.message}</p>
      )}
      {recruiters.isSuccess && recruiterId !== null && (
        <div className="toolbar">
          <RecruiterSwitcher
            recruiters={recruiters.data}
            value={recruiterId}
            onChange={setSelectedId}
          />
          <CandidateFilters
            search={searchInput}
            onSearchChange={setSearchInput}
            status={status}
            onStatusChange={setStatus}
          />
        </div>
      )}
      {recruiterId !== null && candidates.isPending && <p role="status">Loading…</p>}
      {candidates.isPlaceholderData && <p role="status">Updating…</p>}
      {candidates.isError && (
        <p role="alert">Couldn't load candidates: {candidates.error.message}</p>
      )}
      {candidates.isSuccess && (
        <div aria-busy={candidates.isPlaceholderData} className="results">
          {candidates.data.items.length === 0 ? (
            <p>No candidates match.</p>
          ) : (
            <CandidateTable items={candidates.data.items} />
          )}
          <Pager
            page={page}
            pageSize={candidates.data.page_size}
            total={candidates.data.total}
            onPageChange={setPage}
          />
        </div>
      )}
    </main>
  );
}
