/** Shared Tailwind class names for form controls on light surfaces. */

export function inputClassName(hasError = false): string {
  const base =
    'block w-full rounded-md border bg-white px-3 py-2.5 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:ring-2 focus:outline-none disabled:bg-slate-100 sm:text-sm'
  return hasError
    ? `${base} border-red-400 focus:border-red-500 focus:ring-red-200`
    : `${base} border-slate-300 focus:border-brand-500 focus:ring-brand-200`
}

export const labelClassName = 'block text-sm font-medium text-slate-800'

export const primaryButtonClassName =
  'inline-flex items-center justify-center gap-2 rounded-md bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70'

export const secondaryButtonClassName =
  'inline-flex items-center justify-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-300 hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70'
