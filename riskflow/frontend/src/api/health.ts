export interface HealthResponse {
  status: 'ok'
  service: 'riskflow'
  phase: number
}

export async function getHealth(apiUrl: string, signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl}/health`, { signal })
  if (!response.ok) {
    throw new Error(`RiskFlow API respondió con HTTP ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}

