interface StatusCardProps {
  eyebrow: string
  title: string
  description: string
}

export function StatusCard({ eyebrow, title, description }: StatusCardProps) {
  return (
    <article className="status-card">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="status-row" aria-label="Modo actual">
        <span className="status-dot" aria-hidden="true" />
        Fase 1 verificada localmente
      </div>
    </article>
  )
}

