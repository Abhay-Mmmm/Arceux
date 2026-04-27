import { useState, useEffect, useRef } from 'react'
import { arceuxWS } from '../services/websocket'

export function useWebSocket<T>(
    eventType: string,
    onMessage?: (data: T) => void
): { lastMessage: T | null; connected: boolean } {
    const [lastMessage, setLastMessage] = useState<T | null>(null)
    const [connected, setConnected] = useState(arceuxWS.connected)
    const onMessageRef = useRef(onMessage)

    useEffect(() => { onMessageRef.current = onMessage })

    useEffect(() => {
        arceuxWS.connect()
        const unsubEvent = arceuxWS.on(eventType, (data: T) => {
            setLastMessage(data)
            onMessageRef.current?.(data)
        })
        const unsubConnect = arceuxWS.on('__connected', () => setConnected(true))
        const unsubDisconnect = arceuxWS.on('__disconnected', () => setConnected(false))
        return () => { unsubEvent(); unsubConnect(); unsubDisconnect() }
    }, [eventType])

    return { lastMessage, connected }
}
