import { useState, useEffect } from 'react'
import { Plus, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useSessionStore, SessionMetadata } from '@/store/sessionStore'
import { SessionListItem } from './SessionListItem'
import { useHydration } from '@/hooks/useHydration'
import apiClient from '@/lib/apiClient'

interface ChatSidebarProps {
  currentSessionId: string | null
  onSessionSelect: (sessionId: string) => void
  onNewChat: () => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function ChatSidebar({ 
  currentSessionId, 
  onSessionSelect, 
  onNewChat,
  open: controlledOpen,
  onOpenChange: setControlledOpen
}: ChatSidebarProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  
  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : internalOpen
  const setOpen = isControlled ? setControlledOpen : setInternalOpen

  const hydrated = useHydration()
  const sessions = useSessionStore((state) => state.sessions)
  const setSessions = useSessionStore((state) => state.setSessions)
  
  // Sync sessions on mount
  useEffect(() => {
    // In a real app, fetch from API. 
    // For now, we rely on local storage persistence, 
    // but we should probably fetch list from backend if we implemented that endpoint.
    // Since we don't have a GET /sessions endpoint in the story, 
    // we rely on what's in the store or what we build up.
    
    // If we had GET /sessions:
    /*
    apiClient.getSessions().then(setSessions).catch(console.error)
    */
  }, [])

  const sortedSessions = [...sessions].sort((a, b) => 
    new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )

  const handleSessionSelect = (sessionId: string) => {
    onSessionSelect(sessionId)
    setOpen?.(false) // Auto-close on mobile
  }

  const handleNewChat = () => {
    onNewChat()
    setOpen?.(false)
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="p-4 border-b">
        <Button 
          onClick={handleNewChat} 
          className="w-full justify-start gap-2" 
          variant="secondary"
        >
          <Plus className="h-4 w-4" />
          Nuova Chat
        </Button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {!hydrated ? (
          <div className="p-4 text-center text-muted-foreground text-sm">
            Caricamento...
          </div>
        ) : sortedSessions.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground text-sm">
            Nessuna conversazione recente
          </div>
        ) : (
          <div className="space-y-1">
            {sortedSessions.map((session) => (
              <SessionListItem
                key={session.id}
                session={session}
                isActive={session.id === currentSessionId}
                onSelect={handleSessionSelect}
              />
            ))}
          </div>
        )}
      </div>

      <div className="p-4 border-t text-xs text-center text-muted-foreground">
        Fisio RAG v1.0
      </div>
    </div>
  )

  return (
    <>
      {/* Mobile: Sheet overlay */}
      <Sheet open={open} onOpenChange={setOpen}>
        {/* Trigger is now handled externally if controlled, or via this if not */}
        {!isControlled && (
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden shrink-0">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Menu</span>
            </Button>
          </SheetTrigger>
        )}
        
        <SheetContent 
          side="left" 
          className="w-[300px] sm:w-[350px] p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Sessioni Chat</SheetTitle>
          </SheetHeader>
          {sidebarContent}
        </SheetContent>
      </Sheet>

      {/* Desktop: Fixed aside */}
      <aside className="hidden lg:flex w-[300px] border-r flex-col fixed inset-y-0 z-20">
        {sidebarContent}
      </aside>
    </>
  )
}

