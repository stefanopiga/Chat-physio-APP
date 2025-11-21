import { useEffect, useState } from 'react'
import { useSessionStore } from '../store/sessionStore'

export function useHydration() {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const unsubHydrate = useSessionStore.persist.onHydrate(() => 
      setHydrated(false)
    )
    const unsubFinish = useSessionStore.persist.onFinishHydration(() => 
      setHydrated(true)
    )

    setHydrated(useSessionStore.persist.hasHydrated())

    return () => {
      unsubHydrate()
      unsubFinish()
    }
  }, [])

  return hydrated
}

