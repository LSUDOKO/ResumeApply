export class GeminiLiveClient {
    private pc: RTCPeerConnection | null = null
    private dc: RTCDataChannel | null = null
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
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000
            }
        })

        const response = await fetch('/api/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ system_prompt: systemPrompt })
        })

        const { offer, sessionId } = await response.json()

        this.pc = new RTCPeerConnection()

        this.mediaStream.getTracks().forEach(track => {
            this.pc!.addTrack(track, this.mediaStream!)
        })

        this.dc = this.pc.createDataChannel('events')
        this.dc.onmessage = (event) => {
            const data = JSON.parse(event.data)
            if (data.type === 'transcript') {
                this.onTranscript(data.text)
            }
        }

        this.pc.ontrack = (event) => {
            const audio = new Audio()
            audio.srcObject = event.streams[0]
            audio.play()
        }

        await this.pc.setRemoteDescription(offer)
        const answer = await this.pc.createAnswer()
        await this.pc.setLocalDescription(answer)

        await fetch(`/api/session/${sessionId}/answer`, {
            method: 'POST',
            body: JSON.stringify({ answer })
        })
    }

    sendTextToAgent(text: string) {
        if (this.dc?.readyState === 'open') {
            this.dc.send(JSON.stringify({ type: 'user_text', text }))
        }
    }

    async stop() {
        this.mediaStream?.getTracks().forEach(t => t.stop())
        this.dc?.close()
        this.pc?.close()
    }
}
