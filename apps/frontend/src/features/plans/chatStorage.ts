import type { ChatMessage } from '../../api/types.ts'

// iOS kills home-screen apps in the background: without this the chat would be lost.
const KEY = 'cadence:plan-chat'

export function loadChat(): ChatMessage[] {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

export function saveChat(messages: ChatMessage[]) {
  try {
    if (messages.length) localStorage.setItem(KEY, JSON.stringify(messages))
    else localStorage.removeItem(KEY)
  } catch {
    // Private mode or storage full: the chat still works, it just won't survive a reload.
  }
}
