import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Image as ImageIcon,
} from "lucide-react";
import { UI_STRINGS } from "@/lib/strings.id";
import { getUploadDetail, getUploads } from "@/services/uploads";
import type { UploadListItem } from "@/types/uploads";

function UploadHistoryRow({ upload }: { upload: UploadListItem }) {
  const isReady = upload.status === "ready";
  const { data: detail } = useQuery({
    queryKey: ["upload-detail", upload.id.toString()],
    queryFn: () => getUploadDetail(upload.id),
    enabled: isReady,
    staleTime: 60_000,
  });

  const counts = detail?.counts;

  return (
    <div className="flex flex-col justify-between gap-3 p-4 transition-colors hover:bg-muted/40 sm:flex-row sm:items-center">
      <div className="flex items-start gap-3">
        {upload.source_type === "image" ? (
          <ImageIcon className="mt-0.5 h-5 w-5 text-muted-foreground" />
        ) : (
          <FileText className="mt-0.5 h-5 w-5 text-muted-foreground" />
        )}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-ink">#{upload.id}</span>
            <span className="text-xs text-muted-foreground">
              {new Date(upload.created_at).toLocaleString("id-ID", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>
              {upload.source_type === "image"
                ? UI_STRINGS.tabPhoto
                : UI_STRINGS.tabText}
            </span>
            <span>•</span>
            <span>{upload.row_count} baris</span>
            {counts && (
              <>
                <span>•</span>
                <span className="flex flex-wrap items-center gap-1.5">
                  {counts.manual > 0 && (
                    <span className="rounded-sm bg-brick/10 px-1.5 py-0.5 font-medium text-brick">
                      {counts.manual} {UI_STRINGS.manualLaneTitle.toLowerCase()}
                    </span>
                  )}
                  {counts.confirm > 0 && (
                    <span className="rounded-sm bg-amber/15 px-1.5 py-0.5 font-medium text-amber">
                      {counts.confirm}{" "}
                      {UI_STRINGS.confirmLaneTitle.toLowerCase()}
                    </span>
                  )}
                  {counts.saved > 0 && (
                    <span className="rounded-sm bg-sprout/15 px-1.5 py-0.5 font-medium text-sprout">
                      {counts.saved} tersimpan
                    </span>
                  )}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 sm:justify-end">
        {upload.status === "processing" && (
          <span className="inline-flex items-center gap-1 rounded-sm bg-amber/10 px-2.5 py-1 text-xs font-medium text-amber">
            <Clock className="h-3.5 w-3.5" />
            <span>{UI_STRINGS.statusProcessing}</span>
          </span>
        )}
        {upload.status === "ready" && (
          <span className="inline-flex items-center gap-1 rounded-sm bg-sprout/10 px-2.5 py-1 text-xs font-medium text-sprout">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{UI_STRINGS.statusReady}</span>
          </span>
        )}
        {upload.status === "failed" && (
          <span className="inline-flex items-center gap-1 rounded-sm bg-brick/10 px-2.5 py-1 text-xs font-medium text-brick">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>{UI_STRINGS.statusFailed}</span>
          </span>
        )}

        <Link
          to={`/uploads/${upload.id}`}
          className="flex min-h-[36px] items-center gap-1 rounded-sm border border-rule px-3 py-1 text-xs font-medium text-ink transition-colors hover:bg-muted"
        >
          <span>Tinjau</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}

export function UploadHistoryPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["uploads"],
    queryFn: () => getUploads(1, 50),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="border-b border-rule pb-3">
        <h2 className="text-2xl font-bold tracking-tight text-ink">
          {UI_STRINGS.uploadHistoryTitle}
        </h2>
      </div>

      {isLoading && (
        <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
          {UI_STRINGS.loading}
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
        >
          {UI_STRINGS.unknownError}
        </div>
      )}

      {!isLoading && !isError && data?.results.length === 0 && (
        <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
          {UI_STRINGS.noUploadsYet}
        </div>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="divide-y divide-rule rounded-sm border border-rule bg-paper">
          {data.results.map((upload: UploadListItem) => (
            <UploadHistoryRow key={upload.id} upload={upload} />
          ))}
        </div>
      )}
    </div>
  );
}
