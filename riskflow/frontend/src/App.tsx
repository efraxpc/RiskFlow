import { StatusCard } from './components/StatusCard'
import { HomePage } from './pages/HomePage'

export function App() {
  return (
    <HomePage>
      <StatusCard
        eyebrow="Estado del proyecto"
        title="Base determinista lista"
        description="El dominio, los escenarios reproducibles y las reglas de riesgo ya pueden verificarse sin una clave de API."
      />
    </HomePage>
  )
}

