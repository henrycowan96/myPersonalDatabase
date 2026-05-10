import AsyncStorage from '@react-native-async-storage/async-storage';

interface CacheItem<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

interface CacheStats {
  totalItems: number;
  totalSize: number;
  hitRate: number;
  misses: number;
  hits: number;
}

class CacheService {
  private static instance: CacheService;
  private stats: CacheStats = {
    totalItems: 0,
    totalSize: 0,
    hitRate: 0,
    misses: 0,
    hits: 0,
  };
  private maxCacheSize = 50 * 1024 * 1024; // 50MB default
  private cleanupThreshold = 0.8; // Clean up when 80% full

  static getInstance(): CacheService {
    if (!CacheService.instance) {
      CacheService.instance = new CacheService();
    }
    return CacheService.instance;
  }

  async set<T>(key: string, data: T, ttl: number = 300000): Promise<void> {
    try {
      const item: CacheItem<T> = {
        data,
        timestamp: Date.now(),
        ttl,
      };

      const serialized = JSON.stringify(item);
      const size = new Blob([serialized]).size;

      // Check if we need to clean up before adding
      await this.checkAndCleanup(size);

      await AsyncStorage.setItem(`cache_${key}`, serialized);
      
      this.stats.totalItems++;
      this.stats.totalSize += size;
    } catch (error) {
      console.error('Cache set error:', error);
      // If storage is full, try to clean up and retry
      if (error instanceof Error && error.message.includes('QuotaExceededError')) {
        await this.forceCleanup();
        await this.set(key, data, ttl);
      }
    }
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const serialized = await AsyncStorage.getItem(`cache_${key}`);
      if (!serialized) {
        this.stats.misses++;
        this.updateHitRate();
        return null;
      }

      const item: CacheItem<T> = JSON.parse(serialized);
      const now = Date.now();

      // Check if item has expired
      if (now - item.timestamp > item.ttl) {
        await this.remove(key);
        this.stats.misses++;
        this.updateHitRate();
        return null;
      }

      this.stats.hits++;
      this.updateHitRate();
      return item.data;
    } catch (error) {
      console.error('Cache get error:', error);
      this.stats.misses++;
      this.updateHitRate();
      return null;
    }
  }

  async remove(key: string): Promise<void> {
    try {
      const serialized = await AsyncStorage.getItem(`cache_${key}`);
      if (serialized) {
        const size = new Blob([serialized]).size;
        await AsyncStorage.removeItem(`cache_${key}`);
        this.stats.totalItems = Math.max(0, this.stats.totalItems - 1);
        this.stats.totalSize = Math.max(0, this.stats.totalSize - size);
      }
    } catch (error) {
      console.error('Cache remove error:', error);
    }
  }

  async clear(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(key => key.startsWith('cache_'));
      await AsyncStorage.multiRemove(cacheKeys);
      this.stats = {
        totalItems: 0,
        totalSize: 0,
        hitRate: 0,
        misses: 0,
        hits: 0,
      };
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }

  private updateHitRate(): void {
    const total = this.stats.hits + this.stats.misses;
    this.stats.hitRate = total > 0 ? this.stats.hits / total : 0;
  }

  private async checkAndCleanup(newItemSize: number): Promise<void> {
    const projectedSize = this.stats.totalSize + newItemSize;
    const threshold = this.maxCacheSize * this.cleanupThreshold;

    if (projectedSize > threshold) {
      await this.cleanup();
    }
  }

  private async cleanup(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(key => key.startsWith('cache_'));
      
      const items: Array<{ key: string; item: CacheItem<any>; size: number }> = [];
      
      for (const key of cacheKeys) {
        try {
          const serialized = await AsyncStorage.getItem(key);
          if (serialized) {
            const item: CacheItem<any> = JSON.parse(serialized);
            const size = new Blob([serialized]).size;
            const now = Date.now();
            
            // Skip expired items
            if (now - item.timestamp > item.ttl) {
              await AsyncStorage.removeItem(key);
              this.stats.totalItems = Math.max(0, this.stats.totalItems - 1);
              this.stats.totalSize = Math.max(0, this.stats.totalSize - size);
              continue;
            }
            
            items.push({ key, item, size });
          }
        } catch (error) {
          // Remove corrupted items
          await AsyncStorage.removeItem(key);
        }
      }

      // Sort by oldest first (LRU strategy)
      items.sort((a, b) => a.item.timestamp - b.item.timestamp);

      // Remove oldest items until we're under the threshold
      const targetSize = this.maxCacheSize * 0.6; // Clean up to 60%
      let currentSize = this.stats.totalSize;

      for (const { key, size } of items) {
        if (currentSize <= targetSize) break;
        
        await AsyncStorage.removeItem(key);
        this.stats.totalItems = Math.max(0, this.stats.totalItems - 1);
        this.stats.totalSize = Math.max(0, this.stats.totalSize - size);
        currentSize -= size;
      }
    } catch (error) {
      console.error('Cache cleanup error:', error);
    }
  }

  private async forceCleanup(): Promise<void> {
    try {
      await this.clear();
    } catch (error) {
      console.error('Force cleanup error:', error);
    }
  }

  async getStats(): Promise<CacheStats> {
    return { ...this.stats };
  }

  async getExpiredKeys(): Promise<string[]> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(key => key.startsWith('cache_'));
      const expiredKeys: string[] = [];
      const now = Date.now();

      for (const key of cacheKeys) {
        try {
          const serialized = await AsyncStorage.getItem(key);
          if (serialized) {
            const item: CacheItem<any> = JSON.parse(serialized);
            if (now - item.timestamp > item.ttl) {
              expiredKeys.push(key);
            }
          }
        } catch (error) {
          expiredKeys.push(key); // Remove corrupted items
        }
      }

      return expiredKeys;
    } catch (error) {
      console.error('Get expired keys error:', error);
      return [];
    }
  }

  async removeExpired(): Promise<number> {
    try {
      const expiredKeys = await this.getExpiredKeys();
      if (expiredKeys.length > 0) {
        await AsyncStorage.multiRemove(expiredKeys);
        this.stats.totalItems = Math.max(0, this.stats.totalItems - expiredKeys.length);
      }
      return expiredKeys.length;
    } catch (error) {
      console.error('Remove expired error:', error);
      return 0;
    }
  }

  setMaxCacheSize(size: number): void {
    this.maxCacheSize = size;
  }

  setCleanupThreshold(threshold: number): void {
    this.cleanupThreshold = Math.max(0.1, Math.min(0.9, threshold));
  }
}

export default CacheService.getInstance();
