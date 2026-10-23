import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, fetchCandidates, fetchRecruiters } from "./api";
import { CandidateTable } from "./CandidateTable";
import { RecruiterSwitcher } from "./RecruiterSwitcher";

// Client errors (401/403/422) won't fix themselves; only retry the rest.
function retryUnlessClientError(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export function App() {
  const recruiters = useQuery({ queryKey: ["recruiters"], queryFn: fetchRecruiters });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const recruiterId = selectedId ?? recruiters.data?.[0]?.id ?? null;

  // Ticket 05 adds search, status and paging.
  const page = 1;
  const candidates = useQuery({
    // The Recruiter ID is part of the key, so one Recruiter's cached rows are
    // never shown to another.
    queryKey: ["candidates", recruiterId, { page }],
    queryFn: () => fetchCandidates(recruiterId!, page),
    enabled: recruiterId !== null,
    retry: retryUnlessClientError,
  });

  return (
    <main>
      <h1>Candidates</h1>
      {recruiters.isPending && <p role="status">Loading recruiters…</p>}
      {recruiters.isError && (
        <p role="alert">Couldn't load recruiters: {recruiters.error.message}</p>
      )}
      {recruiters.isSuccess && recruiterId !== null && (
        <RecruiterSwitcher
          recruiters={recruiters.data}
          value={recruiterId}
          onChange={setSelectedId}
        />
      )}
      {recruiterId !== null && candidates.isPending && <p role="status">Loading…</p>}
      {candidates.isError && (
        <p role="alert">Couldn't load candidates: {candidates.error.message}</p>
      )}
      {candidates.isSuccess &&
        (candidates.data.items.length === 0 ? (
          <p>No candidates.</p>
        ) : (
          <>
            <CandidateTable items={candidates.data.items} />
            <p>{candidates.data.total} candidates</p>
          </>
        ))}
    </main>
  );
}
