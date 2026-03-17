export class GeminiLiveClient {
    private ws: WebSocket | null = null
    private audioContext: AudioContext | null = null
    private processor: ScriptProcessorNode | null = null
    private mediaStream: MediaStream | null = null
    private onTranscript: (text: string) => void
    private onAgentSpeech: (audioBlob: Blob) => void

    constructor(callbacks: {
        onTranscript: (text: string) => void
        onAgentSpeech: (audioBlob: Blob) => void
    }) {
        this.onTranscript = callbacks.onTranscript
        this.onAgentSpeech = callbacks.onAgentSpeech
    }

    async startVoiceSession(systemPrompt: string) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || window.location.host
        const sessionId = Math.random().toString(36).substring(7)
        
        this.ws = new WebSocket(`${protocol}//${host}/api/ws/voice/${sessionId}`)
        this.ws.binaryType = 'arraybuffer'

        this.ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                const data = JSON.parse(event.data)
                if (data.type === 'transcript') {
                    this.onTranscript(data.text)
                }
            } else {
                // Audio response from agent (MP3 or PCM)
                const audioBlob = new Blob([event.data], { type: 'audio/mp3' })
                this.onAgentSpeech(audioBlob)
            }
        }

        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        this.audioContext = new AudioContext({ sampleRate: 16000 })
        const source = this.audioContext.createMediaStreamSource(this.mediaStream)
        
        // Use ScriptProcessor for simple PCM16 chunking
        this.processor = this.audioContext.createScriptProcessor(4096, 1, 1)
        source.connect(this.processor)
        this.processor.connect(this.audioContext.destination)

        this.processor.onaudioprocess = (e) => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                const inputData = e.inputBuffer.getChannelData(0)
                const pcm16 = this.floatTo16BitPCM(inputData)
                this.ws.send(pcm16)
            }
        }
    }

    private floatTo16BitPCM(float32Array: Float32Array): ArrayBuffer {
        const buffer = new ArrayBuffer(float32Array.length * 2)
        const view = new DataView(buffer)
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]))
            view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
        }
        return buffer
    }

    sendTextToAgent(text: string) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'user_text', text }))
        }
    }

    async stop() {
        this.mediaStream?.getTracks().forEach(t => t.stop())
        this.processor?.disconnect()
        this.audioContext?.close()
        this.ws?.close()
    }
}
