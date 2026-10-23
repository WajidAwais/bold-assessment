import { STATUSES, type Status } from "./api";

export function CandidateFilters({
  search,
  onSearchChange,
  status,
  onStatusChange,
}: {
  search: string;
  onSearchChange: (search: string) => void;
  status: Status | null;
  onStatusChange: (status: Status | null) => void;
}) {
  return (
    <div className="filters">
      <label>
        Search{" "}
        <input
          type="search"
          value={search}
          placeholder="Name, email or role"
          maxLength={200}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
      <label>
        Status{" "}
        <select
          value={status ?? ""}
          onChange={(event) => onStatusChange((event.target.value || null) as Status | null)}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
