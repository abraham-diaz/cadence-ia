import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef, type DependencyList } from 'react'

// Only register the pieces we use, to keep the bundle small. Each chart adds its own extras.
echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

export { echarts }

export type ChartOption = echarts.EChartsCoreOption

/** Theme colors, defined as CSS variables in styles/tokens.css. */
export function themeColors() {
  const css = getComputedStyle(document.documentElement)
  const get = (name: string) => css.getPropertyValue(name).trim()
  return {
    hr: get('--hr'),
    hrBand: get('--hr-band'),
    accent: get('--accent'),
    text: get('--text-secondary'),
    grid: get('--grid'),
    surface: get('--surface'),
    ink: get('--text-primary'),
  }
}

/** A chart in the returned ref's element, built again when `deps` or the light/dark scheme change. */
export function useChart(build: () => ChartOption, deps: DependencyList) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    const render = () => chart.setOption(build(), true)
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}
