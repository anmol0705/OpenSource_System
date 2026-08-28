import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { server } from "@/test/mocks/server";
import { API_BASE_URL } from "@/lib/api";
import { savePrContext } from "@/lib/storage";
import { PrReviewView } from "./PrReviewView";

const SESSION_ID = "sess-1";

function seedContext() {
  savePrContext(SESSION_ID, {
    workspace_id: "ws-1",
    repo_full_name: "octo/widgets",
    target_file: "src/retry.py",
    original_content: "def retry():\n    pass\n",
    final_content: "def retry():\n    return True\n",
    test_command: "python -m pytest",
    issue_title: "Retries fail silently",
    issue_body: "Issue #7: Retries fail silently",
  });
}

describe("PrReviewView", () => {
  it("shows a message when there is no PR context", () => {
    render(<PrReviewView sessionId={SESSION_ID} />);
    expect(screen.getByText(/no passing mentor session found/i)).toBeInTheDocument();
  });

  it("renders the diff between original and final content", async () => {
    seedContext();
    render(<PrReviewView sessionId={SESSION_ID} />);
    expect(await screen.findByText(/return true/i)).toBeInTheDocument();
  });

  it("shows a loading state while approving and pushing", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/pr/request-approval`, async () => {
        await delay(30);
        return HttpResponse.json({ session_id: "pr-sess-1", status: "awaiting_human_approval" });
      }),
      http.post(`${API_BASE_URL}/sandboxes/pr/pr-sess-1/approve`, async () => {
        await delay(30);
        return HttpResponse.json({ status: "pushed", pr_number: 99 });
      })
    );
    const user = userEvent.setup();
    render(<PrReviewView sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /approve & push/i }));
    expect(await screen.findByText(/pushing/i)).toBeInTheDocument();
  });

  it("on success, shows the real PR URL as a clickable link", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/pr/request-approval`, () =>
        HttpResponse.json({ session_id: "pr-sess-1", status: "awaiting_human_approval" })
      ),
      http.post(`${API_BASE_URL}/sandboxes/pr/pr-sess-1/approve`, () =>
        HttpResponse.json({ status: "pushed", pr_number: 99 })
      )
    );
    const user = userEvent.setup();
    render(<PrReviewView sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /approve & push/i }));

    const link = await screen.findByRole("link", { name: /view pull request/i });
    expect(link).toHaveAttribute("href", "https://github.com/octo/widgets/pull/99");
  });

  it("shows a readable error message when approval fails", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/pr/request-approval`, () =>
        HttpResponse.json({ detail: "push rejected" }, { status: 500 })
      )
    );
    const user = userEvent.setup();
    render(<PrReviewView sessionId={SESSION_ID} />);

    await user.click(screen.getByRole("button", { name: /approve & push/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/push rejected/i);
  });

  it("lets the reviewer save change-request feedback instead of approving blind", async () => {
    seedContext();
    server.use(
      http.post(`${API_BASE_URL}/sandboxes/ws-1/pr/request-approval`, () =>
        HttpResponse.json({ session_id: "pr-sess-1", status: "awaiting_human_approval" })
      )
    );
    const user = userEvent.setup();
    render(<PrReviewView sessionId={SESSION_ID} />);

    await user.type(
      screen.getByLabelText(/change request feedback/i),
      "Please add a test for the timeout case."
    );
    await user.click(screen.getByRole("button", { name: /request changes/i }));

    const saved = await screen.findByTestId("saved-feedback");
    expect(saved).toHaveTextContent(/please add a test for the timeout case/i);
    expect(screen.queryByRole("link", { name: /view pull request/i })).not.toBeInTheDocument();
  });
});
