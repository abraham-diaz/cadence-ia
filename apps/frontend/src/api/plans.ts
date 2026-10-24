import { request, send } from './client.ts'
import type { ChatMessage, Plan, PlanChatReply, PlanInput, PlanProposal, WeekProgress, WeekSummary } from './types.ts'

export const sendPlanChat = (messages: ChatMessage[]) =>
  send<PlanChatReply>('POST', '/api/plans/chat', { messages })

export const fetchWeekSummary = () => request<WeekSummary>('/api/plans/week-summary')

export const proposePlan = (messages: ChatMessage[]) =>
  send<PlanProposal>('POST', '/api/plans/proposal', { messages })

export const savePlan = (plan: PlanInput) => send<Plan>('POST', '/api/plans', plan)

export const fetchCurrentPlan = () => request<Plan | null>('/api/plans/current')

/** A week by any of its days ("2026-10-15"); without one, this week. */
export const fetchWeekProgress = (start?: string) =>
  request<WeekProgress>(`/api/plans/week-progress${start ? `?start=${start}` : ''}`)
