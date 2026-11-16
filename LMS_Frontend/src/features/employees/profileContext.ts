import { useOutletContext } from 'react-router'

import type { Employee } from '../../types/employee'

export interface ProfileContext {
  employee: Employee
  /** The requested business date, or undefined for today (the server's business date). */
  asOf: string | undefined
}

/** For the tab pages rendered in the profile's <Outlet/>. */
export function useProfile(): ProfileContext {
  return useOutletContext<ProfileContext>()
}
