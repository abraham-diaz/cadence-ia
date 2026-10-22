import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import type { HistoryPoint, SessionStats } from '../../api/types.ts'
import { formatShortDate } from '../../shared/format.ts'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

interface Props {
  history: HistoryPoint[]
  currentId: string
  metric: keyof SessionStats
  unit: string
}

function themeColors() {
  const css = getComputedStyle(document.documentElement)
  const get = (name: string) => css.getPropertyValue(name).trim()
  return {
    line: get('--accent'),
    text: get('--text-secondary'),
    grid: get('--grid'),
    surface: get('--surface'),
    ink: get('--text-primary'),
  }
}

/** One metric across the sessions of a workout type; the open session is highlighted. */
export default function TrendChart({ history, currentId, metric, unit }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)

    const render = () => {
      const c = themeColors()
      chart.setOption(
        {
          animation: false,
          grid: { left: 32, right: 12, top: 12, bottom: 24 },
          xAxis: {
            type: 'category',
            data: history.map((h) => formatShortDate(h.start_time)),
            axisLabel: { color: c.text, hideOverlap: true },
            axisLine: { lineStyle: { color: c.grid } },
            axisTick: { show: false },
          },
          yAxis: {
            type: 'value',
            scale: true,
            splitNumber: 3,
            axisLabel: { color: c.text },
            splitLine: { lineStyle: { color: c.grid } },
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: c.surface,
            borderColor: c.grid,
            textStyle: { color: c.ink },
            valueFormatter: (v: number | null) => (v === null ? '–' : `${Math.round(v)} ${unit}`),
          },
          series: [
            {
              type: 'line',
              connectNulls: true,
              lineStyle: { width: 2, color: c.line },
              itemStyle: { color: c.line, borderColor: c.surface, borderWidth: 2 },
              symbolSize: 8,
              data: history.map((h) => ({
                value: h[metric],
                // Bigger dot for the session being viewed.
                ...(h.id === currentId ? { symbolSize: 14 } : {}),
              })),
            },
          ],
        },
        true,
      )
    }
    render()

    const scheme = window.matchMedia('(prefers-color-scheme: dark)')
    const resize = () => chart.resize()
    scheme.addEventListener('change', render)
    window.addEventListener('resize', resize)
    return () => {
      scheme.removeEventListener('change', render)
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [history, currentId, metric, unit])

  return <div ref={ref} className="trend-chart" role="img" aria-label={`Evolución: ${metric}`} />
}
