import type { Profile, Proficiency } from "./api";

const PROFILE_KEY = "esa_profile";
const INVESTIGATION_KEY = "esa_investigation";
const MENTOR_PREFIX = "esa_mentor_";
const PR_PREFIX = "esa_pr_";

export interface StoredProfile extends Profile {
  proficiency: Proficiency;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function saveProfile(profile: StoredProfile): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
}

export function loadProfile(): StoredProfile | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(PROFILE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredProfile;
  } catch {
    return null;
  }
}

export interface InvestigationContext {
  workspace_id: string;
  repo_full_name: string;
  issue_title: string;
  issue_body: string;
}

export function saveInvestigationContext(ctx: InvestigationContext): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(INVESTIGATION_KEY, JSON.stringify(ctx));
}

export function loadInvestigationContext(): InvestigationContext | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(INVESTIGATION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as InvestigationContext;
  } catch {
    return null;
  }
}

export interface MentorContext {
  workspace_id: string;
  repo_full_name: string;
  target_file: string;
  original_content: string;
  test_command: string;
  issue_title: string;
  issue_body: string;
  initial_hint: string | null;
  initial_hint_count: number;
}

export function saveMentorContext(sessionId: string, ctx: MentorContext): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(`${MENTOR_PREFIX}${sessionId}`, JSON.stringify(ctx));
}

export function loadMentorContext(sessionId: string): MentorContext | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(`${MENTOR_PREFIX}${sessionId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MentorContext;
  } catch {
    return null;
  }
}

export interface PrContext {
  workspace_id: string;
  repo_full_name: string;
  target_file: string;
  original_content: string;
  final_content: string;
  test_command: string;
  issue_title: string;
  issue_body: string;
  teaching_summary?: string;
}

export function savePrContext(mentorSessionId: string, ctx: PrContext): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(`${PR_PREFIX}${mentorSessionId}`, JSON.stringify(ctx));
}

export function loadPrContext(mentorSessionId: string): PrContext | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(`${PR_PREFIX}${mentorSessionId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PrContext;
  } catch {
    return null;
  }
}
