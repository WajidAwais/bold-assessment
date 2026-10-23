import type { CandidateListItem } from "./api";

export function CandidateTable({ items }: { items: CandidateListItem[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Region</th>
          <th>Role</th>
          <th>Status</th>
          <th>Applied</th>
        </tr>
      </thead>
      <tbody>
        {items.map((c) => (
          <tr key={c.id}>
            <td>
              {c.first_name} {c.last_name}
            </td>
            <td>{c.email}</td>
            <td>{c.region}</td>
            <td>{c.desired_role ?? "—"}</td>
            <td>{c.status}</td>
            <td>{c.applied_date ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
