export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "Could not reach the backend. Is it running?");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // no JSON body — fall back to statusText
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Profiles ----------

export interface ProfileSkills {
  languages: Record<string, string>;
  domains: string[];
}

export interface Profile {
  id: string;
  name: string;
  skills: ProfileSkills;
}

export interface CreateProfileRequest {
  name: string;
  languages: Record<string, string>;
  domains: string[];
}

export function createProfile(payload: CreateProfileRequest): Promise<Profile> {
  return request<Profile>("/profiles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------- Repositories ----------

export interface RepoScoreBreakdown {
  project_quality: number;
  maintainer_activity: number;
  contribution_accessibility: number;
  abandonment_risk_penalty: number;
  [key: string]: number;
}

export interface RepoResult {
  full_name: string;
  score: number;
  breakdown: RepoScoreBreakdown;
  stars: number;
}

export function discoverRepositories(
  query: string,
  limit = 10
): Promise<RepoResult[]> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return request<RepoResult[]>(`/repos/discover?${params.toString()}`, {
    method: "POST",
  });
}

export interface IssueScoreBreakdown {
  skill_fit: number;
  issue_clarity: number;
  learning_value_stub: number;
  merge_probability_stub: number;
  career_relevance_stub: number;
  novel_skill_value_stub: number;
  estimated_impact_stub: number;
  staleness_penalty: number;
  already_claimed_penalty: number;
  [key: string]: number;
}

export interface IssueResult {
  number: number;
  title: string;
  score: number;
  breakdown: IssueScoreBreakdown;
}

export function discoverIssues(
  fullName: string,
  profileId: string
): Promise<IssueResult[]> {
  const params = new URLSearchParams({ profile_id: profileId });
  return request<IssueResult[]>(
    `/repos/${encodeURIComponent(fullName)}/issues/discover?${params.toString()}`,
    { method: "POST" }
  );
}

// ---------- Sandboxes ----------

export interface CreateSandboxResponse {
  workspace_id: string;
}

export function createSandbox(repoCloneUrl: string): Promise<CreateSandboxResponse> {
  return request<CreateSandboxResponse>("/sandboxes", {
    method: "POST",
    body: JSON.stringify({ repo_clone_url: repoCloneUrl }),
  });
}

export interface RunCommandResponse {
  exit_code: number;
  output: string;
}

export function runSandboxCommand(
  workspaceId: string,
  command: string
): Promise<RunCommandResponse> {
  return request<RunCommandResponse>(`/sandboxes/${workspaceId}/run`, {
    method: "POST",
    body: JSON.stringify({ command }),
  });
}

export interface InvestigateRequest {
  issue_title: string;
  issue_body: string;
}

export interface InvestigateResponse {
  hypothesis: string;
  target_file: string;
  confidence: number;
  iterations: number;
  files_inspected: string[];
  history: string[];
  files_with_history_checked: string[];
}

export function investigate(
  workspaceId: string,
  payload: InvestigateRequest
): Promise<InvestigateResponse> {
  return request<InvestigateResponse>(`/sandboxes/${workspaceId}/investigate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type Proficiency = "beginner" | "intermediate" | "advanced";

export interface StartMentorRequest {
  issue_title: string;
  issue_body: string;
  target_file: string;
  original_content: string;
  test_command: string;
  proficiency: Proficiency;
}

export interface StartMentorResponse {
  session_id: string;
  hint: string | null;
  hint_count: number;
}

export function startMentorSession(
  workspaceId: string,
  payload: StartMentorRequest
): Promise<StartMentorResponse> {
  return request<StartMentorResponse>(`/sandboxes/${workspaceId}/mentor/start`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface SubmitAttemptRequest {
  human_attempt: string;
}

export interface SubmitAttemptResponse {
  tests_passed: boolean;
  test_output: string;
  hint: string | null;
  hint_count: number;
}

export function submitMentorAttempt(
  sessionId: string,
  payload: SubmitAttemptRequest
): Promise<SubmitAttemptResponse> {
  return request<SubmitAttemptResponse>(
    `/sandboxes/mentor/${sessionId}/submit-attempt`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export interface StartPRRequest {
  repo_full_name: string;
  branch_name: string;
  target_file: string;
  final_content: string;
  commit_message: string;
  pr_title: string;
  pr_body: string;
  test_command: string;
  issue_title: string;
  issue_body: string;
}

export interface StartPRResponse {
  session_id: string;
  status: string;
}

export function requestPrApproval(
  workspaceId: string,
  payload: StartPRRequest
): Promise<StartPRResponse> {
  return request<StartPRResponse>(`/sandboxes/${workspaceId}/pr/request-approval`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ApprovePRResponse {
  status: string;
  pr_number: number | null;
}

export function approvePr(prSessionId: string): Promise<ApprovePRResponse> {
  return request<ApprovePRResponse>(`/sandboxes/pr/${prSessionId}/approve`, {
    method: "POST",
  });
}
