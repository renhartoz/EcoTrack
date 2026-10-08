import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUploadDetail, retryUpload } from "@/services/uploads";
import type { UploadDetail } from "@/types/uploads";

export function useUpload(id: number | string | undefined) {
  const queryClient = useQueryClient();

  const query = useQuery<UploadDetail>({
    queryKey: ["upload", id],
    queryFn: () => {
      if (!id) {
        throw new Error("Upload ID is required");
      }
      return getUploadDetail(id);
    },
    enabled: !!id,
    refetchInterval: (q) => {
      const data = q.state.data;
      if (data && data.status === "processing") {
        return 1500;
      }
      return false;
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => {
      if (!id) {
        throw new Error("Upload ID is required");
      }
      return retryUpload(id);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(["upload", id], updated);
    },
  });

  return {
    ...query,
    upload: query.data,
    retry: retryMutation.mutateAsync,
    isRetrying: retryMutation.isPending,
  };
}
