import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSessionStore, SessionMetadata } from '@/store/sessionStore'

interface RenameSessionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  session: SessionMetadata
}

export function RenameSessionDialog({
  open,
  onOpenChange,
  session,
}: RenameSessionDialogProps) {
  const [name, setName] = useState(session.title)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const updateSession = useSessionStore((state) => state.updateSession)

  useEffect(() => {
    if (open) {
      setName(session.title)
    }
  }, [open, session.title])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!name.trim() || name.length > 100) return

    setIsSubmitting(true)
    try {
      // TODO: Implement API call when backend endpoint is ready
      // await apiClient.updateSessionMetadata(session.id, { display_name: name })
      
      // Update local store
      updateSession(session.id, { title: name })
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to rename session:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Rinomina sessione</DialogTitle>
          <DialogDescription>
            Scegli un nuovo nome per questa conversazione.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nome</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                disabled={isSubmitting}
              />
            </div>
          </div>
          <DialogFooter>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Annulla
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              {isSubmitting ? 'Salvataggio...' : 'Salva modifiche'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

