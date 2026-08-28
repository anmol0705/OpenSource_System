import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { server } from "@/test/mocks/server";
import { API_BASE_URL } from "@/lib/api";
import { loadProfile } from "@/lib/storage";
import { ProfileForm } from "./ProfileForm";

async function fillMinimalValidForm() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/your name/i), "Ada Lovelace");

  await user.type(screen.getByLabelText(/language name/i), "Python");
  await user.selectOptions(screen.getByLabelText(/proficiency level/i), "advanced");
  await user.click(screen.getByRole("button", { name: /add language/i }));

  await user.click(screen.getByRole("checkbox", { name: /backend/i }));

  return user;
}

describe("ProfileForm", () => {
  it("renders the core fields", () => {
    render(<ProfileForm />);
    expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/language name/i)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /backend/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create profile/i })).toBeInTheDocument();
  });

  it("shows a loading state while the request is in flight", async () => {
    server.use(
      http.post(`${API_BASE_URL}/profiles`, async () => {
        await delay(50);
        return HttpResponse.json({
          id: "profile-1",
          name: "Ada Lovelace",
          skills: { languages: { Python: "advanced" }, domains: ["backend"] },
        });
      })
    );

    render(<ProfileForm />);
    const user = await fillMinimalValidForm();
    await user.click(screen.getByRole("button", { name: /create profile/i }));

    expect(
      await screen.findByRole("button", { name: /creating/i })
    ).toBeDisabled();
  });

  it("on success, stores the profile and shows a confirmation", async () => {
    server.use(
      http.post(`${API_BASE_URL}/profiles`, async () => {
        return HttpResponse.json({
          id: "profile-1",
          name: "Ada Lovelace",
          skills: { languages: { Python: "advanced" }, domains: ["backend"] },
        });
      })
    );

    render(<ProfileForm />);
    const user = await fillMinimalValidForm();
    await user.click(screen.getByRole("button", { name: /create profile/i }));

    const success = await screen.findByTestId("profile-success");
    expect(within(success).getByText(/ada lovelace/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(loadProfile()?.id).toBe("profile-1");
    });
  });

  it("shows a readable error message when the request fails", async () => {
    server.use(
      http.post(`${API_BASE_URL}/profiles`, async () => {
        return HttpResponse.json({ detail: "boom" }, { status: 500 });
      })
    );

    render(<ProfileForm />);
    const user = await fillMinimalValidForm();
    await user.click(screen.getByRole("button", { name: /create profile/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/boom/i);
  });
});
