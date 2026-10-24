// Short names for the types generated from the backend (schema.d.ts).
// Never edit schema.d.ts by hand: run `npm run gen:api` after the API changes.
import type { components } from './schema.d.ts'

type Schemas = components['schemas']

export type Category = Schemas['WorkoutTypeIn']['category']
export type WorkoutTypeInput = Schemas['WorkoutTypeIn']
export type WorkoutTypeRef = Schemas['WorkoutTypeRef']
export type WorkoutType = Schemas['WorkoutTypeOut']

export type SessionSummary = Schemas['SessionSummary']
export type SessionDetail = Schemas['SessionDetail']
export type SessionStats = Schemas['SessionStats']
export type Segment = Schemas['SegmentOut']
export type HeartRatePoint = Schemas['HeartRatePoint']
export type HistoryPoint = Schemas['HistoryPoint']
export type Comparison = Schemas['Comparison']
export type Assessment = Schemas['AssessmentOut']

export type ChatMessage = Schemas['ChatMessageIn']
export type PlanChatReply = Schemas['PlanChatOut']
export type WeekSummary = Schemas['WeekSummaryOut']
export type PlanProposal = Schemas['PlanProposalOut']
export type ProposedDay = Schemas['ProposedDayOut']
export type PlanInput = Schemas['PlanIn']
export type PlanDayInput = Schemas['PlanDayIn']
export type Plan = Schemas['PlanOut']
export type PlanDay = Schemas['PlanDayOut']
export type Exercise = Schemas['ExerciseOut']
export type WeekProgress = Schemas['WeekProgressOut']
export type DayProgress = Schemas['DayProgressOut']
export type PlannedWorkout = Schemas['PlannedWorkoutOut']
export type DayStatus = DayProgress['status']

export type ErrorCode = Schemas['ErrorOut']['code']
