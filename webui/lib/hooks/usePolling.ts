import useSWR from 'swr';

export function usePolling<T>(
  key: string,
  fetcher: () => Promise<T>,
  interval: number,
  options?: {
    enabled?: boolean;
  }
) {
  return useSWR(
    options?.enabled !== false ? key : null,
    fetcher,
    {
      refreshInterval: interval,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: interval / 2,
    }
  );
}
