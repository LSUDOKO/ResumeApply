'use client'
import { useState, useRef } from 'react'
import { useAgentStore } from '@/lib/store'
import { GeminiLiveClient } from '@/lib/geminiLive'

export function VoiceCommand() {
    const [isListening, setIsListening] = useState(false)
    const [transcript, setTranscript] = useState('')
    const clientRef = useRef<GeminiLiveClient | null>(null)
    const { setLastVoiceCommand, sessionId, preferences, setAgentStatus } = useAgentStore()

    const startListening = async () => {
        setIsListening(true)
        clientRef.current = new GeminiLiveClient({
            onTranscript: (text) => {
                setTranscript(text)
                setLastVoiceCommand(text)
            },
            onAgentSpeech: () => { }
        })

        const systemPrompt = "You are the voice interface for ResumeApply. Confirm job search commands."
        await clientRef.current.startVoiceSession(systemPrompt)
    }

    const stopListening = async () => {
        setIsListening(false)
        await clientRef.current?.stop()

        if (transcript) {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
            const response = await fetch(`${apiUrl}/api/agent/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    preferences,
                    voice_command: transcript
                })
            })
            if (response.ok) setAgentStatus('running')
        }
    }

    return (
        <div className="p-6 bg-neutral-dark rounded-lg border border-primary/20">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-widest text-primary">Voice Command</h3>
                <div className={`w-3 h-3 rounded-full ${isListening ? 'bg-red-500 animate-pulse' : 'bg-white/20'}`}></div>
            </div>

            <div className="h-12 flex items-center gap-1 mb-4">
                {isListening ? (
                    Array.from({ length: 12 }).map((_, i) => (
                        <div key={i} className="flex-1 bg-primary/40 animate-waveform" style={{ height: `${Math.random() * 100}%`, animationDelay: `${i * 0.05}s` }}></div>
                    ))
                ) : (
                    <div className="w-full h-px bg-white/10"></div>
                )}
            </div>

            <p className="text-sm font-mono text-white/50 mb-6 italic min-h-[1.5rem]">
                {transcript || 'Wait for command...'}
            </p>

            <button
                onMouseDown={startListening}
                onMouseUp={stopListening}
                className={`w-full py-4 font-black uppercase tracking-widest transition-all ${isListening ? 'bg-red-500 text-white scale-95' : 'bg-primary text-black hover:scale-105'}`}
            >
                {isListening ? 'RELEASE TO SEND' : 'HOLD TO COMMAND'}
            </button>
        </div>
    )
}
