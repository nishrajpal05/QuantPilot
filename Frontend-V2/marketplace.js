import { supabase } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function authHeaders() {
  const { data: { session } } = await supabase.auth.getSession()
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session?.access_token ?? ''}`,
  }
}

export async function fetchMarketplace(params = {}) {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${API_BASE}/api/v1/marketplace?${qs}`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch marketplace')
  return res.json()
}

export async function cloneStrategy(strategyId) {
  const res = await fetch(`${API_BASE}/api/v1/marketplace/${strategyId}/clone`, {
    method: 'POST',
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Clone failed')
  return res.json()
}

export async function analyzePortfolio(symbols, startDate, endDate) {
  const res = await fetch(`${API_BASE}/api/v1/portfolio/analyze`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({ symbols, start_date: startDate, end_date: endDate }),
  })
  if (!res.ok) throw new Error('Portfolio analysis failed')
  return res.json()
}

export async function createAlert(strategyId, type, destination) {
  const res = await fetch(`${API_BASE}/api/v1/alerts`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({ strategy_id: strategyId, type, destination }),
  })
  if (!res.ok) throw new Error('Failed to create alert')
  return res.json()
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/api/v1/alerts`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch alerts')
  return res.json()
}

export async function deleteAlert(alertId) {
  const res = await fetch(`${API_BASE}/api/v1/alerts/${alertId}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete alert')
  return res.json()
}
