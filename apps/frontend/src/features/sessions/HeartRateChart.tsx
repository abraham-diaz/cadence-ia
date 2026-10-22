import { LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  MarkAreaComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import type { HeartRatePoint, Segment } from '../../api/types.ts'
import { formatClock } from '../../shared/format.ts'

// Only register the pieces we use, to keep the bundle small.
echarts.use([LineChart, GridComponent, TooltipComponent, MarkAreaComponent, DataZoomComponent, CanvasRenderer])

interface Props {
  points: HeartRatePoint[]
  segments: Segment[]
}

/** Read the theme colors defined as CSS variables in index.css. */
function themeColors() {
  const css = getComputedStyle(document.documentElement)
  const get = (name: string) => css.getPropertyValue(name).trim()
  return {
    line: get('--hr'),
    band: get('--hr-band'),
    text: get('--text-secondary'),
    grid: get('--grid'),
    surface: get('--surface'),
    ink: get('--text-primary'),
  }
}

function buildOption(points: HeartRatePoint[], segments: Segment[]): echarts.EChartsCoreOption {
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
        lineStyle: { width: 2, color: c.line },
        itemStyle: { color: c.line },
        markArea: {
          silent: true,
          itemStyle: { color: c.band },
          data: segments
            .filter((s) => s.kind === 'work')
            .map((s) => [{ xAxis: s.start_s }, { xAxis: s.end_s }]),
        },
      },
    ],
  }
}

export default function HeartRateChart({ points, segments }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    const render = () => chart.setOption(buildOption(points, segments), true)
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
  }, [points, segments])

  return (
    <div
      ref={ref}
      className="hr-chart"
      role="img"
      aria-label="Curva de frecuencia cardiaca con las series sombreadas"
    />
  )
}
