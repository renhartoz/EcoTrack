import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  Lock,
  RotateCw,
  Scale,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { ERROR_MESSAGES, UI_STRINGS, type ErrorCode } from "@/lib/strings.id";
import { ApiError } from "@/types/api";

export function LoginPage() {
  const { login, registerDemo, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isRegisteringDemo, setIsRegisteringDemo] = useState(false);
  const [demoErrorMessage, setDemoErrorMessage] = useState<string | null>(null);
  const [showCustomDemo, setShowCustomDemo] = useState(false);
  const [customJudgeUsername, setCustomJudgeUsername] = useState("");
  const [customBankName, setCustomBankName] = useState("");

  const fromLocation =
    (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  if (isAuthenticated) {
    return <Navigate to={fromLocation} replace />;
  }

  async function handleOperatorLogin(event: FormEvent<HTMLFormElement>) {
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

  async function handleJudgeDemoRegister() {
    setDemoErrorMessage(null);
    setIsRegisteringDemo(true);

    try {
      await registerDemo({
        username: customJudgeUsername.trim() || undefined,
        bank_name: customBankName.trim() || undefined,
      });
      navigate(fromLocation, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped = ERROR_MESSAGES[error.code as ErrorCode];
        setDemoErrorMessage(mapped || error.message || UI_STRINGS.unknownError);
      } else {
        setDemoErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsRegisteringDemo(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col justify-between bg-paper text-ink">
      <header className="border-b border-rule bg-paper px-4 py-3 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-ink">
              {UI_STRINGS.appTitle}
            </span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              · Digitalisasi Buku Kas Bank Sampah
            </span>
          </div>
          <span className="inline-flex items-center gap-1 rounded-sm border border-rule px-2 py-1 text-[11px] font-medium text-muted-foreground">
            JOINTS UGM 2026
          </span>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl flex-1 grid-cols-1 items-start gap-8 px-4 py-8 sm:px-8 lg:grid-cols-12 lg:gap-12 lg:py-14">
        <div className="space-y-6 lg:col-span-7">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-1.5 rounded-sm bg-sprout/10 px-2.5 py-1 text-xs font-semibold text-sprout">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Subtema Sustainability · Solusi Sampah Non-Organik</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-ink sm:text-4xl lg:text-5xl">
              Ubah Catatan Tangan Menjadi Data Dampak Nyata.
            </h1>
            <p className="text-base text-muted-foreground sm:text-lg">
              Solusi digitalisasi sampah non-organik untuk bank sampah yang
              mengelola limbah dari{" "}
              <strong className="text-ink">pasar tradisional</strong>,{" "}
              <strong className="text-ink">UMKM kuliner</strong>, dan{" "}
              <strong className="text-ink">rumah tangga</strong>: foto catatan
              tangan fisik, verifikasi hasil AI cerdas, dan pantau reduksi emisi
              GRK untuk mencegah pencemaran lingkungan.
            </p>
          </div>

          <div className="rounded-sm border border-rule bg-paper p-4 sm:p-5">
            <div className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Alur Transformasi Data Buku Kas
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-sm border border-rule bg-muted/20 p-3">
                <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                  <span>Buku Kas Fisik (UMKM / Pasar / Warga)</span>
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                </div>
                <div className="mt-2 font-mono text-sm font-semibold text-ink">
                  02/10 Warung Bu Siti jelantah 5 liter
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  Tulisan tangan & satuan tak baku diverifikasi
                </div>
              </div>

              <div className="rounded-sm border border-sprout/40 bg-sprout/5 p-3">
                <div className="flex items-center justify-between text-xs font-medium text-sprout">
                  <span>Data Terstruktur & Emisi Sah</span>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                </div>
                <div className="mt-2 font-mono text-sm font-semibold text-ink">
                  Warung Bu Siti (UMKM) · Jelantah · 5.000 kg
                </div>
                <div className="mt-1 font-semibold text-[11px] text-sprout tabular-nums">
                  Terdivergensi dari pencemaran air & selokan
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-sm border border-rule bg-paper p-3">
              <div className="flex items-center gap-1.5 font-bold text-xs text-ink">
                <ShieldCheck className="h-4 w-4 text-sprout" />
                <span>Pasar Tradisional</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Digitalisasi timbulan kardus sayur/buah & plastik kresek
                pedagang pasar.
              </p>
            </div>

            <div className="rounded-sm border border-rule bg-paper p-3">
              <div className="flex items-center gap-1.5 font-bold text-xs text-ink">
                <UserCheck className="h-4 w-4 text-sprout" />
                <span>UMKM Kuliner</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Pencatatan minyak jelantah, jerigen, kaleng, dan kemasan makanan
                warung.
              </p>
            </div>

            <div className="rounded-sm border border-rule bg-paper p-3">
              <div className="flex items-center gap-1.5 font-bold text-xs text-ink">
                <Scale className="h-4 w-4 text-sprout" />
                <span>Rumah Tangga</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Pencatatan botol PET, kardus paket, dan kertas warga perumahan.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-sm border border-rule bg-paper p-6 sm:p-8 lg:col-span-5">
          <div className="space-y-6">
            <div className="rounded-sm border border-sprout/50 bg-sprout/5 p-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 font-bold text-xs text-sprout uppercase tracking-wider">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{UI_STRINGS.judgeAccessTitle}</span>
                </span>
                <span className="rounded-sm bg-sprout/20 px-1.5 py-0.5 text-[10px] font-semibold text-sprout">
                  Juri Hackathon
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {UI_STRINGS.judgeAccessDesc}
              </p>

              {demoErrorMessage && (
                <div
                  role="alert"
                  className="mt-3 flex items-center gap-2 rounded-sm border border-brick bg-paper p-2.5 text-xs text-brick"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{demoErrorMessage}</span>
                </div>
              )}

              <button
                type="button"
                onClick={() => void handleJudgeDemoRegister()}
                disabled={isRegisteringDemo}
                className="mt-3 flex min-h-[44px] w-full items-center justify-center gap-2 rounded-sm bg-sprout px-4 py-2.5 font-medium text-sm text-white transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-sprout outline-none disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isRegisteringDemo ? (
                  <>
                    <RotateCw className="h-4 w-4 animate-spin" />
                    <span>Membuat Bank Sampah Demo...</span>
                  </>
                ) : (
                  <>
                    <span>{UI_STRINGS.judgeAccessButton}</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              <div className="mt-3 border-t border-rule/60 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCustomDemo((prev) => !prev)}
                  className="flex min-h-[36px] w-full items-center justify-between text-[11px] text-muted-foreground hover:text-ink focus-visible:ring-2 focus-visible:ring-sprout outline-none"
                >
                  <span>Atur nama pengguna / nama bank khusus</span>
                  {showCustomDemo ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </button>

                {showCustomDemo && (
                  <div className="mt-2 space-y-2 pt-1 text-xs">
                    <div>
                      <label
                        htmlFor="custom-judge-username"
                        className="block text-[11px] text-muted-foreground"
                      >
                        Nama Pengguna Juri (Opsional)
                      </label>
                      <input
                        id="custom-judge-username"
                        type="text"
                        value={customJudgeUsername}
                        onChange={(e) => setCustomJudgeUsername(e.target.value)}
                        placeholder="Contoh: juri_ugm"
                        className="mt-1 min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-2.5 py-1 text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="custom-bank-name"
                        className="block text-[11px] text-muted-foreground"
                      >
                        Nama Bank Sampah (Opsional)
                      </label>
                      <input
                        id="custom-bank-name"
                        type="text"
                        value={customBankName}
                        onChange={(e) => setCustomBankName(e.target.value)}
                        placeholder="Contoh: Bank Sampah Evaluasi"
                        className="mt-1 min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-2.5 py-1 text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="relative text-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-rule" />
              </div>
              <span className="relative bg-paper px-2 text-xs text-muted-foreground">
                atau masuk dengan akun pengelola
              </span>
            </div>

            <div>
              <h2 className="text-lg font-bold tracking-tight text-ink">
                {UI_STRINGS.loginTitle}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {UI_STRINGS.loginSubtitle}
              </p>

              {errorMessage && (
                <div
                  id="login-error"
                  role="alert"
                  className="mt-3 flex items-center gap-2 rounded-sm border border-brick bg-paper p-3 text-xs text-brick"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <form onSubmit={handleOperatorLogin} className="mt-4 space-y-4">
                <div>
                  <label
                    htmlFor="username"
                    className="block font-medium text-xs text-ink"
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
                    className="mt-1 min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-3 py-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block font-medium text-xs text-ink"
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
                    className="mt-1 min-h-[44px] w-full rounded-sm border border-input-border bg-paper px-3 py-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex min-h-[44px] w-full items-center justify-center gap-2 rounded-sm border border-input-border bg-paper px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-sprout outline-none disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Lock className="h-4 w-4 text-muted-foreground" />
                  <span>
                    {isSubmitting
                      ? UI_STRINGS.loggingInButton
                      : UI_STRINGS.loginButton}
                  </span>
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-rule bg-paper px-4 py-4 text-center text-xs text-muted-foreground">
        <p>EcoTrack · Platform Digitalisasi Bank Sampah & Pengurangan Emisi</p>
      </footer>
    </div>
  );
}
