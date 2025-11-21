import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useSessionStore } from '@/store/sessionStore'
import apiClient from '@/lib/apiClient'

// Simple toast implementation since we don't have sonner installed yet in the snippet provided
// If sonner or similar is available, replace this with actual toast call
const toast = {
  success: (msg: string) => console.log('Toast Success:', msg),
  error: (msg: string) => console.error('Toast Error:', msg)
}

interface DeleteSessionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  sessionTitle: string
}

export function DeleteSessionDialog({
  open,
  onOpenChange,
  sessionId,
  sessionTitle,
}: DeleteSessionDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const deleteSession = useSessionStore((state) => state.deleteSession)

  const handleDelete = async () => {
    setIsDeleting(true)
    
    try {
      // API call
      await apiClient.deleteSession(sessionId)
      
      // Update store
      deleteSession(sessionId)
      
      toast.success('Sessione eliminata con successo')
      onOpenChange(false)
      
    } catch (error) {
      console.error("Delete session error:", error)
      toast.error('Errore durante eliminazione sessione')
      // Non chiudere dialog su errore per permettere retry
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Conferma eliminazione</AlertDialogTitle>
          <AlertDialogDescription>
            Sei sicuro di voler eliminare la sessione "{sessionTitle}"? 
            Questa azione è irreversibile e cancellerà tutti i messaggi associati.
          </AlertDialogDescription>
        </AlertDialogHeader>
        
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Annulla
          </AlertDialogCancel>
          
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={(e) => {
              e.preventDefault() // Previeni auto-close
              handleDelete()
            }}
            disabled={isDeleting}
          >
            {isDeleting ? 'Eliminazione...' : 'Elimina'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

