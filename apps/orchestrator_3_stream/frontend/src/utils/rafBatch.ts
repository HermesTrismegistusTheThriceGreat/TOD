/**
 * RAF Batching Utility
 *
 * Batches high-frequency updates into single animation frames.
 * Prevents UI freezing from rapid reactive updates.
 */

type BatchCallback<T> = (items: Map<string, T>) => void

export class RafBatcher<T> {
  private pending: Map<string, T> = new Map()
  private frameId: number | null = null
  private callback: BatchCallback<T>

  constructor(callback: BatchCallback<T>) {
    this.callback = callback
  }

  /**
   * Queue an update. Latest value wins per key.
   */
  add(key: string, value: T): void {
    this.pending.set(key, value)
    this.scheduleFlush()
  }

  private scheduleFlush(): void {
    if (this.frameId !== null) return

    this.frameId = requestAnimationFrame(() => {
      this.frameId = null
      if (this.pending.size === 0) return

      const batch = new Map(this.pending)
      this.pending.clear()
      this.callback(batch)
    })
  }

  clear(): void {
    if (this.frameId !== null) {
      cancelAnimationFrame(this.frameId)
      this.frameId = null
    }
    this.pending.clear()
  }
}

/**
 * Creates a debounced function that uses requestAnimationFrame.
 */
export function rafDebounce<T extends (...args: unknown[]) => void>(fn: T): T {
  let frameId: number | null = null

  return ((...args: unknown[]) => {
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
    }
    frameId = requestAnimationFrame(() => {
      frameId = null
      fn(...args)
    })
  }) as T
}
