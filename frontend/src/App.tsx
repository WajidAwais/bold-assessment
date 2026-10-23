import { useQuery } from "@tanstack/react-query";
import { fetchCandidates } from "./api";
import { CandidateTable } from "./CandidateTable";

export function App() {
  // Ticket 02 adds the Recruiter to this key; 05 adds search, status and paging.
  const page = 1;
  const candidates = useQuery({
    queryKey: ["candidates", { page }],
    queryFn: () => fetchCandidates(page),
  });

  return (
    <main>
      <h1>Candidates</h1>
      {candidates.isPending && <p role="status">Loading…</p>}
      {candidates.isError && <p role="alert">Couldn't load candidates: {candidates.error.message}</p>}
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
