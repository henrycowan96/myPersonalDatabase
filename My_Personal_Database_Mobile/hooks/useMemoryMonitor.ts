import { useState, useEffect, useCallback } from 'react';
import memoryManager from '../lib/memoryManager';
import cache from '../lib/cache';

interface MemoryStats {
  cacheSize: number;
  cacheSizeMB: number;
  itemCount: number;
  hitRate: number;
  isBackground: boolean;
}

interface UseMemoryMonitorOptions {
  interval?: number;
  showAlerts?: boolean;
  threshold?: number; // MB threshold for warnings
}

export function useMemoryMonitor(options: UseMemoryMonitorOptions = {}) {
  const {
    interval = 30000, // 30 seconds default
    showAlerts = false,
    threshold = 40, // 40MB threshold
  } = options;

  const [stats, setStats] = useState<MemoryStats>({
    cacheSize: 0,
    cacheSizeMB: 0,
    itemCount: 0,
    hitRate: 0,
    isBackground: false,
  });
  const [warning, setWarning] = useState<string | null>(null);

  const updateStats = useCallback(async () => {
    try {
      const memoryStats = await memoryManager.getMemoryUsage();
      setStats(memoryStats);

      // Check for memory warnings
      if (memoryStats.cacheSizeMB > threshold) {
        const warningMessage = `High memory usage: ${memoryStats.cacheSizeMB.toFixed(2)}MB`;
        setWarning(warningMessage);
        
        if (showAlerts) {
          console.warn(`[MemoryMonitor] ${warningMessage}`);
        }
      } else {
        setWarning(null);
      }
    } catch (error) {
      console.error('[MemoryMonitor] Error updating stats:', error);
    }
  }, [threshold, showAlerts]);

  useEffect(() => {
    updateStats(); // Initial update

    const intervalId = setInterval(updateStats, interval);

    return () => {
      clearInterval(intervalId);
    };
  }, [updateStats, interval]);

  const forceCleanup = useCallback(async () => {
    try {
      await memoryManager.forceCleanup();
      await updateStats(); // Update stats after cleanup
    } catch (error) {
      console.error('[MemoryMonitor] Force cleanup error:', error);
    }
  }, [updateStats]);

  const clearCache = useCallback(async () => {
    try {
      await cache.clear();
      await updateStats(); // Update stats after clearing
    } catch (error) {
      console.error('[MemoryMonitor] Clear cache error:', error);
    }
  }, [updateStats]);

  return {
    stats,
    warning,
    forceCleanup,
    clearCache,
    updateStats,
  };
}

export function useCacheInvalidation() {
  const invalidateByPattern = useCallback(async (pattern: string) => {
    try {
      // This is a simplified implementation
      // In a real app, you might want to implement pattern matching
      const cacheStats = await cache.getStats();
      
      if (__DEV__) {
        console.log(`[CacheInvalidation] Invalidating cache for pattern: ${pattern}`);
        console.log(`[CacheInvalidation] Current cache stats:`, cacheStats);
      }

      // For now, we'll clear all cache when pattern is provided
      if (pattern.includes('*')) {
        await cache.clear();
      } else {
        await cache.remove(pattern);
      }
    } catch (error) {
      console.error('[CacheInvalidation] Error:', error);
    }
  }, []);

  const invalidateMultiple = useCallback(async (keys: string[]) => {
    try {
      await Promise.all(keys.map(key => cache.remove(key)));
      
      if (__DEV__) {
        console.log(`[CacheInvalidation] Invalidated ${keys.length} cache keys`);
      }
    } catch (error) {
      console.error('[CacheInvalidation] Error invalidating multiple keys:', error);
    }
  }, []);

  const invalidateExpired = useCallback(async () => {
    try {
      const removedCount = await cache.removeExpired();
      
      if (__DEV__) {
        console.log(`[CacheInvalidation] Removed ${removedCount} expired cache items`);
      }
      
      return removedCount;
    } catch (error) {
      console.error('[CacheInvalidation] Error removing expired items:', error);
      return 0;
    }
  }, []);

  return {
    invalidateByPattern,
    invalidateMultiple,
    invalidateExpired,
  };
}

export function useCacheDebug() {
  const [debugInfo, setDebugInfo] = useState<any>(null);

  const getDebugInfo = useCallback(async () => {
    try {
      const stats = await cache.getStats();
      const expiredKeys = await cache.getExpiredKeys();
      const memoryStats = await memoryManager.getMemoryUsage();

      const debugData = {
        cacheStats: stats,
        expiredKeysCount: expiredKeys.length,
        expiredKeys: expiredKeys.slice(0, 10), // Show first 10
        memoryStats,
        timestamp: new Date().toISOString(),
      };

      setDebugInfo(debugData);
      return debugData;
    } catch (error) {
      console.error('[CacheDebug] Error getting debug info:', error);
      return null;
    }
  }, []);

  useEffect(() => {
    if (__DEV__) {
      getDebugInfo();
    }
  }, [getDebugInfo]);

  return {
    debugInfo,
    getDebugInfo,
  };
}
