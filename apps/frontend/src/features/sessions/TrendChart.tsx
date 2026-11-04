import type { HistoryPoint, SessionStats } from '../../api/types.ts'
import { formatShortDate } from '../../shared/format.ts'
import { themeColors, useChart, type ChartOption } from './echarts.ts'

interface Props {
  history: HistoryPoint[]
  currentId: string
  metric: keyof SessionStats
  title: string
  unit: string
}

function buildOption({ history, currentId, metric, unit }: Props): ChartOption {
  const c = themeColors()
  return {
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
        lineStyle: { width: 2, color: c.accent },
        itemStyle: { color: c.accent, borderColor: c.surface, borderWidth: 2 },
        symbolSize: 8,
        data: history.map((h) => ({
          value: h[metric],
          // Bigger dot for the session being viewed.
          ...(h.id === currentId ? { symbolSize: 14 } : {}),
        })),
      },
    ],
  }
}

/** One metric across the sessions of a workout type; the open session is highlighted. */
export default function TrendChart(props: Props) {
  const { history, currentId, metric, title, unit } = props
  const ref = useChart(() => buildOption(props), [history, currentId, metric, unit])
  return <div ref={ref} className="trend-chart" role="img" aria-label={`Evolución: ${title}`} />
}
