import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  Download,
  Edit2,
  Filter,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { formatDate, formatWeight } from "@/lib/format";
import { UI_STRINGS } from "@/lib/strings.id";
import {
  createDeposit,
  deleteDeposit,
  exportDepositsCsv,
  getDeposits,
  updateDeposit,
} from "@/services/deposits";
import { getNasabahList } from "@/services/nasabah";
import { getWasteTypes } from "@/services/wasteTypes";
import type { Deposit, DepositSource } from "@/types/deposits";

export function DepositsPage() {
  const queryClient = useQueryClient();

  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [filterNasabah, setFilterNasabah] = useState<string>("");
  const [filterWasteType, setFilterWasteType] = useState<string>("");
  const [filterSource, setFilterSource] = useState<string>("");

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newNasabahId, setNewNasabahId] = useState<string>("");
  const [newWasteTypeId, setNewWasteTypeId] = useState<string>("");
  const [newWeightKg, setNewWeightKg] = useState("");
  const [newDate, setNewDate] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );

  const [editingDeposit, setEditingDeposit] = useState<Deposit | null>(null);
  const [editWeightKg, setEditWeightKg] = useState("");
  const [editDate, setEditDate] = useState("");

  const [deletingDepositId, setDeletingDepositId] = useState<number | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const filterParams = {
    from: filterFrom || undefined,
    to: filterTo || undefined,
    nasabah: filterNasabah ? parseInt(filterNasabah, 10) : undefined,
    waste_type: filterWasteType ? parseInt(filterWasteType, 10) : undefined,
    source: (filterSource as DepositSource) || undefined,
    page_size: 100,
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ["deposits", filterParams],
    queryFn: () => getDeposits(filterParams),
  });

  const { data: nasabahData } = useQuery({
    queryKey: ["nasabah-list"],
    queryFn: () => getNasabahList({ page_size: 100 }),
  });

  const { data: wasteTypes = [] } = useQuery({
    queryKey: ["waste-types"],
    queryFn: () => getWasteTypes(),
  });

  const createMutation = useMutation({
    mutationFn: createDeposit,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["deposits"] });
      setIsAddOpen(false);
      setNewNasabahId("");
      setNewWasteTypeId("");
      setNewWeightKg("");
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: { weight_kg?: string; deposit_date?: string };
    }) => updateDeposit(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["deposits"] });
      setEditingDeposit(null);
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDeposit(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["deposits"] });
      setDeletingDepositId(null);
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const handleExportCsv = async () => {
    try {
      setIsExporting(true);
      setActionError(null);
      const blob = await exportDepositsCsv(filterParams);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `deposits_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : UI_STRINGS.unknownError,
      );
    } finally {
      setIsExporting(false);
    }
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNasabahId || !newWasteTypeId || !newWeightKg || !newDate) {
      return;
    }
    setActionError(null);
    const parsedWeight = parseFloat(newWeightKg.replace(",", "."));
    if (Number.isNaN(parsedWeight) || parsedWeight <= 0) {
      setActionError("Berat harus berupa angka positif");
      return;
    }
    createMutation.mutate({
      nasabah_id: parseInt(newNasabahId, 10),
      waste_type_id: parseInt(newWasteTypeId, 10),
      weight_kg: parsedWeight.toFixed(3),
      deposit_date: newDate,
    });
  };

  const handleUpdateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDeposit || !editWeightKg || !editDate) {
      return;
    }
    setActionError(null);
    const parsedWeight = parseFloat(editWeightKg.replace(",", "."));
    if (Number.isNaN(parsedWeight) || parsedWeight <= 0) {
      setActionError("Berat harus berupa angka positif");
      return;
    }
    updateMutation.mutate({
      id: editingDeposit.id,
      payload: {
        weight_kg: parsedWeight.toFixed(3),
        deposit_date: editDate,
      },
    });
  };

  const nasabahList = nasabahData?.results || [];
  const deposits = data?.results || [];

  const getSourceBadge = (source: DepositSource) => {
    switch (source) {
      case "auto":
        return (
          <span className="inline-flex rounded-sm bg-sprout/15 px-2 py-0.5 text-xs font-semibold text-sprout">
            {UI_STRINGS.sourceAuto}
          </span>
        );
      case "confirmed":
        return (
          <span className="inline-flex rounded-sm bg-amber/15 px-2 py-0.5 text-xs font-semibold text-amber">
            {UI_STRINGS.sourceConfirmed}
          </span>
        );
      case "manual":
        return (
          <span className="inline-flex rounded-sm bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
            {UI_STRINGS.sourceManual}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.depositsListTitle}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Daftar seluruh setoran tersimpan, entri manual, dan ekspor data CSV.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleExportCsv()}
            disabled={isExporting}
            className="flex min-h-[44px] items-center gap-2 rounded-sm border border-rule bg-paper px-4 py-2 font-medium text-ink transition-colors hover:bg-muted disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            <span>
              {isExporting ? UI_STRINGS.loading : UI_STRINGS.exportCsvButton}
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActionError(null);
              setIsAddOpen(true);
            }}
            className="flex min-h-[44px] items-center gap-2 rounded-sm bg-sprout px-4 py-2 font-medium text-white transition-opacity hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            <span>{UI_STRINGS.addDepositButton}</span>
          </button>
        </div>
      </div>

      {actionError && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-sm border border-brick bg-paper p-3 text-sm text-brick"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      <div className="rounded-sm border border-rule bg-paper p-4">
        <div className="mb-3 flex items-center gap-2 font-semibold text-xs text-ink uppercase tracking-wider">
          <Filter className="h-3.5 w-3.5" />
          <span>Filter Data</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-5">
          <div>
            <label
              htmlFor="filter-from"
              className="block font-medium text-xs text-muted-foreground"
            >
              {UI_STRINGS.filterFrom}
            </label>
            <input
              id="filter-from"
              type="date"
              value={filterFrom}
              onChange={(e) => setFilterFrom(e.target.value)}
              className="mt-1 min-h-[40px] w-full rounded-sm border border-input bg-paper px-2.5 text-xs text-ink transition-colors focus:border-sprout focus:outline-hidden"
            />
          </div>

          <div>
            <label
              htmlFor="filter-to"
              className="block font-medium text-xs text-muted-foreground"
            >
              {UI_STRINGS.filterTo}
            </label>
            <input
              id="filter-to"
              type="date"
              value={filterTo}
              onChange={(e) => setFilterTo(e.target.value)}
              className="mt-1 min-h-[40px] w-full rounded-sm border border-input bg-paper px-2.5 text-xs text-ink transition-colors focus:border-sprout focus:outline-hidden"
            />
          </div>

          <div>
            <label
              htmlFor="filter-nasabah"
              className="block font-medium text-xs text-muted-foreground"
            >
              Nasabah
            </label>
            <select
              id="filter-nasabah"
              value={filterNasabah}
              onChange={(e) => setFilterNasabah(e.target.value)}
              className="mt-1 min-h-[40px] w-full rounded-sm border border-input bg-paper px-2.5 text-xs text-ink transition-colors focus:border-sprout focus:outline-hidden"
            >
              <option value="">Semua Nasabah</option>
              {nasabahList.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-type"
              className="block font-medium text-xs text-muted-foreground"
            >
              Jenis Sampah
            </label>
            <select
              id="filter-type"
              value={filterWasteType}
              onChange={(e) => setFilterWasteType(e.target.value)}
              className="mt-1 min-h-[40px] w-full rounded-sm border border-input bg-paper px-2.5 text-xs text-ink transition-colors focus:border-sprout focus:outline-hidden"
            >
              <option value="">Semua Jenis</option>
              {wasteTypes.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name_id}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-source"
              className="block font-medium text-xs text-muted-foreground"
            >
              {UI_STRINGS.filterSource}
            </label>
            <select
              id="filter-source"
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="mt-1 min-h-[40px] w-full rounded-sm border border-input bg-paper px-2.5 text-xs text-ink transition-colors focus:border-sprout focus:outline-hidden"
            >
              <option value="">{UI_STRINGS.filterAllSources}</option>
              <option value="auto">{UI_STRINGS.sourceAuto}</option>
              <option value="confirmed">{UI_STRINGS.sourceConfirmed}</option>
              <option value="manual">{UI_STRINGS.sourceManual}</option>
            </select>
          </div>
        </div>
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

      {!isLoading && !isError && deposits.length === 0 && (
        <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
          Tidak ada data setoran yang sesuai dengan filter.
        </div>
      )}

      {!isLoading && !isError && deposits.length > 0 && (
        <div className="overflow-x-auto rounded-sm border border-rule bg-paper">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-rule bg-muted/30 text-xs font-semibold text-muted-foreground">
              <tr>
                <th className="p-3">Tanggal</th>
                <th className="p-3">Nasabah</th>
                <th className="p-3">Jenis Sampah</th>
                <th className="p-3 text-right">Berat</th>
                <th className="p-3">Sumber</th>
                <th className="p-3 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {deposits.map((deposit) => (
                <tr
                  key={deposit.id}
                  className="transition-colors hover:bg-muted/20"
                >
                  <td className="p-3 font-medium text-ink">
                    {formatDate(deposit.deposit_date)}
                  </td>
                  <td className="p-3 text-ink">{deposit.nasabah.name}</td>
                  <td className="p-3 text-ink">{deposit.waste_type.name_id}</td>
                  <td className="p-3 text-right font-mono font-semibold text-ink">
                    {formatWeight(deposit.weight_kg)}
                  </td>
                  <td className="p-3">{getSourceBadge(deposit.source)}</td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => {
                          setActionError(null);
                          setEditingDeposit(deposit);
                          setEditWeightKg(deposit.weight_kg);
                          setEditDate(deposit.deposit_date);
                        }}
                        aria-label={UI_STRINGS.editButton}
                        className="rounded-sm p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-ink"
                        title={UI_STRINGS.editButton}
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeletingDepositId(deposit.id)}
                        aria-label={UI_STRINGS.deleteButton}
                        className="rounded-sm p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-brick"
                        title={UI_STRINGS.deleteButton}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isAddOpen && (
        <dialog
          open
          aria-modal="true"
          className="fixed inset-0 z-50 flex h-full w-full max-h-none max-w-none items-center justify-center border-none bg-black/40 p-4"
        >
          <div className="w-full max-w-md rounded-sm border border-rule bg-paper p-6 shadow-lg">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <h3 className="font-bold text-base text-ink">
                {UI_STRINGS.addDepositButton}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                aria-label={UI_STRINGS.cancelButton}
                className="rounded-sm p-1 text-muted-foreground hover:bg-muted hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-4">
              <div>
                <label
                  htmlFor="new-deposit-date"
                  className="block font-medium text-xs text-ink"
                >
                  Tanggal Setoran
                </label>
                <input
                  id="new-deposit-date"
                  type="date"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                />
              </div>

              <div>
                <label
                  htmlFor="new-deposit-nasabah"
                  className="block font-medium text-xs text-ink"
                >
                  Nasabah
                </label>
                <select
                  id="new-deposit-nasabah"
                  value={newNasabahId}
                  onChange={(e) => setNewNasabahId(e.target.value)}
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                >
                  <option value="">Pilih Nasabah</option>
                  {nasabahList
                    .filter((n) => n.is_active)
                    .map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.name}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="new-deposit-waste-type"
                  className="block font-medium text-xs text-ink"
                >
                  Jenis Sampah
                </label>
                <select
                  id="new-deposit-waste-type"
                  value={newWasteTypeId}
                  onChange={(e) => setNewWasteTypeId(e.target.value)}
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                >
                  <option value="">Pilih Jenis Sampah</option>
                  {wasteTypes
                    .filter((w) => w.is_active)
                    .map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name_id}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="new-deposit-weight"
                  className="block font-medium text-xs text-ink"
                >
                  Berat (kg)
                </label>
                <input
                  id="new-deposit-weight"
                  type="text"
                  inputMode="decimal"
                  value={newWeightKg}
                  onChange={(e) => setNewWeightKg(e.target.value)}
                  placeholder="Contoh: 2.500"
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="min-h-[40px] rounded-sm border border-rule px-4 py-2 text-xs font-medium text-ink hover:bg-muted"
                >
                  {UI_STRINGS.cancelButton}
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-sm bg-sprout px-4 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>{UI_STRINGS.saveButton}</span>
                </button>
              </div>
            </form>
          </div>
        </dialog>
      )}

      {editingDeposit && (
        <dialog
          open
          aria-modal="true"
          className="fixed inset-0 z-50 flex h-full w-full max-h-none max-w-none items-center justify-center border-none bg-black/40 p-4"
        >
          <div className="w-full max-w-md rounded-sm border border-rule bg-paper p-6 shadow-lg">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <h3 className="font-bold text-base text-ink">
                Ubah Setoran #{editingDeposit.id}
              </h3>
              <button
                type="button"
                onClick={() => setEditingDeposit(null)}
                aria-label={UI_STRINGS.cancelButton}
                className="rounded-sm p-1 text-muted-foreground hover:bg-muted hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleUpdateSubmit} className="mt-4 space-y-4">
              <div>
                <label
                  htmlFor="edit-deposit-date"
                  className="block font-medium text-xs text-ink"
                >
                  Tanggal Setoran
                </label>
                <input
                  id="edit-deposit-date"
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                />
              </div>

              <div>
                <label
                  htmlFor="edit-deposit-weight"
                  className="block font-medium text-xs text-ink"
                >
                  Berat (kg)
                </label>
                <input
                  id="edit-deposit-weight"
                  type="text"
                  inputMode="decimal"
                  value={editWeightKg}
                  onChange={(e) => setEditWeightKg(e.target.value)}
                  required
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingDeposit(null)}
                  className="min-h-[40px] rounded-sm border border-rule px-4 py-2 text-xs font-medium text-ink hover:bg-muted"
                >
                  {UI_STRINGS.cancelButton}
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-sm bg-sprout px-4 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>{UI_STRINGS.saveButton}</span>
                </button>
              </div>
            </form>
          </div>
        </dialog>
      )}

      {deletingDepositId !== null && (
        <dialog
          open
          aria-modal="true"
          className="fixed inset-0 z-50 flex h-full w-full max-h-none max-w-none items-center justify-center border-none bg-black/40 p-4"
        >
          <div className="w-full max-w-sm rounded-sm border border-rule bg-paper p-6 shadow-lg">
            <h3 className="font-bold text-base text-ink">Hapus Setoran</h3>
            <p className="mt-2 text-xs text-muted-foreground">
              Apakah Anda yakin ingin menghapus data setoran ini? Tindakan ini
              dapat dibatalkan dari riwayat.
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeletingDepositId(null)}
                className="min-h-[40px] rounded-sm border border-rule px-4 py-2 text-xs font-medium text-ink hover:bg-muted"
              >
                {UI_STRINGS.cancelButton}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(deletingDepositId)}
                disabled={deleteMutation.isPending}
                className="flex min-h-[40px] items-center gap-1.5 rounded-sm bg-brick px-4 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{UI_STRINGS.deleteButton}</span>
              </button>
            </div>
          </div>
        </dialog>
      )}
    </div>
  );
}
