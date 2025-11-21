import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface SessionMetadata {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
}

interface SessionState {
  sessions: SessionMetadata[]
  currentSessionId: string | null
  
  // Actions
  setSessions: (sessions: SessionMetadata[]) => void
  addSession: (session: SessionMetadata) => void
  updateSession: (id: string, updates: Partial<SessionMetadata>) => void
  deleteSession: (id: string) => void
  setCurrentSession: (id: string | null) => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      sessions: [],
      currentSessionId: null,
      
      setSessions: (sessions) => set({ sessions }),
      
      addSession: (session) => 
        set((state) => ({ 
          sessions: [session, ...state.sessions] 
        })),
      
      updateSession: (id, updates) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        })),
      
      deleteSession: (id) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          currentSessionId: 
            state.currentSessionId === id ? null : state.currentSessionId,
        })),
      
      setCurrentSession: (id) => set({ currentSessionId: id }),
    }),
    {
      name: 'chat.sessions', // localStorage key
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
)

