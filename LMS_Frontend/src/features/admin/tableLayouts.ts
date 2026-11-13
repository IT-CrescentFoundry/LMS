/**
 * Responsive table classes. Below the chosen breakpoint every row becomes a
 * stacked card whose cells carry their column label; from it, a normal table.
 * Wide tables (many columns, long IDs) switch at `xl` so no column is squeezed
 * or clipped at tablet / small-laptop widths. The class strings are written out
 * in full so Tailwind can find them.
 */
export const TABLE_LAYOUTS = {
  md: {
    head: 'hidden border-b border-slate-200 bg-slate-50 md:table-header-group',
    body: 'block divide-y divide-slate-100 md:table-row-group',
    row: 'block px-4 py-3 md:table-row md:p-0',
    cell: 'flex gap-3 py-1 md:table-cell md:px-4 md:py-3 md:align-top',
    label: 'w-28 shrink-0 text-xs font-medium text-slate-500 md:hidden',
    detailRow: 'block bg-slate-50 md:table-row',
    detailCell: 'block px-4 py-3 md:table-cell',
  },
  xl: {
    head: 'hidden border-b border-slate-200 bg-slate-50 xl:table-header-group',
    body: 'block divide-y divide-slate-100 xl:table-row-group',
    row: 'block px-4 py-3 xl:table-row xl:p-0',
    cell: 'flex gap-3 py-1 xl:table-cell xl:px-4 xl:py-3 xl:align-top',
    label: 'w-28 shrink-0 text-xs font-medium text-slate-500 xl:hidden',
    detailRow: 'block bg-slate-50 xl:table-row',
    detailCell: 'block px-4 py-3 xl:table-cell',
  },
} as const

export type TableLayout = keyof typeof TABLE_LAYOUTS

/** Card around a table: scrolls horizontally rather than ever clipping a column. */
export const TABLE_CONTAINER = 'overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm'
