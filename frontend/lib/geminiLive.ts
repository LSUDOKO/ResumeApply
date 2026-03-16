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

        this.pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        })

        // ── 1. Track handling ──
        this.mediaStream.getTracks().forEach(track => {
            this.pc!.addTrack(track, this.mediaStream!)
        })

        this.pc.ontrack = (event) => {
            const audio = new Audio()
            audio.srcObject = event.streams[0]
            audio.play()
        }

        // ── 2. Create Offer ──
        const offer = await this.pc.createOffer()
        await this.pc.setLocalDescription(offer)

        // ── 3. Handshake ──
        const response = await fetch('/api/voice/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                system_prompt: systemPrompt,
                offer: { sdp: offer.sdp, type: offer.type }
            })
        })

        const { answer, session_id } = await response.json()
        await this.pc.setRemoteDescription(new RTCSessionDescription(answer))

        // ── 4. ICE Trickle ──
        this.pc.onicecandidate = (event) => {
            if (event.candidate) {
                fetch(`/api/voice/session/${session_id}/ice`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(event.candidate.toJSON())
                }).catch(err => console.error("ICE trickle failed", err))
            }
        }
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
