import { AppState, AppStateStatus } from 'react-native';
import cache from './cache';

interface MemoryConfig {
  maxMemoryUsage: number; // in MB
  cleanupInterval: number; // in milliseconds
  backgroundCleanupDelay: number; // delay before background cleanup
}

class MemoryManager {
  private static instance: MemoryManager;
  private config: MemoryConfig = {
    maxMemoryUsage: 100, // 100MB default
    cleanupInterval: 60000, // 1 minute
    backgroundCleanupDelay: 5000, // 5 seconds after background
  };
  
  private cleanupTimer: ReturnType<typeof setInterval> | null = null;
  private isBackgroundMode = false;
  private memoryWarnings = 0;

  static getInstance(): MemoryManager {
    if (!MemoryManager.instance) {
      MemoryManager.instance = new MemoryManager();
    }
    return MemoryManager.instance;
  }

  initialize(config?: Partial<MemoryConfig>): void {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    // Start periodic cleanup
    this.startPeriodicCleanup();

    // Listen for app state changes
    AppState.addEventListener('change', this.handleAppStateChange.bind(this));

    // Set up memory pressure warnings (if available)
    this.setupMemoryWarnings();
  }

  private startPeriodicCleanup(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
    }

    this.cleanupTimer = setInterval(async () => {
      await this.performCleanup();
    }, this.config.cleanupInterval);
  }

  private async handleAppStateChange(nextAppState: AppStateStatus): Promise<void> {
    const wasBackground = this.isBackgroundMode;
    this.isBackgroundMode = nextAppState === 'background';

    if (this.isBackgroundMode && !wasBackground) {
      // App went to background - schedule cleanup
      setTimeout(async () => {
        await this.performBackgroundCleanup();
      }, this.config.backgroundCleanupDelay);
    } else if (!this.isBackgroundMode && wasBackground) {
      // App came to foreground - optimize for performance
      await this.performForegroundOptimization();
    }
  }

  private async performCleanup(): Promise<void> {
    try {
      // Remove expired cache items
      const removedCount = await cache.removeExpired();
      
      // Get cache stats
      const stats = await cache.getStats();
      
      // Log cleanup results (only in development)
      if (__DEV__) {
        console.log(`[MemoryManager] Cleanup completed: removed ${removedCount} expired items`);
        console.log(`[MemoryManager] Cache stats:`, stats);
      }

      // If cache is still large, perform aggressive cleanup
      if (stats.totalSize > this.config.maxMemoryUsage * 1024 * 1024 * 0.8) {
        await this.performAggressiveCleanup();
      }
    } catch (error) {
      console.error('[MemoryManager] Cleanup error:', error);
    }
  }

  private async performBackgroundCleanup(): Promise<void> {
    try {
      // More aggressive cleanup in background
      await this.performAggressiveCleanup();
      
      // Clear non-essential cache items
      await this.clearNonEssentialCache();
      
      if (__DEV__) {
        console.log('[MemoryManager] Background cleanup completed');
      }
    } catch (error) {
      console.error('[MemoryManager] Background cleanup error:', error);
    }
  }

  private async performForegroundOptimization(): Promise<void> {
    try {
      // Pre-warm essential cache items
      await this.preWarmCache();
      
      if (__DEV__) {
        console.log('[MemoryManager] Foreground optimization completed');
      }
    } catch (error) {
      console.error('[MemoryManager] Foreground optimization error:', error);
    }
  }

  private async performAggressiveCleanup(): Promise<void> {
    try {
      // Force cleanup of expired items
      await cache.removeExpired();
      
      // Clear cache with shorter TTL items
      await this.clearShortLivedCache();
      
      // Reduce cache size limit temporarily
      const originalMaxSize = 50 * 1024 * 1024; // 50MB
      cache.setMaxCacheSize(originalMaxSize * 0.5); // Reduce to 25MB
      
      // Trigger cleanup
      await cache.removeExpired();
      
      // Restore original size
      cache.setMaxCacheSize(originalMaxSize);
    } catch (error) {
      console.error('[MemoryManager] Aggressive cleanup error:', error);
    }
  }

  private async clearNonEssentialCache(): Promise<void> {
    try {
      // Clear cache items that are not essential for background operation
      const nonEssentialKeys = [
        'health_status',
        'ui_preferences',
        'analytics_data',
        'temp_data',
      ];

      for (const key of nonEssentialKeys) {
        await cache.remove(key);
      }
    } catch (error) {
      console.error('[MemoryManager] Clear non-essential cache error:', error);
    }
  }

  private async clearShortLivedCache(): Promise<void> {
    try {
      // This would require modification to cache service to support filtering by TTL
      // For now, we'll clear common short-lived cache keys
      const shortLivedKeys = [
        'temp_session',
        'draft_data',
        'preview_data',
      ];

      for (const key of shortLivedKeys) {
        await cache.remove(key);
      }
    } catch (error) {
      console.error('[MemoryManager] Clear short-lived cache error:', error);
    }
  }

  private async preWarmCache(): Promise<void> {
    try {
      // Pre-warm essential cache items that should be ready when user returns
      // This is app-specific and would need to be implemented based on usage patterns
      
      if (__DEV__) {
        console.log('[MemoryManager] Cache pre-warming completed');
      }
    } catch (error) {
      console.error('[MemoryManager] Pre-warm cache error:', error);
    }
  }

  private setupMemoryWarnings(): void {
    // This would be platform-specific for memory pressure warnings
    // For now, we'll use a simple approach
    if (__DEV__) {
      setInterval(async () => {
        const stats = await cache.getStats();
        const sizeInMB = stats.totalSize / (1024 * 1024);
        
        if (sizeInMB > this.config.maxMemoryUsage * 0.9) {
          this.memoryWarnings++;
          console.warn(`[MemoryManager] High memory usage: ${sizeInMB.toFixed(2)}MB`);
          
          if (this.memoryWarnings > 3) {
            console.warn('[MemoryManager] Triggering emergency cleanup');
            await this.performAggressiveCleanup();
            this.memoryWarnings = 0;
          }
        } else {
          this.memoryWarnings = 0;
        }
      }, 30000); // Check every 30 seconds
    }
  }

  async getMemoryUsage(): Promise<{
    cacheSize: number;
    cacheSizeMB: number;
    itemCount: number;
    hitRate: number;
    isBackground: boolean;
  }> {
    const stats = await cache.getStats();
    
    return {
      cacheSize: stats.totalSize,
      cacheSizeMB: stats.totalSize / (1024 * 1024),
      itemCount: stats.totalItems,
      hitRate: stats.hitRate,
      isBackground: this.isBackgroundMode,
    };
  }

  async forceCleanup(): Promise<void> {
    await this.performAggressiveCleanup();
  }

  updateConfig(config: Partial<MemoryConfig>): void {
    this.config = { ...this.config, ...config };
    
    // Restart periodic cleanup with new interval
    this.startPeriodicCleanup();
  }

  cleanup(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
  }
}

export default MemoryManager.getInstance();
