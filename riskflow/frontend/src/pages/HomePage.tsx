import type { ReactNode } from 'react'

interface HomePageProps {
  children: ReactNode
}

const capabilities = [
  'Pedidos sintéticos reproducibles',
  'Puntuación explicable de 0 a 100',
  'Cinco escenarios de demostración',
]

export function HomePage({ children }: HomePageProps) {
  return (
    <main>
      <header className="hero">
        <div className="brand" aria-label="RiskFlow">
          <span className="brand-mark" aria-hidden="true">
            RF
          </span>
          <span>RiskFlow</span>
        </div>
        <div className="hero-grid">
          <section>
            <p className="eyebrow">Workflow agéntico · datos 100% sintéticos</p>
            <h1>Decisiones de riesgo que se pueden explicar y auditar.</h1>
            <p className="lede">
              Una demostración segura de reglas deterministas, revisión humana y recuperación de
              operaciones para pedidos de comercio electrónico.
            </p>
            <ul className="capability-list">
              {capabilities.map((capability) => (
                <li key={capability}>{capability}</li>
              ))}
            </ul>
          </section>
          {children}
        </div>
      </header>
      <section className="next-phase" aria-labelledby="next-phase-title">
        <p className="eyebrow">Próximo hito</p>
        <h2 id="next-phase-title">Orquestación durable</h2>
        <p>
          La fase 2 conectará los estados, el inventario y el pago simulado con compensación
          automática ante fallos.
        </p>
      </section>
    </main>
  )
}

