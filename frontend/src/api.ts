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
    throw new ApiError(response.status, `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function fetchCandidates(page: number): Promise<CandidateList> {
  const params = new URLSearchParams({ page: String(page) });
  return getJson<CandidateList>(`/api/v1/candidates?${params}`);
}
