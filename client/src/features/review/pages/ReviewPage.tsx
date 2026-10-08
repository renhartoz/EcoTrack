import { useParams } from "react-router";
import { AlertCircle, RotateCw } from "lucide-react";
import { ERROR_MESSAGES, UI_STRINGS, type ErrorCode } from "@/lib/strings.id";
import { useUpload } from "@/features/upload/hooks/useUpload";
import type { ExtractedRow } from "@/types/uploads";

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const { upload, isLoading, isError, error, retry, isRetrying } =
    useUpload(id);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
        {UI_STRINGS.loading}
      </div>
    );
  }

  if (isError || !upload) {
    return (
      <div
        role="alert"
        className="mx-auto max-w-5xl rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
      >
        {error?.message || UI_STRINGS.unknownError}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-2 border-b border-rule pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.reviewTitle} #{upload.id}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {new Date(upload.created_at).toLocaleString("id-ID", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </p>
        </div>
      </div>

      {upload.status === "processing" && (
        <output
          aria-live="polite"
          className="flex items-center gap-3 rounded-sm border border-sprout/40 bg-sprout/10 p-4 text-sm font-medium text-sprout block"
        >
          <RotateCw className="h-5 w-5 animate-spin" />
          <span>{UI_STRINGS.uploadProcessing}</span>
        </output>
      )}

      {upload.status === "failed" && (
        <div
          role="alert"
          aria-live="polite"
          className="space-y-3 rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
        >
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="h-5 w-5" />
            <span>Ekstraksi Gagal</span>
          </div>
          <p>
            {upload.error_code === "LLM_RATE_LIMITED"
              ? ERROR_MESSAGES.LLM_RATE_LIMITED
              : upload.error_message ||
                (upload.error_code
                  ? ERROR_MESSAGES[upload.error_code as ErrorCode]
                  : UI_STRINGS.unknownError)}
          </p>
          <button
            type="button"
            onClick={() => void retry()}
            disabled={isRetrying}
            className="flex min-h-[44px] items-center gap-2 rounded-sm bg-brick px-4 py-2 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <RotateCw
              className={`h-4 w-4 ${isRetrying ? "animate-spin" : ""}`}
            />
            <span>{UI_STRINGS.retryButton}</span>
          </button>
        </div>
      )}

      {upload.status === "ready" && (
        <div className="space-y-4">
          {upload.rows.length === 0 ? (
            <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
              {UI_STRINGS.noRowsExtracted}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-sm border border-rule bg-paper">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-rule bg-muted/30 text-xs font-semibold text-ink uppercase">
                  <tr>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderIndex}
                    </th>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderDate}
                    </th>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderName}
                    </th>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderType}
                    </th>
                    <th scope="col" className="px-4 py-3 text-right">
                      {UI_STRINGS.tableHeaderWeight}
                    </th>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderUnit}
                    </th>
                    <th scope="col" className="px-4 py-3">
                      {UI_STRINGS.tableHeaderEvidence}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule">
                  {upload.rows.map((row: ExtractedRow) => (
                    <tr
                      key={row.id}
                      className="transition-colors hover:bg-muted/30"
                    >
                      <td className="px-4 py-3 font-medium text-muted-foreground">
                        {row.row_index + 1}
                      </td>
                      <td className="px-4 py-3 text-ink">
                        {row.raw.tanggal || "-"}
                      </td>
                      <td className="px-4 py-3 font-medium text-ink">
                        {row.raw.nama || "-"}
                      </td>
                      <td className="px-4 py-3 text-ink">
                        {row.raw.jenis || "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-ink">
                        {row.raw.berat || "-"}
                      </td>
                      <td className="px-4 py-3 text-ink">
                        {row.raw.satuan || "-"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {row.raw.evidence_text || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
