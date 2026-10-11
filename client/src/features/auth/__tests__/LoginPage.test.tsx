import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "../pages/LoginPage";
import * as AuthContextModule from "@/context/AuthContext";
import { UI_STRINGS } from "@/lib/strings.id";

describe("LoginPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  const mockLogin = vi.fn().mockResolvedValue(undefined);
  const mockRegisterDemo = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    vi.restoreAllMocks();

    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: mockLogin,
      registerDemo: mockRegisterDemo,
      logout: vi.fn(),
    });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders landing hero and judge onboarding button", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>,
      );
    });

    expect(container.textContent).toContain("EcoTrack");
    expect(container.textContent).toContain(
      "Ubah Catatan Tangan Menjadi Data Dampak Nyata.",
    );
    expect(container.textContent).toContain(UI_STRINGS.judgeAccessTitle);
    expect(container.textContent).toContain(UI_STRINGS.judgeAccessButton);
  });

  it("triggers registerDemo when judge demo button is clicked", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>,
      );
    });

    const buttons = Array.from(container.querySelectorAll("button"));
    const demoButton = buttons.find((btn) =>
      btn.textContent?.includes(UI_STRINGS.judgeAccessButton),
    );

    expect(demoButton).toBeDefined();

    await act(async () => {
      demoButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(mockRegisterDemo).toHaveBeenCalledTimes(1);
  });
});
