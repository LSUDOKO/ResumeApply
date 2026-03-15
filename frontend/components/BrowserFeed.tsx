'use client'
import { useEffect, useState } from 'react'
import { wsManager } from '@/lib/websocket'
import { useAgentStore } from '@/lib/store'

export function BrowserFeed() {
    const {
        currentScreenshot, setCurrentScreenshot,
        currentUrl, setCurrentUrl,
        setAgentThinking, addApplication,
        incrementApplied, incrementSkipped
    } = useAgentStore()

    const [scanLineY, setScanLineY] = useState(0)

    useEffect(() => {
        const interval = setInterval(() => {
            setScanLineY(prev => prev >= 100 ? 0 : prev + 0.5)
        }, 30)

        const unsubScreenshot = wsManager.on('screenshot', (data) => {
            setCurrentScreenshot(data.data)
            setCurrentUrl(data.url)
            setAgentThinking(data.context)
        })

        wsManager.on('job_applied', (data) => {
            addApplication({
                job_title: data.job_title,
                company: data.company,
                status: 'applied',
                match_score: data.match_score,
                cover_letter: data.cover_letter,
                timestamp: new Date().toISOString()
            })
            incrementApplied()
        })

        wsManager.on('job_skipped', (data) => {
            addApplication({
                job_title: data.job_title,
                company: data.company,
                status: 'skipped',
                match_score: data.match_score,
                reason: data.reason,
                timestamp: new Date().toISOString()
            })
            incrementSkipped()
        })

        return () => clearInterval(interval)
    }, [])

    return (
        <div className="flex-1 bg-neutral-dark rounded-lg border border-primary/20 overflow-hidden relative flex flex-col">
            <div className="p-3 border-b border-white/5 flex items-center gap-2 bg-black/40">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50"></div>
                </div>
                <div className="ml-2 bg-black/40 px-3 py-1 rounded text-[10px] font-mono text-primary/60 truncate flex-1 border border-white/5 italic">
                    {currentUrl || 'Waiting for browser...'}
                </div>
            </div>

            <div className="flex-1 relative bg-black flex items-center justify-center overflow-hidden">
                {currentScreenshot ? (
                    <img
                        src={`data:image/jpeg;base64,${currentScreenshot}`}
                        alt="Agent browser view"
                        className="w-full h-full object-contain opacity-90 grayscale-[0.2]"
                    />
                ) : (
                    <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.5em] animate-pulse">
                        Connection Idle
                    </div>
                )}

                <div
                    className="absolute inset-x-0 h-px bg-primary/40 shadow-[0_0_10px_#C8FF00]"
                    style={{ top: `${scanLineY}%` }}
                />
            </div>
        </div>
    )
}
