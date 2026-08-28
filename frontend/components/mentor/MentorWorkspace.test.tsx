import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { server } from "@/test/mocks/server";
import { API_BASE_URL } from "@/lib/api";
import { loadPrContext, saveMentorContext } from "@/lib/storage";
import { MentorWorkspace } from "./MentorWorkspace";

vi.mock("@monaco-editor/react", () => ({
  default: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string | undefined) => void;
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

const SESSION_ID = "sess-1";

function seedContext() {
  saveMentorContext(SESSION_ID, {
    workspace_id: "ws-1",
    repo_full_name: "octo/widgets",
    target_file: "src/retry.py",
    original_content: "def retry():\n    pass\n",
    test_command: "python -m pytest",
    issue_title: "Retries fail silently",
    issue_body: "Issue #7: Retries fail silently",
    initial_hint: "What happens to the exception on the last retry attempt?",
    initial_hint_count: 1,
  });
}

beforeEach(seedContext);

describe("MentorWorkspace", () => {
  it("renders the issue, the first hint, hint counter, and the editor preloaded with original content", () => {
    render(<MentorWorkspace sessionId={SESSION_ID} />);

    expect(screen.getByText("Retries fail silently")).toBeInTheDocument();
    expect(
      screen.getByText(/what happens to the exception/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/hint 1 of 4/i)).toBeInTheDocument();
    expect(screen.getByTestId("monaco-editor")).toHaveValue("def retry():\n    pass\n");
  });

  it("shows a loading state while submitting an attempt", async () => {
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/mentor/${SESSION_ID}/submit-attempt`, async () => {
        await delay(50);
        return HttpResponse.json({
          tests_passed: false,
          test_output: "1 failed",
          hint: "Look at the except block more closely.",
          hint_count: 2,
        });
      })
    );
    const user = userEvent.setup();
    render(<MentorWorkspace sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /i've read this hint/i }));
    await user.click(screen.getByRole("button", { name: /run tests/i }));
    expect(await screen.findByText(/running tests/i)).toBeInTheDocument();
  });

  it("on a failing attempt, shows test output, animates in the new hint, and blocks another run until acknowledged", async () => {
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/mentor/${SESSION_ID}/submit-attempt`, () =>
        HttpResponse.json({
          tests_passed: false,
          test_output: "AssertionError: 1 failed",
          hint: "Look at the except block more closely.",
          hint_count: 2,
        })
      )
    );
    const user = userEvent.setup();
    render(<MentorWorkspace sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /i've read this hint/i }));
    await user.click(screen.getByRole("button", { name: /run tests/i }));

    expect(await screen.findByText(/assertionerror: 1 failed/i)).toBeInTheDocument();
    expect(screen.getByText(/look at the except block/i)).toBeInTheDocument();
    expect(screen.getByText(/hint 2 of 4/i)).toBeInTheDocument();

    const runButton = screen.getByRole("button", { name: /run tests/i });
    expect(runButton).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /i've read this hint/i }));
    expect(runButton).toBeEnabled();
  });

  it("on a passing attempt, shows a success state, saves PR context, and offers a Proceed to PR Review CTA", async () => {
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/mentor/${SESSION_ID}/submit-attempt`, () =>
        HttpResponse.json({
          tests_passed: true,
          test_output: "2 passed",
          hint: null,
          hint_count: 1,
        })
      )
    );
    const user = userEvent.setup();
    render(<MentorWorkspace sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /i've read this hint/i }));
    await user.click(screen.getByRole("button", { name: /run tests/i }));

    expect(await screen.findByText(/tests passed/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /proceed to pr review/i })).toHaveAttribute(
      "href",
      `/pr-review/${SESSION_ID}`
    );

    await waitFor(() => {
      expect(loadPrContext(SESSION_ID)?.final_content).toBe("def retry():\n    pass\n");
    });
  });

  it("shows a readable error message when submitting an attempt fails", async () => {
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/mentor/${SESSION_ID}/submit-attempt`, () =>
        HttpResponse.json({ detail: "sandbox unreachable" }, { status: 500 })
      )
    );
    const user = userEvent.setup();
    render(<MentorWorkspace sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /i've read this hint/i }));
    await user.click(screen.getByRole("button", { name: /run tests/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/sandbox unreachable/i);
  });
});
