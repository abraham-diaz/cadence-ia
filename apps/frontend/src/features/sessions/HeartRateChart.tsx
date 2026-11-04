import { DataZoomComponent, MarkAreaComponent } from 'echarts/components'
import type { HeartRatePoint, Segment } from '../../api/types.ts'
import { formatClock } from '../../shared/format.ts'
import { echarts, themeColors, useChart, type ChartOption } from './echarts.ts'

echarts.use([MarkAreaComponent, DataZoomComponent])

interface Props {
  points: HeartRatePoint[]
  segments: Segment[]
}

function buildOption(points: HeartRatePoint[], segments: Segment[]): ChartOption {
  const c = themeColors()
  const hrs = points.map((p) => p.hr)

  return {
    animation: false,
    grid: { left: 36, right: 8, top: 12, bottom: 28 },
    xAxis: {
      type: 'value',
      min: 0,
      max: points.at(-1)?.t ?? 0,
      axisLabel: { color: c.text, formatter: (v: number) => formatClock(v), hideOverlap: true },
      axisLine: { lineStyle: { color: c.grid } },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: Math.floor((Math.min(...hrs) - 5) / 20) * 20,
      max: Math.ceil((Math.max(...hrs) + 5) / 20) * 20,
      interval: 20,
      axisLabel: { color: c.text },
      splitLine: { lineStyle: { color: c.grid } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: c.surface,
      borderColor: c.grid,
      textStyle: { color: c.ink },
      axisPointer: { type: 'line', lineStyle: { color: c.text } },
      formatter: (params: { value: [number, number] }[]) => {
        const [t, hr] = params[0].value
        return `${formatClock(t)} · <b>${hr}</b> ppm`
      },
    },
    dataZoom: [{ type: 'inside', filterMode: 'none' }],
    series: [
      {
        type: 'line',
        data: points.map((p) => [p.t, p.hr]),
        showSymbol: false,
        lineStyle: { width: 2, color: c.hr },
        itemStyle: { color: c.hr },
        markArea: {
          silent: true,
          itemStyle: { color: c.hrBand },
          data: segments.filter((s) => s.kind === 'work').map((s) => [{ xAxis: s.start_s }, { xAxis: s.end_s }]),
        },
      },
    ],
  }
}

export default function HeartRateChart({ points, segments }: Props) {
  const ref = useChart(() => buildOption(points, segments), [points, segments])
  return (
    <div
      ref={ref}
      className="hr-chart"
      role="img"
      aria-label="Curva de frecuencia cardiaca con las series sombreadas"
    />
  )
}
