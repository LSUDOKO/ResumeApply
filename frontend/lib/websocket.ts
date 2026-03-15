type MessageHandler = (data: any) => void

class WebSocketManager {
    private ws: WebSocket | null = null
    private handlers: Map<string, MessageHandler[]> = new Map()
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null

    connect(sessionId: string) {
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

        this.ws = new WebSocket(`${wsUrl}/ws/${sessionId}`)

        this.ws.onopen = () => {
            console.log('WebSocket connected')
            this.emit('connected', {})
        }

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            this.emit(data.type, data)
            this.emit('*', data)
        }

        this.ws.onclose = () => {
            this.reconnectTimer = setTimeout(() => {
                this.connect(sessionId)
            }, 2000)
        }
    }

    on(event: string, handler: MessageHandler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, [])
        }
        this.handlers.get(event)!.push(handler)
        return () => this.off(event, handler)
    }

    off(event: string, handler: MessageHandler) {
        const handlers = this.handlers.get(event) || []
        this.handlers.set(event, handlers.filter(h => h !== handler))
    }

    emit(event: string, data: any) {
        const handlers = this.handlers.get(event) || []
        handlers.forEach(h => h(data))
    }

    send(data: object) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data))
        }
    }

    disconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
        this.ws?.close()
        this.ws = null
    }
}

export const wsManager = new WebSocketManager()
