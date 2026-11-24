import type { Level, MatrixItem } from '../../types/competency'

export function levelText(level: Level | null): string {
  return level ? `${level.code} · ${level.label}` : '—'
}

/** Items grouped by their group label, in display order. */
export function groupItems(items: readonly MatrixItem[]): { label: string | null; items: MatrixItem[] }[] {
  const groups: { label: string | null; items: MatrixItem[] }[] = []
  for (const item of items) {
    const last = groups[groups.length - 1]
    if (last && last.label === item.group_label) last.items.push(item)
    else groups.push({ label: item.group_label, items: [item] })
  }
  return groups
}
