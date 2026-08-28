import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { server } from "@/test/mocks/server";
import { API_BASE_URL } from "@/lib/api";
import { saveProfile } from "@/lib/storage";
import { DiscoverView } from "./DiscoverView";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

function seedProfile() {
  saveProfile({
    id: "profile-1",
    name: "Ada",
    skills: { languages: { Python: "advanced" }, domains: ["backend"] },
    proficiency: "advanced",
  });
}

const repoResults = [
  {
    full_name: "octo/widgets",
    score: 0.812,
    breakdown: {
      project_quality: 0.9,
      maintainer_activity: 0.8,
      contribution_accessibility: 0.7,
      abandonment_risk_penalty: 0.1,
    },
    stars: 1200,
  },
];

const issueResults = [
  {
    number: 42,
    title: "Fix flaky retry logic",
    score: 0.55,
    breakdown: {
      skill_fit: 0.6,
      issue_clarity: 0.5,
      learning_value_stub: 0.5,
      merge_probability_stub: 0.5,
      career_relevance_stub: 0.5,
      novel_skill_value_stub: 0.5,
      estimated_impact_stub: 0.5,
      staleness_penalty: 0.1,
      already_claimed_penalty: 0,
    },
  },
];

beforeEach(() => {
  pushMock.mockReset();
  seedProfile();
});

describe("DiscoverView", () => {
  it("shows a loading state while searching repositories", async () => {
    server.use(
      http.post(`${API_BASE_URL}/repos/discover`, async () => {
        await delay(50);
        return HttpResponse.json(repoResults);
      })
    );
    const user = userEvent.setup();
    render(<DiscoverView />);

    await user.type(screen.getByLabelText(/search query/i), "widgets");
    await user.click(screen.getByRole("button", { name: /search/i }));

    expect(await screen.findByText(/searching/i)).toBeInTheDocument();
  });

  it("shows scored repo cards with the full breakdown on success", async () => {
    server.use(
      http.post(`${API_BASE_URL}/repos/discover`, () => HttpResponse.json(repoResults))
    );
    const user = userEvent.setup();
    render(<DiscoverView />);

    await user.type(screen.getByLabelText(/search query/i), "widgets");
    await user.click(screen.getByRole("button", { name: /search/i }));

    expect(await screen.findByText("octo/widgets")).toBeInTheDocument();
    expect(screen.getByText(/project quality/i)).toBeInTheDocument();
    expect(screen.getByText(/maintainer activity/i)).toBeInTheDocument();
    expect(screen.getByText(/contribution accessibility/i)).toBeInTheDocument();
    expect(screen.getByText(/abandonment risk penalty/i)).toBeInTheDocument();
  });

  it("shows a readable error message when repo search fails", async () => {
    server.use(
      http.post(`${API_BASE_URL}/repos/discover`, () =>
        HttpResponse.json({ detail: "github rate limited" }, { status: 502 })
      )
    );
    const user = userEvent.setup();
    render(<DiscoverView />);

    await user.type(screen.getByLabelText(/search query/i), "widgets");
    await user.click(screen.getByRole("button", { name: /search/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/github rate limited/i);
  });

  it("clicking a repo card loads scored issues, and selecting one creates a sandbox and navigates", async () => {
    server.use(
      http.post(`${API_BASE_URL}/repos/discover`, () => HttpResponse.json(repoResults)),
      http.post(`${API_BASE_URL}/repos/octo%2Fwidgets/issues/discover`, () =>
        HttpResponse.json(issueResults)
      ),
      http.post(`${API_BASE_URL}/sandboxes`, () =>
        HttpResponse.json({ workspace_id: "ws-1" })
      )
    );
    const user = userEvent.setup();
    render(<DiscoverView />);

    await user.type(screen.getByLabelText(/search query/i), "widgets");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByText("octo/widgets"));

    expect(await screen.findByText("Fix flaky retry logic")).toBeInTheDocument();
    expect(screen.getByText(/skill fit/i)).toBeInTheDocument();

    await user.click(screen.getByText("Fix flaky retry logic"));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/investigate");
    });
  });
});
