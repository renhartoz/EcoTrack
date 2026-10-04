import { UI_STRINGS } from "@/lib/strings.id";

export function DashboardPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold tracking-tight text-ink">
        {UI_STRINGS.navDashboard}
      </h2>
      <div className="rounded-sm border border-rule p-4 text-sm text-muted-foreground">
        Halaman ringkasan data bank sampah.
      </div>
    </div>
  );
}
