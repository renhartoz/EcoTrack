import { useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  CircleHelp,
  PencilLine,
  RotateCcw,
  X,
} from "lucide-react";
import { calculateEvidenceCrop } from "@/lib/evidenceCrop";
import {
  ERROR_MESSAGES,
  FLAG_MESSAGES,
  UI_STRINGS,
  type ErrorCode,
  type FlagCode,
} from "@/lib/strings.id";
import { ApiError } from "@/types/api";
import type { Nasabah } from "@/types/nasabah";
import type { RowUpdatePayload } from "@/types/rows";
import type { ExtractedRow } from "@/types/uploads";
import type { WasteType } from "@/types/wasteTypes";

interface RowCardProps {
  row: ExtractedRow;
  uploadId: number;
  sourceType: "image" | "text";
  nasabahList: Nasabah[];
  wasteTypes: WasteType[];
  isActive?: boolean;
  onFocus?: () => void;
  onConfirm: (rowId: number) => Promise<void>;
  onReject: (rowId: number) => Promise<void>;
  onRevert?: (depositId: number) => Promise<void>;
  onUpdate: (rowId: number, fields: RowUpdatePayload) => Promise<void>;
  onCreateNasabah: (name: string) => Promise<Nasabah>;
}

export function RowCard({
  row,
  uploadId,
  sourceType,
  nasabahList,
  wasteTypes,
  isActive = false,
  onFocus,
  onConfirm,
  onReject,
  onRevert,
  onUpdate,
  onCreateNasabah,
}: RowCardProps) {
  const [tanggal, setTanggal] = useState(row.normalized.tanggal || "");
  const [nasabahId, setNasabahId] = useState<number | "">(
    row.normalized.nasabah_id ?? "",
  );
  const [wasteTypeId, setWasteTypeId] = useState<number | "">(
    row.normalized.waste_type_id ?? "",
  );
  const [weightKg, setWeightKg] = useState(
    row.normalized.weight_kg || row.raw.berat || "",
  );

  const [isAddingNasabah, setIsAddingNasabah] = useState(false);
  const [newNasabahName, setNewNasabahName] = useState("");
  const [isSubmittingNasabah, setIsSubmittingNasabah] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isActing, setIsActing] = useState(false);

  const hasHardFlag = row.flags.some((flag) => flag.severity === "hard");
  const crop = calculateEvidenceCrop(row.evidence.y_min, row.evidence.y_max);
  const imageUrl = `/api/uploads/${uploadId}/image/`;

  function resolveErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const mapped = ERROR_MESSAGES[err.code as ErrorCode];
      if (mapped) {
        return mapped;
      }
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return UI_STRINGS.unknownError;
  }

  async function handleFieldBlur() {
    setErrorMessage(null);
    try {
      await onUpdate(row.id, {
        tanggal: tanggal || null,
        nasabah_id: typeof nasabahId === "number" ? nasabahId : null,
        waste_type_id: typeof wasteTypeId === "number" ? wasteTypeId : null,
        weight_kg: weightKg || null,
      });
    } catch (err) {
      setErrorMessage(resolveErrorMessage(err));
    }
  }

  async function handleConfirmClick() {
    if (hasHardFlag || isActing) {
      return;
    }
    setIsActing(true);
    setErrorMessage(null);
    try {
      await onConfirm(row.id);
    } catch (err) {
      setErrorMessage(resolveErrorMessage(err));
    } finally {
      setIsActing(false);
    }
  }

  async function handleRejectClick() {
    if (isActing) {
      return;
    }
    setIsActing(true);
    setErrorMessage(null);
    try {
      await onReject(row.id);
    } catch (err) {
      setErrorMessage(resolveErrorMessage(err));
    } finally {
      setIsActing(false);
    }
  }

  async function handleRevertClick() {
    if (!row.deposit_id || !onRevert || isActing) {
      return;
    }
    setIsActing(true);
    setErrorMessage(null);
    try {
      await onRevert(row.deposit_id);
    } catch (err) {
      setErrorMessage(resolveErrorMessage(err));
    } finally {
      setIsActing(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter" && !hasHardFlag && row.status === "pending") {
      event.preventDefault();
      void handleConfirmClick();
    }
  }

  async function handleCreateNasabahSubmit() {
    if (!newNasabahName.trim() || isSubmittingNasabah) {
      return;
    }
    setIsSubmittingNasabah(true);
    try {
      const created = await onCreateNasabah(newNasabahName.trim());
      setNasabahId(created.id);
      setIsAddingNasabah(false);
      setNewNasabahName("");
      await onUpdate(row.id, {
        tanggal: tanggal || null,
        nasabah_id: created.id,
        waste_type_id: typeof wasteTypeId === "number" ? wasteTypeId : null,
        weight_kg: weightKg || null,
      });
    } catch (err) {
      setErrorMessage(resolveErrorMessage(err));
    } finally {
      setIsSubmittingNasabah(false);
    }
  }

  return (
    <div
      onFocus={onFocus}
      className={`space-y-4 rounded-sm border bg-paper p-4 transition-all ${
        isActive
          ? "border-sprout ring-1 ring-sprout shadow-sm"
          : "border-rule hover:border-input-border"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-bold text-ink">#{row.row_index + 1}</span>
          {row.route === "auto" && (
            <span className="inline-flex items-center gap-1 rounded-sm bg-sprout/10 px-2 py-0.5 font-medium text-sprout">
              <CheckCircle2 className="h-3 w-3" />
              <span>{UI_STRINGS.sourceAuto}</span>
            </span>
          )}
          {row.route === "confirm" && (
            <span className="inline-flex items-center gap-1 rounded-sm bg-amber/10 px-2 py-0.5 font-medium text-amber">
              <CircleHelp className="h-3 w-3" />
              <span>{UI_STRINGS.confirmLaneTitle}</span>
            </span>
          )}
          {row.route === "manual" && (
            <span className="inline-flex items-center gap-1 rounded-sm bg-brick/10 px-2 py-0.5 font-medium text-brick">
              <PencilLine className="h-3 w-3" />
              <span>{UI_STRINGS.manualLaneTitle}</span>
            </span>
          )}
          {row.status === "saved" && (
            <span className="rounded-sm bg-sprout/20 px-1.5 py-0.5 font-medium text-sprout">
              Tersimpan
            </span>
          )}
          {row.status === "rejected" && (
            <span className="rounded-sm bg-brick/20 px-1.5 py-0.5 font-medium text-brick">
              Ditolak
            </span>
          )}
          {row.status === "reverted" && (
            <span className="rounded-sm bg-muted px-1.5 py-0.5 font-medium text-muted-foreground">
              Dibatalkan
            </span>
          )}
        </div>
        {row.human_edited && (
          <span className="text-muted-foreground italic text-[11px]">
            Diedit operator
          </span>
        )}
      </div>

      <div>
        <div className="mb-1 text-[11px] font-medium text-muted-foreground uppercase">
          {UI_STRINGS.rawSourceLabel}
        </div>
        {sourceType === "image" ? (
          crop.isValid ? (
            <div
              className="h-20 w-full overflow-hidden rounded-sm border border-rule bg-muted/20"
              style={{
                backgroundImage: `url(${imageUrl})`,
                backgroundPosition: crop.backgroundPosition,
                backgroundSize: crop.backgroundSize,
                backgroundRepeat: "no-repeat",
              }}
              title="Potongan tulisan buku kas"
            />
          ) : (
            <div className="flex h-16 w-full items-center justify-between rounded-sm border border-rule bg-muted/20 px-3 text-xs text-muted-foreground">
              <span>Gambar penuh (posisi koordinat tidak tersedia)</span>
              <span className="font-mono text-ink">
                Baris #{row.row_index + 1}
              </span>
            </div>
          )
        ) : (
          <div className="rounded-sm border border-rule bg-muted/15 p-2 font-mono text-xs text-ink">
            {row.raw.evidence_text || "-"}
          </div>
        )}
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span>Tgl: {row.raw.tanggal || "-"}</span>
          <span>Nama: {row.raw.nama || "-"}</span>
          <span>Jenis: {row.raw.jenis || "-"}</span>
          <span>
            Berat: {row.raw.berat || "-"} {row.raw.satuan || ""}
          </span>
          {row.raw.evidence_text && (
            <span className="w-full font-mono text-ink">
              {row.raw.evidence_text}
            </span>
          )}
        </div>
      </div>

      {row.flags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {row.flags.map((flag, idx) => {
            const isHard = flag.severity === "hard";
            const message = FLAG_MESSAGES[flag.code as FlagCode] || flag.code;
            return (
              <span
                key={`${flag.code}-${idx}`}
                className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs ${
                  isHard
                    ? "border border-brick/40 bg-brick/10 font-medium text-brick"
                    : "border border-amber/40 bg-amber/10 text-amber"
                }`}
                title={message}
              >
                {isHard ? (
                  <AlertCircle className="h-3 w-3" />
                ) : (
                  <AlertTriangle className="h-3 w-3" />
                )}
                <span>{message}</span>
              </span>
            );
          })}
        </div>
      )}

      {errorMessage && (
        <div
          role="alert"
          className="rounded-sm border border-brick bg-paper p-2 text-xs text-brick"
        >
          {errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink">
            {UI_STRINGS.tableHeaderDate}
          </label>
          <input
            type="date"
            value={tanggal}
            onChange={(e) => setTanggal(e.target.value)}
            onBlur={handleFieldBlur}
            onKeyDown={handleKeyDown}
            disabled={row.status !== "pending"}
            className="w-full min-h-[44px] rounded-sm border border-input-border bg-paper px-2.5 py-1.5 text-xs text-ink outline-none focus-visible:ring-1 focus-visible:ring-sprout disabled:opacity-60"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-ink">
            {UI_STRINGS.tableHeaderName}
          </label>
          {isAddingNasabah ? (
            <div className="flex gap-1">
              <input
                type="text"
                placeholder="Nama baru..."
                value={newNasabahName}
                onChange={(e) => setNewNasabahName(e.target.value)}
                className="w-full min-h-[44px] rounded-sm border border-input-border bg-paper px-2 py-1 text-xs text-ink outline-none focus-visible:ring-1 focus-visible:ring-sprout"
              />
              <button
                type="button"
                onClick={() => void handleCreateNasabahSubmit()}
                disabled={isSubmittingNasabah || !newNasabahName.trim()}
                aria-label={UI_STRINGS.saveButton}
                className="flex min-h-[44px] items-center rounded-sm bg-sprout px-2 text-white hover:opacity-90 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setIsAddingNasabah(false)}
                aria-label={UI_STRINGS.cancelButton}
                className="flex min-h-[44px] items-center rounded-sm border border-rule px-2 text-ink hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <select
              value={nasabahId}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "__add_new__") {
                  setIsAddingNasabah(true);
                  return;
                }
                setNasabahId(val ? parseInt(val, 10) : "");
              }}
              onBlur={handleFieldBlur}
              disabled={row.status !== "pending"}
              className="w-full min-h-[44px] rounded-sm border border-input-border bg-paper px-2.5 py-1.5 text-xs text-ink outline-none focus-visible:ring-1 focus-visible:ring-sprout disabled:opacity-60"
            >
              <option value="">Pilih Nasabah...</option>
              {nasabahList
                .filter(
                  (n) => n.is_active || n.id === row.normalized.nasabah_id,
                )
                .map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name}
                  </option>
                ))}
              {row.status === "pending" && (
                <option value="__add_new__">
                  {UI_STRINGS.addNasabahOption}
                </option>
              )}
            </select>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-ink">
            {UI_STRINGS.tableHeaderType}
          </label>
          <select
            value={wasteTypeId}
            onChange={(e) => {
              const val = e.target.value;
              setWasteTypeId(val ? parseInt(val, 10) : "");
            }}
            onBlur={handleFieldBlur}
            disabled={row.status !== "pending"}
            className="w-full min-h-[44px] rounded-sm border border-input-border bg-paper px-2.5 py-1.5 text-xs text-ink outline-none focus-visible:ring-1 focus-visible:ring-sprout disabled:opacity-60"
          >
            <option value="">Pilih Jenis Sampah...</option>
            {wasteTypes.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name_id}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-ink">
            {UI_STRINGS.tableHeaderWeight} (kg)
          </label>
          <div className="relative">
            <input
              type="text"
              inputMode="decimal"
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
              onBlur={handleFieldBlur}
              onKeyDown={handleKeyDown}
              disabled={row.status !== "pending"}
              placeholder="0.000"
              className="w-full min-h-[44px] rounded-sm border border-input-border bg-paper pr-8 pl-2.5 py-1.5 font-mono text-xs text-ink outline-none focus-visible:ring-1 focus-visible:ring-sprout disabled:opacity-60"
            />
            <span className="pointer-events-none absolute inset-y-0 right-2.5 flex items-center text-xs text-muted-foreground">
              kg
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-rule pt-2">
        {row.status === "pending" && (
          <>
            <button
              type="button"
              onClick={() => void handleRejectClick()}
              disabled={isActing}
              className="flex min-h-[44px] items-center gap-1.5 rounded-sm border border-brick/40 px-3 py-1.5 text-xs font-medium text-brick transition-colors hover:bg-brick/10 disabled:opacity-50"
            >
              <X className="h-3.5 w-3.5" />
              <span>{UI_STRINGS.rejectRowButton}</span>
            </button>
            <button
              type="button"
              onClick={() => void handleConfirmClick()}
              disabled={hasHardFlag || isActing}
              title={
                hasHardFlag
                  ? "Selesaikan kesalahan kolom sebelum mengonfirmasi"
                  : "Simpan baris sebagai setoran"
              }
              className="flex min-h-[44px] items-center gap-1.5 rounded-sm bg-sprout px-4 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Check className="h-3.5 w-3.5" />
              <span>{UI_STRINGS.confirmRowButton}</span>
            </button>
          </>
        )}

        {row.status === "saved" && onRevert && (
          <button
            type="button"
            onClick={() => void handleRevertClick()}
            disabled={isActing}
            className="flex min-h-[44px] items-center gap-1.5 rounded-sm border border-rule px-3 py-1.5 text-xs font-medium text-brick transition-colors hover:bg-brick/10 disabled:opacity-50"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>{UI_STRINGS.cancelAutoSavedButton}</span>
          </button>
        )}
      </div>
    </div>
  );
}
