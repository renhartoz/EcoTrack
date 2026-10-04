import { useParams } from "react-router";

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold tracking-tight text-ink">
        Tinjau Unggahan #{id}
      </h2>
      <div className="rounded-sm border border-rule p-4 text-sm text-muted-foreground">
        Halaman verifikasi dan konfirmasi baris setoran.
      </div>
    </div>
  );
}
