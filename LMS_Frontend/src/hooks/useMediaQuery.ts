import { useSyncExternalStore } from 'react'

/**
 * Tracks a CSS media query. Where `matchMedia` is unavailable (tests, very old
 * browsers) it reports `fallback`.
 */
export function useMediaQuery(query: string, fallback = true): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window.matchMedia !== 'function') return () => undefined
      const list = window.matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    },
    () => (typeof window.matchMedia === 'function' ? window.matchMedia(query).matches : fallback),
    () => fallback,
  )
}

/** Tailwind's `lg` breakpoint: the organisation tree and details sit side by side. */
export const WIDE_LAYOUT_QUERY = '(min-width: 1024px)'
