import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { server } from "@/test/mocks/server";
import { API_BASE_URL } from "@/lib/api";
import { saveInvestigationContext, saveProfile } from "@/lib/storage";
import { InvestigateView } from "./InvestigateView";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const investigationResponse = {
  hypothesis: "The retry loop swallows the final exception",
  target_file: "src/retry.py",
  confidence: 0.82,
  iterations: 2,
  files_inspected: ["src/retry.py", "src/client.py"],
  history: [
    "iteration 1: Looked at client.py, suspect retry.py handles backoff incorrectly",
    "iteration 2: retry.py confirms the swallowed exception on the final attempt",
  ],
  files_with_history_checked: ["src/retry.py"],
};

function seedContext() {
  saveInvestigationContext({
    workspace_id: "ws-1",
    repo_full_name: "octo/widgets",
    issue_title: "Retries fail silently",
    issue_body: "Issue #7: Retries fail silently",
  });
  saveProfile({
    id: "profile-1",
    name: "Ada",
    skills: { languages: { Python: "advanced" }, domains: ["backend"] },
    proficiency: "advanced",
  });
}

beforeEach(() => {
  pushMock.mockReset();
});

describe("InvestigateView", () => {
  it("shows a loading state while the investigation runs", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/investigate`, async () => {
        await delay(50);
        return HttpResponse.json(investigationResponse);
      })
    );
    render(<InvestigateView />);
    expect(await screen.findByText(/investigating/i)).toBeInTheDocument();
  });

  it("renders the reasoning timeline, final confidence, and target file on success", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/investigate`, () =>
        HttpResponse.json(investigationResponse)
      )
    );
    render(<InvestigateView />);

    expect(await screen.findByText("src/retry.py")).toBeInTheDocument();
    expect(screen.getByText(/looked at client\.py/i)).toBeInTheDocument();
    expect(screen.getByText(/confirms the swallowed exception/i)).toBeInTheDocument();
    expect(screen.getByText("82", { exact: false })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start mentoring session/i })
    ).toBeInTheDocument();
  });

  it("shows a readable error message when the investigation fails", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/investigate`, () =>
        HttpResponse.json({ detail: "sandbox crashed" }, { status: 500 })
      )
    );
    render(<InvestigateView />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/sandbox crashed/i);
  });

  it("shows a message instead of investigating when there is no context", async () => {
    render(<InvestigateView />);
    expect(
      await screen.findByText(/no investigation in progress/i)
    ).toBeInTheDocument();
  });

  it("starting a mentoring session fetches file content, starts the session, and navigates", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/investigate`, () =>
        HttpResponse.json(investigationResponse)
      ),
      http.post(`${API_BASE_URL}/sandboxes/ws-1/run`, () =>
        HttpResponse.json({ exit_code: 0, output: "def retry():\n    pass\n" })
      ),
      http.post(`${API_BASE_URL}/sandboxes/ws-1/mentor/start`, () =>
        HttpResponse.json({ session_id: "sess-1", hint: null, hint_count: 0 })
      )
    );
    const user = userEvent.setup();
    render(<InvestigateView />);

    await user.click(
      await screen.findByRole("button", { name: /start mentoring session/i })
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/mentor/sess-1");
    });
  });
});
