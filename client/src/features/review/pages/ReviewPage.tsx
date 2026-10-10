import { useState } from "react";
import { useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCheck,
  ChevronDown,
  ChevronUp,
  RotateCw,
} from "lucide-react";
import { RowCard } from "../components/RowCard";
import { filterEligibleForConfirmAll } from "../lib/confirmAll";
import { ERROR_MESSAGES, UI_STRINGS, type ErrorCode } from "@/lib/strings.id";
import { ApiError } from "@/types/api";
import { useUpload } from "@/features/upload/hooks/useUpload";
import { deleteDeposit } from "@/services/deposits";
import { createNasabah, getNasabahList } from "@/services/nasabah";
import {
  confirmAllRows,
  confirmRow,
  rejectRow,
  updateRow,
} from "@/services/rows";
import { getWasteTypes } from "@/services/wasteTypes";
import type { RowUpdatePayload } from "@/types/rows";
import type { ExtractedRow } from "@/types/uploads";

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { upload, isLoading, isError, error, retry, isRetrying } =
    useUpload(id);

  const { data: nasabahData } = useQuery({
    queryKey: ["nasabah-list"],
    queryFn: () => getNasabahList({ page_size: 100 }),
  });

  const { data: wasteTypes = [] } = useQuery({
    queryKey: ["waste-types"],
    queryFn: () => getWasteTypes(),
  });

  const [activeRowId, setActiveRowId] = useState<number | null>(null);
  const [isAutoSavedExpanded, setIsAutoSavedExpanded] = useState(false);
  const [isConfirmAllDialogOpen, setIsConfirmAllDialogOpen] = useState(false);
  const [isConfirmingAll, setIsConfirmingAll] = useState(false);
  const [pageErrorMessage, setPageErrorMessage] = useState<string | null>(null);

  const nasabahList = nasabahData?.results || [];

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
        {UI_STRINGS.loading}
      </div>
    );
  }

  if (isError || !upload) {
    return (
      <div
        role="alert"
        className="mx-auto max-w-6xl rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
      >
        {error?.message || UI_STRINGS.unknownError}
      </div>
    );
  }

  if (upload.status === "failed") {
    const failureMessage =
      upload.error_code === "LLM_RATE_LIMITED"
        ? ERROR_MESSAGES.LLM_RATE_LIMITED
        : upload.error_message ||
          (upload.error_code && upload.error_code in ERROR_MESSAGES
            ? ERROR_MESSAGES[upload.error_code as ErrorCode]
            : UI_STRINGS.unknownError);

    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div
          role="alert"
          className="space-y-3 rounded-sm border border-brick bg-paper p-6 text-sm text-brick"
        >
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="h-5 w-5" />
            <span>Ekstraksi Gagal</span>
          </div>
          <p>{failureMessage}</p>
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
      </div>
    );
  }

  const manualRows = upload.rows.filter(
    (r) => r.status === "pending" && (r.route === "manual" || !r.route),
  );
  const confirmRows = upload.rows.filter(
    (r) => r.status === "pending" && r.route === "confirm",
  );
  const autoOrSavedRows = upload.rows.filter(
    (r) => r.status === "saved" || r.route === "auto",
  );

  const eligibleForConfirmAll = filterEligibleForConfirmAll(upload.rows);

  const activeRow =
    upload.rows.find((r) => r.id === activeRowId) ||
    manualRows[0] ||
    confirmRows[0] ||
    upload.rows[0];

  async function handleUpdateRow(rowId: number, fields: RowUpdatePayload) {
    setPageErrorMessage(null);
    const updated = await updateRow(rowId, fields);
    queryClient.setQueryData(["upload", id], (prev: typeof upload) => {
      if (!prev) return prev;
      return {
        ...prev,
        rows: prev.rows.map((r) => (r.id === rowId ? updated : r)),
      };
    });
  }

  async function handleConfirmRow(rowId: number) {
    setPageErrorMessage(null);
    const updated = await confirmRow(rowId);
    queryClient.setQueryData(["upload", id], (prev: typeof upload) => {
      if (!prev) return prev;
      return {
        ...prev,
        rows: prev.rows.map((r) => (r.id === rowId ? updated : r)),
      };
    });
  }

  async function handleRejectRow(rowId: number) {
    setPageErrorMessage(null);
    const updated = await rejectRow(rowId);
    queryClient.setQueryData(["upload", id], (prev: typeof upload) => {
      if (!prev) return prev;
      return {
        ...prev,
        rows: prev.rows.map((r) => (r.id === rowId ? updated : r)),
      };
    });
  }

  async function handleRevertDeposit(depositId: number) {
    setPageErrorMessage(null);
    await deleteDeposit(depositId);
    await queryClient.invalidateQueries({ queryKey: ["upload", id] });
  }

  async function handleCreateNasabah(name: string) {
    const created = await createNasabah({ name });
    await queryClient.invalidateQueries({ queryKey: ["nasabah-list"] });
    return created;
  }

  async function handleConfirmAllSubmit() {
    if (!upload || eligibleForConfirmAll.length === 0 || isConfirmingAll) {
      return;
    }
    setIsConfirmingAll(true);
    setPageErrorMessage(null);
    try {
      await confirmAllRows(upload.id);
      setIsConfirmAllDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["upload", id] });
    } catch (err) {
      if (err instanceof ApiError) {
        const mapped = ERROR_MESSAGES[err.code as ErrorCode];
        setPageErrorMessage(mapped || err.message);
      } else if (err instanceof Error) {
        setPageErrorMessage(err.message);
      } else {
        setPageErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsConfirmingAll(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-rule pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.reviewTitle} #{upload.id}
          </h2>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="font-semibold text-sprout">
              {autoOrSavedRows.length} tersimpan otomatis
            </span>
            <span>•</span>
            <span className="font-semibold text-amber">
              {confirmRows.length} perlu konfirmasi
            </span>
            <span>•</span>
            <span className="font-semibold text-brick">
              {manualRows.length} perlu diisi
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsConfirmAllDialogOpen(true)}
          disabled={eligibleForConfirmAll.length === 0}
          className="flex min-h-[44px] items-center gap-2 rounded-sm bg-sprout px-4 py-2 font-medium text-sm text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <CheckCheck className="h-4 w-4" />
          <span>Konfirmasi semua ({eligibleForConfirmAll.length})</span>
        </button>
      </div>

      {pageErrorMessage && (
        <div
          role="alert"
          className="rounded-sm border border-brick bg-paper p-3 text-sm text-brick"
        >
          {pageErrorMessage}
        </div>
      )}

      {isConfirmAllDialogOpen && (
        <dialog
          open
          aria-modal="true"
          className="fixed inset-0 z-50 flex h-full w-full max-h-none max-w-none items-center justify-center border-none bg-black/40 p-4"
        >
          <div className="w-full max-w-md space-y-4 rounded-sm border border-rule bg-paper p-6 shadow-md">
            <h3 className="font-bold text-lg text-ink">
              {UI_STRINGS.confirmAllDialogTitle}
            </h3>
            <p className="text-sm text-muted-foreground">
              Apakah Anda yakin ingin mengonfirmasi{" "}
              {eligibleForConfirmAll.length} baris yang memenuhi syarat
              sekaligus?
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsConfirmAllDialogOpen(false)}
                disabled={isConfirmingAll}
                className="min-h-[44px] rounded-sm border border-rule px-4 py-2 text-sm font-medium text-ink hover:bg-muted"
              >
                {UI_STRINGS.cancelButton}
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmAllSubmit()}
                disabled={isConfirmingAll}
                className="flex min-h-[44px] items-center gap-2 rounded-sm bg-sprout px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {isConfirmingAll && (
                  <RotateCw className="h-4 w-4 animate-spin" />
                )}
                <span>{UI_STRINGS.saveButton}</span>
              </button>
            </div>
          </div>
        </dialog>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="hidden lg:col-span-5 lg:block">
          <div className="sticky top-6 overflow-hidden rounded-sm border border-rule bg-paper">
            <div className="border-b border-rule bg-muted/20 px-3 py-2 font-semibold text-xs text-ink">
              Gambar Halaman Asli
            </div>
            {upload.source_type === "image" ? (
              <div className="relative max-h-[calc(100vh-10rem)] overflow-auto bg-muted/10 p-2">
                <div className="relative inline-block w-full">
                  <img
                    src={`/api/uploads/${upload.id}/image/`}
                    alt="Buku Kas"
                    className="w-full rounded-sm object-contain"
                  />
                  {activeRow &&
                    activeRow.evidence.y_min !== null &&
                    activeRow.evidence.y_max !== null && (
                      <div
                        className="pointer-events-none absolute right-0 left-0 border-2 border-sprout bg-sprout/20 transition-all"
                        style={{
                          top: `${activeRow.evidence.y_min * 100}%`,
                          height: `${
                            (activeRow.evidence.y_max -
                              activeRow.evidence.y_min) *
                            100
                          }%`,
                        }}
                      />
                    )}
                </div>
              </div>
            ) : (
              <div className="max-h-[calc(100vh-10rem)] overflow-auto p-4 font-mono text-xs text-ink whitespace-pre-wrap">
                {upload.rows.map((r) => r.raw.evidence_text).join("\n")}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6 lg:col-span-7">
          {manualRows.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 font-bold text-sm text-brick">
                <span>{UI_STRINGS.manualLaneTitle}</span>
                <span className="rounded-sm bg-brick/10 px-2 py-0.5 text-xs">
                  {manualRows.length}
                </span>
              </div>
              <div className="space-y-3">
                {manualRows.map((row: ExtractedRow) => (
                  <RowCard
                    key={row.id}
                    row={row}
                    uploadId={upload.id}
                    sourceType={upload.source_type}
                    nasabahList={nasabahList}
                    wasteTypes={wasteTypes}
                    isActive={activeRow?.id === row.id}
                    onFocus={() => setActiveRowId(row.id)}
                    onConfirm={handleConfirmRow}
                    onReject={handleRejectRow}
                    onUpdate={handleUpdateRow}
                    onCreateNasabah={handleCreateNasabah}
                  />
                ))}
              </div>
            </div>
          )}

          {confirmRows.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 font-bold text-sm text-amber">
                <span>{UI_STRINGS.confirmLaneTitle}</span>
                <span className="rounded-sm bg-amber/10 px-2 py-0.5 text-xs">
                  {confirmRows.length}
                </span>
              </div>
              <div className="space-y-3">
                {confirmRows.map((row: ExtractedRow) => (
                  <RowCard
                    key={row.id}
                    row={row}
                    uploadId={upload.id}
                    sourceType={upload.source_type}
                    nasabahList={nasabahList}
                    wasteTypes={wasteTypes}
                    isActive={activeRow?.id === row.id}
                    onFocus={() => setActiveRowId(row.id)}
                    onConfirm={handleConfirmRow}
                    onReject={handleRejectRow}
                    onUpdate={handleUpdateRow}
                    onCreateNasabah={handleCreateNasabah}
                  />
                ))}
              </div>
            </div>
          )}

          {autoOrSavedRows.length > 0 && (
            <div className="rounded-sm border border-rule bg-paper">
              <button
                type="button"
                onClick={() => setIsAutoSavedExpanded((prev) => !prev)}
                className="flex min-h-[44px] w-full items-center justify-between p-3 font-semibold text-sm text-sprout transition-colors hover:bg-muted/30"
              >
                <div className="flex items-center gap-2">
                  <span>{UI_STRINGS.autoSavedSectionTitle}</span>
                  <span className="rounded-sm bg-sprout/10 px-2 py-0.5 text-xs">
                    {autoOrSavedRows.length}
                  </span>
                </div>
                {isAutoSavedExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>

              {isAutoSavedExpanded && (
                <div className="space-y-3 border-t border-rule p-3">
                  {autoOrSavedRows.map((row: ExtractedRow) => (
                    <RowCard
                      key={row.id}
                      row={row}
                      uploadId={upload.id}
                      sourceType={upload.source_type}
                      nasabahList={nasabahList}
                      wasteTypes={wasteTypes}
                      isActive={activeRow?.id === row.id}
                      onFocus={() => setActiveRowId(row.id)}
                      onConfirm={handleConfirmRow}
                      onReject={handleRejectRow}
                      onRevert={handleRevertDeposit}
                      onUpdate={handleUpdateRow}
                      onCreateNasabah={handleCreateNasabah}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
