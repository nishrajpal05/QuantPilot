
import AgentProgress  from '../components/AgentProgress'
import MonteCarloChart from '../components/MonteCarloChart'
import WalkForward     from '../components/WalkForward'
import ComplianceBadge from '../components/ComplianceBadge'

async function pollBacktestProgress(jobId, onStep) {
  const interval = setInterval(async () => {
    const res    = await fetch(`/api/v1/backtest/${jobId}/status`)
    const status = await res.json()

    const STEP_MAP = { data: 0, strategy: 1, backtest: 2, risk: 3, compliance: 4, audit: 5 }
    onStep(STEP_MAP[status.current_agent] ?? -1)

    if (status.done || status.error) clearInterval(interval)
  }, 1500)
}

export { AgentProgress, MonteCarloChart, WalkForward, ComplianceBadge }
