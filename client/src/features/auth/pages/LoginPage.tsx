import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useAuth } from "@/context/AuthContext";
import { ERROR_MESSAGES, UI_STRINGS, type ErrorCode } from "@/lib/strings.id";
import { ApiError } from "@/types/api";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fromLocation =
    (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  if (isAuthenticated) {
    return <Navigate to={fromLocation} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate(fromLocation, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped = ERROR_MESSAGES[error.code as ErrorCode];
        setErrorMessage(mapped || error.message || UI_STRINGS.unknownError);
      } else {
        setErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 text-ink">
      <div className="w-full max-w-sm rounded-sm border border-rule bg-paper p-6">
        <h1 className="mb-2 text-2xl font-bold tracking-tight text-ink">
          {UI_STRINGS.loginTitle}
        </h1>
        <p className="mb-6 text-sm text-muted-foreground">
          {UI_STRINGS.loginSubtitle}
        </p>

        {errorMessage && (
          <div
            id="login-error"
            role="alert"
            aria-live="polite"
            className="mb-4 rounded-sm border border-brick bg-paper p-3 text-sm text-brick"
          >
            {errorMessage}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="space-y-4"
          aria-describedby={errorMessage ? "login-error" : undefined}
        >
          <div>
            <label
              htmlFor="username"
              className="mb-1 block text-sm font-medium text-ink"
            >
              {UI_STRINGS.usernameLabel}
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSubmitting}
              className="min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-3 py-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-ink"
            >
              {UI_STRINGS.passwordLabel}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              className="min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-3 py-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="min-h-[44px] w-full rounded-sm bg-sprout px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? UI_STRINGS.loggingInButton : UI_STRINGS.loginButton}
          </button>
        </form>
      </div>
    </div>
  );
}
