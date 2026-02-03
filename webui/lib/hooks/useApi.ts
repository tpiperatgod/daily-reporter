import useSWR, { useSWRConfig } from 'swr';

interface UseApiOptions<T> {
  fetcher: () => Promise<T>;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useApi<T>(
  key: string | null,
  options: UseApiOptions<T>
) {
  const { mutate: globalMutate } = useSWRConfig();

  const { data, error, mutate } = useSWR(
    key,
    options.fetcher,
    {
      onSuccess: options.onSuccess,
      onError: options.onError,
      revalidateOnFocus: false,
    }
  );

  const create = async <C>(createFn: () => Promise<C>): Promise<C> => {
    const result = await createFn();
    await mutate();
    return result;
  };

  const update = async <U>(updateFn: () => Promise<U>): Promise<U> => {
    const result = await updateFn();
    await mutate();
    return result;
  };

  const remove = async (deleteFn: () => Promise<void>): Promise<void> => {
    await deleteFn();
    await mutate();
  };

  return {
    data,
    error,
    isLoading: !error && !data,
    mutate,
    globalMutate,
    create,
    update,
    remove,
  };
}
