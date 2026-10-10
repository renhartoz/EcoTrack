import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  Edit2,
  Plus,
  Search,
  UserCheck,
  UserX,
  X,
} from "lucide-react";
import { UI_STRINGS } from "@/lib/strings.id";
import {
  createNasabah,
  getNasabahList,
  updateNasabah,
} from "@/services/nasabah";
import type { Nasabah } from "@/types/nasabah";

export function NasabahPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [editingNasabah, setEditingNasabah] = useState<Nasabah | null>(null);
  const [editName, setEditName] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["nasabah-list", searchTerm],
    queryFn: () =>
      getNasabahList({
        q: searchTerm.trim() || undefined,
        page_size: 100,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => createNasabah({ name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["nasabah-list"] });
      setNewName("");
      setIsAddOpen(false);
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      updateNasabah(id, { name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["nasabah-list"] });
      setEditingNasabah(null);
      setEditName("");
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      updateNasabah(id, { is_active: isActive }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["nasabah-list"] });
      setActionError(null);
    },
    onError: (err: Error) => {
      setActionError(err.message || UI_STRINGS.unknownError);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      return;
    }
    setActionError(null);
    createMutation.mutate(newName.trim());
  };

  const handleRenameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingNasabah || !editName.trim()) {
      return;
    }
    setActionError(null);
    renameMutation.mutate({ id: editingNasabah.id, name: editName.trim() });
  };

  const nasabahList = data?.results || [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.nasabahListTitle}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Kelola data dan status keaktifan nasabah bank sampah.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setActionError(null);
            setIsAddOpen(true);
          }}
          className="flex min-h-[44px] items-center justify-center gap-2 rounded-sm bg-sprout px-4 py-2 font-medium text-white transition-opacity hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          <span>{UI_STRINGS.addNasabahButton}</span>
        </button>
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

      <div className="relative">
        <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder={UI_STRINGS.searchNasabahPlaceholder}
          className="min-h-[44px] w-full rounded-sm border border-input bg-paper pr-4 pl-9 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
        />
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

      {!isLoading && !isError && nasabahList.length === 0 && (
        <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
          {searchTerm
            ? "Tidak ada nasabah yang cocok dengan pencarian."
            : "Belum ada data nasabah."}
        </div>
      )}

      {!isLoading && !isError && nasabahList.length > 0 && (
        <div className="divide-y divide-rule rounded-sm border border-rule bg-paper">
          {nasabahList.map((nasabah) => (
            <div
              key={nasabah.id}
              className="flex min-h-[56px] flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-ink">
                    {nasabah.name}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-[11px] font-medium ${
                      nasabah.is_active
                        ? "bg-sprout/10 text-sprout"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {nasabah.is_active ? (
                      <UserCheck className="h-3 w-3" />
                    ) : (
                      <UserX className="h-3 w-3" />
                    )}
                    <span>
                      {nasabah.is_active
                        ? UI_STRINGS.activeStatus
                        : UI_STRINGS.inactiveStatus}
                    </span>
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Terdaftar:{" "}
                  {new Date(nasabah.created_at).toLocaleDateString("id-ID", {
                    dateStyle: "medium",
                  })}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setActionError(null);
                    setEditingNasabah(nasabah);
                    setEditName(nasabah.name);
                  }}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-sm border border-rule px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-muted"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                  <span>{UI_STRINGS.renameButton}</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    toggleActiveMutation.mutate({
                      id: nasabah.id,
                      isActive: !nasabah.is_active,
                    })
                  }
                  disabled={toggleActiveMutation.isPending}
                  className={`flex min-h-[40px] items-center gap-1.5 rounded-sm border px-3 py-1.5 text-xs font-medium transition-colors ${
                    nasabah.is_active
                      ? "border-rule text-muted-foreground hover:bg-muted"
                      : "border-sprout/30 bg-sprout/10 text-sprout hover:bg-sprout/20"
                  }`}
                >
                  {nasabah.is_active ? (
                    <span>Nonaktifkan</span>
                  ) : (
                    <span>Aktifkan</span>
                  )}
                </button>
              </div>
            </div>
          ))}
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
                {UI_STRINGS.addNasabahButton}
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
                  htmlFor="new-nasabah-name"
                  className="block font-medium text-xs text-ink"
                >
                  Nama Lengkap Nasabah
                </label>
                <input
                  id="new-nasabah-name"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Contoh: Siti Aminah"
                  required
                  autoFocus
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
                  disabled={createMutation.isPending || !newName.trim()}
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

      {editingNasabah && (
        <dialog
          open
          aria-modal="true"
          className="fixed inset-0 z-50 flex h-full w-full max-h-none max-w-none items-center justify-center border-none bg-black/40 p-4"
        >
          <div className="w-full max-w-md rounded-sm border border-rule bg-paper p-6 shadow-lg">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <h3 className="font-bold text-base text-ink">
                {UI_STRINGS.renameButton}
              </h3>
              <button
                type="button"
                onClick={() => setEditingNasabah(null)}
                aria-label={UI_STRINGS.cancelButton}
                className="rounded-sm p-1 text-muted-foreground hover:bg-muted hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleRenameSubmit} className="mt-4 space-y-4">
              <div>
                <label
                  htmlFor="edit-nasabah-name"
                  className="block font-medium text-xs text-ink"
                >
                  Nama Nasabah Baru
                </label>
                <input
                  id="edit-nasabah-name"
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  required
                  autoFocus
                  className="mt-1 min-h-[44px] w-full rounded-sm border border-input bg-paper px-3 text-sm text-ink transition-colors focus:border-sprout focus:outline-hidden"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingNasabah(null)}
                  className="min-h-[40px] rounded-sm border border-rule px-4 py-2 text-xs font-medium text-ink hover:bg-muted"
                >
                  {UI_STRINGS.cancelButton}
                </button>
                <button
                  type="submit"
                  disabled={renameMutation.isPending || !editName.trim()}
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
    </div>
  );
}
