import { render, screen } from '@testing-library/react'

import { App } from './App'

describe('RiskFlow application shell', () => {
  it('presents the current deterministic foundation', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', {
        name: /decisiones de riesgo que se pueden explicar y auditar/i,
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/base determinista lista/i)).toBeInTheDocument()
    expect(screen.getByText(/pedidos sintéticos reproducibles/i)).toBeInTheDocument()
  })
})

