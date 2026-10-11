import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../pages/DashboardPage";
import * as dashboardService from "@/services/dashboard";
import type { DashboardSummary } from "@/types/dashboard";

function createMockSummary(isDemo: boolean): DashboardSummary {
  return {
    period: { from: "2026-09-01", to: "2026-09-30" },
    totals: {
      weight_kg: "1234.500",
      co2e_kg: "980.200",
      deposit_count: 311,
      active_nasabah: 42,
    },
    by_type: [
      {
        waste_type: "kardus",
        name_id: "Kardus",
        weight_kg: "400.000",
        co2e_kg: "320.000",
      },
    ],
    monthly: [{ month: "2026-09", weight_kg: "1234.500", co2e_kg: "980.200" }],
    pipeline: {
      pending_rows: 7,
      auto_rate: 0.62,
      correction_rate: 0.18,
    },
    coverage: { types_missing_factor: ["besi"] },
    is_demo: isDemo,
  };
}

describe("DashboardPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders Data demo banner when bank is_demo is true", async () => {
    vi.spyOn(dashboardService, "getDashboardSummary").mockResolvedValue(
      createMockSummary(true),
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    const banner = container.querySelector("#demo-banner");
    expect(banner).not.toBeNull();
    expect(container.textContent).toContain("Data demo");
    expect(container.textContent).toContain("1.234,500 kg");
  });

  it("does not render Data demo banner when bank is_demo is false", async () => {
    vi.spyOn(dashboardService, "getDashboardSummary").mockResolvedValue(
      createMockSummary(false),
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    const banner = container.querySelector("#demo-banner");
    expect(banner).toBeNull();
    expect(container.textContent).not.toContain("Data demo");
  });
});
