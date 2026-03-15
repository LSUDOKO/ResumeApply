'use client'
import { useAgentStore } from '@/lib/store'

export function StatsBar() {
    const { totalApplied, totalSkipped, elapsedSeconds } = useAgentStore()

    const formatTime = (sec: number) => {
        const min = Math.floor(sec / 60)
        const s = sec % 60
        return `${min}:${s.toString().padStart(2, '0')}`
    }

    return (
        <div className="h-16 bg-background-dark border-t border-primary/20 px-8 flex items-center justify-between">
            <div className="flex gap-12">
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">APPLIED</span>
                    <span className="text-2xl font-black text-primary font-bebas">{totalApplied.toString().padStart(2, '0')}</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">SKIPPED</span>
                    <span className="text-2xl font-black text-white font-bebas">{totalSkipped.toString().padStart(2, '0')}</span>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm text-primary animate-spin-slow">history</span>
                    <span className="text-xl font-mono text-white font-bold">{formatTime(elapsedSeconds)}</span>
                </div>
                <div className="w-px h-6 bg-white/10 mx-2"></div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></div>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">LIVE FEED ACTIVE</span>
                </div>
            </div>
        </div>
    )
}
