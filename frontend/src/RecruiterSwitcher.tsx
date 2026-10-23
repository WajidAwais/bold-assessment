import type { Recruiter } from "./api";

function regionLabel(recruiter: Recruiter): string {
  return recruiter.role === "admin" ? "All Regions" : recruiter.regions.join(", ");
}

export function RecruiterSwitcher({
  recruiters,
  value,
  onChange,
}: {
  recruiters: Recruiter[];
  value: string;
  onChange: (recruiterId: string) => void;
}) {
  return (
    <label>
      Viewing as{" "}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {recruiters.map((r) => (
          <option key={r.id} value={r.id}>
            {r.full_name} ({regionLabel(r)})
          </option>
        ))}
      </select>
    </label>
  );
}
