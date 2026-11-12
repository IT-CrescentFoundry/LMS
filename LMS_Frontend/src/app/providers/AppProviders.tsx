import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

import { createQueryClient } from './queryClient'

interface AppProvidersProps {
  children: ReactNode
  /** Tests inject an isolated client; the app creates one on first render. */
  queryClient?: QueryClient
}

/**
 * Application-wide providers. i18n is initialised by importing `src/i18n`
 * (see main.tsx) and needs no provider.
 */
export function AppProviders({ children, queryClient }: AppProvidersProps) {
  const [client] = useState(() => queryClient ?? createQueryClient())
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
