// Plain fetch wrappers for the backend. Types mirror the API's response models.

export type CandidateListItem = {
  id: number;
  legacy_id: string;
  first_name: string;
  last_name: string;
  email: string;
  region: string;
  desired_role: string | null;
  status: string;
  applied_date: string | null;
};

export type CandidateList = {
  items: CandidateListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type Recruiter = {
  id: string;
  full_name: string;
  role: "admin" | "recruiter";
  // Canonical Region codes, or ["*"] for an Admin.
  regions: string[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Not JSON; keep the status text.
    }
    throw new ApiError(response.status, `${response.status} ${detail}`);
  }
  return (await response.json()) as T;
}

export function fetchRecruiters(): Promise<Recruiter[]> {
  return getJson<Recruiter[]>("/api/v1/recruiters");
}

export function fetchCandidates(recruiterId: string, page: number): Promise<CandidateList> {
  const params = new URLSearchParams({ page: String(page) });
  return getJson<CandidateList>(`/api/v1/candidates?${params}`, {
    headers: { "X-Recruiter-Id": recruiterId },
  });
}
