import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

/**
 * CorrelationMatrix
 * @param {{
 *   matrix: { [symbol: string]: { [symbol: string]: number } }
 *   symbols: string[]
 * }} props
 */
export default function CorrelationMatrix({ matrix = {}, symbols = [] }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!symbols.length || !Object.keys(matrix).length) return

    const el     = svgRef.current
    const size   = Math.min(el.clientWidth, 420)
    const margin = { top: 40, right: 10, bottom: 10, left: 60 }
    const inner  = size - margin.left - margin.right - margin.top

    d3.select(el).selectAll('*').remove()

    const svg = d3.select(el)
      .attr('width', size)
      .attr('height', size)

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const cellSize = inner / symbols.length

    // Color scale: -1 = red, 0 = dark, +1 = green
    const colorScale = d3.scaleSequential()
      .domain([-1, 1])
      .interpolator(t => {
        if (t < 0.5) return d3.interpolateRgb('#ef4444', '#1e293b')(t * 2)
        return d3.interpolateRgb('#1e293b', '#22c55e')((t - 0.5) * 2)
      })

    // Draw cells
    symbols.forEach((rowSym, ri) => {
      symbols.forEach((colSym, ci) => {
        const val = matrix[rowSym]?.[colSym] ?? 0

        g.append('rect')
          .attr('x', ci * cellSize)
          .attr('y', ri * cellSize)
          .attr('width', cellSize - 2)
          .attr('height', cellSize - 2)
          .attr('rx', 3)
          .attr('fill', colorScale(val))
          .attr('opacity', 0.9)

        if (cellSize > 28) {
          g.append('text')
            .attr('x', ci * cellSize + cellSize / 2 - 1)
            .attr('y', ri * cellSize + cellSize / 2 + 4)
            .attr('text-anchor', 'middle')
            .attr('font-size', Math.min(10, cellSize * 0.28))
            .attr('fill', Math.abs(val) > 0.5 ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.6)')
            .attr('font-family', "'JetBrains Mono', monospace")
            .text(val.toFixed(2))
        }
      })
    })

    // Column labels (top)
    symbols.forEach((sym, i) => {
      g.append('text')
        .attr('x', i * cellSize + cellSize / 2)
        .attr('y', -8)
        .attr('text-anchor', 'middle')
        .attr('font-size', Math.min(10, cellSize * 0.3))
        .attr('fill', '#64748b')
        .attr('font-family', 'system-ui, sans-serif')
        .text(sym)
    })

    // Row labels (left)
    symbols.forEach((sym, i) => {
      g.append('text')
        .attr('x', -8)
        .attr('y', i * cellSize + cellSize / 2 + 4)
        .attr('text-anchor', 'end')
        .attr('font-size', Math.min(10, cellSize * 0.3))
        .attr('fill', '#64748b')
        .attr('font-family', 'system-ui, sans-serif')
        .text(sym)
    })

    // Color bar legend
    const legendW = Math.min(inner, 160)
    const legendX = (inner - legendW) / 2
    const defs    = svg.append('defs')
    const gradId  = 'corr-grad'
    const grad    = defs.append('linearGradient').attr('id', gradId)

    grad.selectAll('stop')
      .data(d3.range(0, 1.01, 0.1))
      .join('stop')
      .attr('offset', d => `${d * 100}%`)
      .attr('stop-color', d => colorScale(d * 2 - 1))

    const legendG = g.append('g').attr('transform', `translate(${legendX},${inner + 14})`)
    legendG.append('rect').attr('width', legendW).attr('height', 8).attr('rx', 4).attr('fill', `url(#${gradId})`)
    legendG.append('text').attr('x', 0).attr('y', 20).attr('fill', '#475569').attr('font-size', 9).text('-1')
    legendG.append('text').attr('x', legendW / 2).attr('y', 20).attr('text-anchor', 'middle').attr('fill', '#475569').attr('font-size', 9).text('0')
    legendG.append('text').attr('x', legendW).attr('y', 20).attr('text-anchor', 'end').attr('fill', '#475569').attr('font-size', 9).text('+1')
  }, [matrix, symbols])

  if (!symbols.length) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#475569', fontSize: 13 }}>
        Run portfolio analysis to see correlation matrix
      </div>
    )
  }

  return (
    <div className="corr-matrix">
      <span className="corr-matrix__title">Correlation Matrix</span>
      <div style={{ overflowX: 'auto' }}>
        <svg ref={svgRef} style={{ display: 'block', margin: '0 auto' }} />
      </div>
      <style>{`
        .corr-matrix { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 16px; }
        .corr-matrix__title { font-size: 13px; font-weight: 600; color: #e2e8f0; display: block; margin-bottom: 14px; }
      `}</style>
    </div>
  )
}
