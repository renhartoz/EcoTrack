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
import { getUploads } from "@/services/uploads";
import type { UploadListItem } from "@/types/uploads";

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
            <Link
              key={upload.id}
              to={`/uploads/${upload.id}`}
              className="flex min-h-[56px] items-center justify-between p-4 transition-colors hover:bg-muted/40"
            >
              <div className="flex items-center gap-3">
                {upload.source_type === "image" ? (
                  <ImageIcon className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <FileText className="h-5 w-5 text-muted-foreground" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-ink">
                      #{upload.id}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(upload.created_at).toLocaleString("id-ID", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>
                      {upload.source_type === "image"
                        ? UI_STRINGS.tabPhoto
                        : UI_STRINGS.tabText}
                    </span>
                    <span>•</span>
                    <span>{upload.row_count} baris</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
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
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
