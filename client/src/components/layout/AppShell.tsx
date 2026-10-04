import { Link, Outlet, useLocation } from "react-router";
import {
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  Package,
  Upload,
  Users,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { UI_STRINGS } from "@/lib/strings.id";

const DESKTOP_NAV_ITEMS = [
  { path: "/", label: UI_STRINGS.navDashboard, icon: LayoutDashboard },
  { path: "/upload", label: UI_STRINGS.navUpload, icon: Upload },
  { path: "/uploads", label: UI_STRINGS.navHistory, icon: History },
  { path: "/deposits", label: UI_STRINGS.navDeposits, icon: Package },
  { path: "/nasabah", label: UI_STRINGS.navNasabah, icon: Users },
  { path: "/reports", label: UI_STRINGS.navReports, icon: FileText },
];

const MOBILE_NAV_ITEMS = [
  { path: "/", label: UI_STRINGS.navDashboard, icon: LayoutDashboard },
  { path: "/upload", label: UI_STRINGS.navUpload, icon: Upload },
  { path: "/uploads", label: UI_STRINGS.navHistory, icon: History },
  { path: "/reports", label: UI_STRINGS.navReports, icon: FileText },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isCurrentPath = (path: string) => {
    if (path === "/") {
      return location.pathname === "/";
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink md:flex-row">
      <aside className="hidden w-64 flex-shrink-0 flex-col justify-between border-r border-rule bg-paper p-4 md:flex">
        <div className="space-y-6">
          <div className="border-b border-rule pb-4">
            <h1 className="text-xl font-bold tracking-tight text-ink">
              {UI_STRINGS.appTitle}
            </h1>
            {user?.bank_sampah && (
              <p className="mt-1 text-xs text-muted-foreground">
                {user.bank_sampah.name}
              </p>
            )}
          </div>

          <nav className="space-y-1">
            {DESKTOP_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = isCurrentPath(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex min-h-[44px] items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                    active
                      ? "border-l-2 border-sprout bg-muted font-semibold text-sprout"
                      : "text-ink hover:bg-muted/60"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="border-t border-rule pt-4">
          {user && (
            <div className="mb-3 px-3 text-xs text-muted-foreground">
              <span className="font-medium text-ink">{user.username}</span>
            </div>
          )}
          <button
            type="button"
            onClick={() => void logout()}
            className="flex min-h-[44px] w-full items-center gap-3 rounded-sm px-3 py-2 text-sm text-brick transition-colors hover:bg-muted/60"
          >
            <LogOut className="h-4 w-4" />
            <span>{UI_STRINGS.logoutButton}</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-4 pb-20 md:p-6 md:pb-6">
        <Outlet />
      </main>

      <nav className="fixed right-0 bottom-0 left-0 flex border-t border-rule bg-paper md:hidden">
        {MOBILE_NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = isCurrentPath(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex min-h-[48px] flex-1 flex-col items-center justify-center gap-1 py-1 text-[11px] transition-colors ${
                active ? "font-semibold text-sprout" : "text-muted-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
