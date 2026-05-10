import { useState, useEffect, useCallback, useRef } from 'react';
import cache from '../lib/cache';

interface UseCacheOptions<T> {
  ttl?: number;
  staleWhileRevalidate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

interface UseCacheResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  invalidate: () => Promise<void>;
  update: (newData: T) => Promise<void>;
}

export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseCacheOptions<T> = {}
): UseCacheResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const {
    ttl = 300000, // 5 minutes default
    staleWhileRevalidate = true,
    onSuccess,
    onError,
  } = options;

  // Use a ref to store the latest fetcher to avoid dependency issues
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const fetchData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);

      // Try to get from cache first (unless force refresh)
      if (!forceRefresh) {
        const cachedData = await cache.get<T>(key);
        if (cachedData !== null) {
          setData(cachedData);
          onSuccess?.(cachedData);
          
          // Background fetch disabled to prevent 503 errors and infinite loops
          // If stale-while-revalidate is needed in the future, implement with proper error boundaries
          return;
        }
      }

      // Fetch fresh data using the ref
      const freshData = await fetcherRef.current();
      await cache.set(key, freshData, ttl);
      setData(freshData);
      onSuccess?.(freshData);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [key, ttl, staleWhileRevalidate]); // Removed fetcher, onSuccess, onError from dependencies

  const refetch = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  const invalidate = useCallback(async () => {
    await cache.remove(key);
    setData(null);
  }, [key]);

  const update = useCallback(async (newData: T) => {
    await cache.set(key, newData, ttl);
    setData(newData);
  }, [key, ttl]);

  // Only run effect when key changes, not when fetchData changes
  useEffect(() => {
    fetchData();
  }, [key]); // Only depend on key

  return {
    data,
    loading,
    error,
    refetch,
    invalidate,
    update,
  };
}

export function useCacheMutation<T>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async <R>(
    key: string,
    mutationFn: (currentData: T | null) => Promise<R>,
    options: { ttl?: number; onSuccess?: (data: R) => void } = {}
  ): Promise<R | null> => {
    try {
      setLoading(true);
      setError(null);

      const currentData = await cache.get<T>(key);
      const result = await mutationFn(currentData);
      
      if (options.ttl !== undefined) {
        await cache.set(key, result, options.ttl);
      }
      
      options.onSuccess?.(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Mutation failed');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mutate,
    loading,
    error,
  };
}

export function useCacheInvalidation() {
  const invalidate = useCallback(async (pattern?: string) => {
    if (pattern) {
      // This would require cache service to support pattern matching
      // For now, we'll clear all cache
      await cache.clear();
    } else {
      await cache.clear();
    }
  }, []);

  const invalidateMultiple = useCallback(async (keys: string[]) => {
    await Promise.all(keys.map(key => cache.remove(key)));
  }, []);

  return {
    invalidate,
    invalidateMultiple,
  };
}
