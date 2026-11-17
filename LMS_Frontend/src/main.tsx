import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { i18nReady } from './i18n'
import './styles/index.css'

import App from './App'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element #root not found in index.html')
}

// The first render waits for the initial language's catalogue (bn, hi and gu are
// downloaded on demand), so the interface never flashes English first.
void i18nReady.then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
