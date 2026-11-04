import type { ChatMessage } from '../../api/types.ts'
import { loadJson, saveJson } from '../../shared/storage.ts'

const KEY = 'cadence:plan-chat'

export const loadChat = () => loadJson<ChatMessage[]>(KEY, [], Array.isArray)

export const saveChat = (messages: ChatMessage[]) => saveJson(KEY, messages.length ? messages : null)
