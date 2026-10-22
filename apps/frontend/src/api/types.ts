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

export type ErrorCode = Schemas['ErrorOut']['code']
