import { MoreVertical, Pencil, Trash2, MessageSquare } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SessionMetadata } from '@/store/sessionStore'
import { RenameSessionDialog } from './RenameSessionDialog'
import { DeleteSessionDialog } from './DeleteSessionDialog'
import { cn } from '@/lib/utils'

interface SessionListItemProps {
  session: SessionMetadata
  isActive: boolean
  onSelect: (id: string) => void
}

export function SessionListItem({ session, isActive, onSelect }: SessionListItemProps) {
  const [showRename, setShowRename] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  return (
    <div className="relative group">
      {/* Session item - click carica sessione */}
      <button
        onClick={() => onSelect(session.id)}
        className={cn(
          "w-full p-3 text-left rounded-lg transition-colors group/item flex items-start gap-3",
          isActive 
            ? "bg-accent text-accent-foreground" 
            : "hover:bg-accent/50 text-foreground"
        )}
      >
        <MessageSquare className="h-4 w-4 mt-1 opacity-70 shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="font-medium truncate pr-6 text-sm">{session.title || "Nuova chat"}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
            <span>{new Date(session.createdAt).toLocaleDateString()}</span>
            <span>•</span>
            <span>{session.messageCount} messaggi</span>
          </div>
        </div>
      </button>

      {/* Actions menu - click non propaga */}
      <div 
        className={cn(
          "absolute right-2 top-2.5 transition-opacity",
          isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        )}
        onClick={(e) => e.stopPropagation()} // CRITICO: previeni parent click
      >
        <DropdownMenu modal={false}> {/* CRITICO: permetti Dialog nesting */}
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
            >
              <MoreVertical className="h-4 w-4" />
              <span className="sr-only">Menu opzioni</span>
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setShowRename(true)}>
              <Pencil className="mr-2 h-4 w-4" />
              Rinomina
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => setShowDelete(true)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Elimina
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Dialogs */}
      <RenameSessionDialog 
        open={showRename} 
        onOpenChange={setShowRename}
        session={session}
      />
      <DeleteSessionDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        sessionId={session.id}
        sessionTitle={session.title}
      />
    </div>
  )
}

