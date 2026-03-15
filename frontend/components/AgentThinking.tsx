'use client'
import { useEffect, useRef, useState } from 'react'
import { wsManager } from '@/lib/websocket'

export function AgentThinking() {
    const [lines, setLines] = useState<string[]>([])
    const [currentLine, setCurrentLine] = useState('')
    const containerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const unsubThinking = wsManager.on('agent_thinking', (data) => {
            typewriterEffect(data.text)
        })

        wsManager.on('job_applied', (data) => {
            setLines(prev => [...prev, `✓ ${data.company} · ${data.job_title} · APPLIED`])
        })

        wsManager.on('job_skipped', (data) => {
            setLines(prev => [...prev, `✗ ${data.company} · SKIPPED · ${data.reason}`])
        })

        return () => unsubThinking()
    }, [])

    const typewriterEffect = (text: string) => {
        let i = 0
        setCurrentLine('')
        const interval = setInterval(() => {
            if (i < text.length) {
                setCurrentLine(prev => prev + text[i])
                i++
                if (containerRef.current) containerRef.current.scrollTop = containerRef.current.scrollHeight
            } else {
                clearInterval(interval)
                setLines(prev => [...prev, text])
                setCurrentLine('')
            }
        }, 25)
    }

    return (
        <div className="flex-1 bg-neutral-dark border border-primary/20 p-4 rounded-lg flex flex-col gap-3 min-h-[150px] overflow-hidden font-mono text-xs">
            <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-primary text-sm animate-pulse">psychology</span>
                <span className="font-bold text-primary tracking-widest uppercase">Agent Reasoning</span>
            </div>

            <div ref={containerRef} className="flex-1 overflow-y-auto space-y-1 custom-scrollbar">
                {lines.slice(-10).map((line, i) => (
                    <div key={i} className={`flex gap-3 ${line.startsWith('✓') ? 'text-green-400' : line.startsWith('✗') ? 'text-red-400' : 'text-white/40'}`}>
                        <span className="opacity-30">14:02:{11 + i}</span>
                        <span>{line}</span>
                    </div>
                ))}
                {currentLine && (
                    <div className="flex gap-3 text-primary">
                        <span className="opacity-30">14:02:XX</span>
                        <span className="flex border-r-2 border-primary animate-pulse">{currentLine}</span>
                    </div>
                )}
            </div>
        </div>
    )
}
