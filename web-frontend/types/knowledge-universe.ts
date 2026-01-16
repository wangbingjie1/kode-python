export interface Card {
  id: string
  title: string
  type: string
  badge: string
  row: number
  col: number
  stats: Record<string, string>
}

export interface Connection {
  from: string
  to: string
}

export interface Message {
  role: "user" | "assistant"
  content: string
  time: string
}
