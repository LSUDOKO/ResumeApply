"use client";

import { useEffect } from "react";
import { useAgentStore } from "@/lib/store";
import { wsManager } from "@/lib/websocket";
import { BrowserFeed } from "@/components/BrowserFeed";
import { AgentThinking } from "@/components/AgentThinking";
import { VoiceCommand } from "@/components/VoiceCommand";
import { StatsBar } from "@/components/StatsBar";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
    const {
        sessionId, agentStatus, setAgentStatus,
        totalApplied, totalSkipped, setElapsed
    } = useAgentStore();
    const router = useRouter();

    useEffect(() => {
        if (!sessionId) {
            router.push('/upload');
            return;
        }

        // Listen for completion to auto-navigate
        const unsubComplete = wsManager.on('agent_complete', () => {
            setAgentStatus('complete');
            setTimeout(() => router.push('/tracker'), 3000);
        });

        // Elapsed time counter
        let seconds = 0;
        const timer = setInterval(() => {
            seconds++;
            setElapsed(seconds);
        }, 1000);

        return () => {
            unsubComplete();
            clearInterval(timer);
        };
    }, [sessionId]);

    const handleStop = async () => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        await fetch(`${apiUrl}/api/agent/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        router.push('/tracker');
    };

    return (
        <div className="bg-background-dark min-h-screen pt-24 flex flex-col overflow-hidden text-slate-100 selection:bg-primary selection:text-black">
            <main className="flex-1 flex overflow-hidden">
                {/* Left: Agent's View (Browser Stream) */}
                <section className="w-[55%] p-6 flex flex-col gap-6 border-r border-primary/10 bg-black/20">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-bold tracking-[0.2em] uppercase text-slate-400">Agent's View — Live</h2>
                        <div className="text-[10px] font-mono text-primary/60 uppercase tracking-tighter">Session ID: {sessionId?.slice(0, 8)}...</div>
                    </div>

                    <BrowserFeed />

                    <div className="flex gap-4">
                        <button
                            onClick={handleStop}
                            className="flex-1 py-4 bg-primary text-background-dark font-black uppercase tracking-widest text-lg hover:brightness-110 transition-all shadow-[4px_4px_0px_rgba(255,255,255,0.2)]"
                        >
                            STOP AGENT
                        </button>
                        <button className="flex-1 py-4 border-2 border-white/10 text-white/40 font-black uppercase tracking-widest text-lg hover:border-primary/40 hover:text-white transition-all">
                            PAUSE SESSION
                        </button>
                    </div>
                </section>

                {/* Right: Agent Brain & Stats */}
                <section className="w-[45%] p-6 flex flex-col gap-6 bg-black/40">
                    <h2 className="text-sm font-bold tracking-[0.2em] uppercase text-slate-400">Agent Control & Reason</h2>

                    <VoiceCommand />

                    <AgentThinking />

                    <div className="flex-1 flex flex-col">
                        <h3 className="text-[10px] font-bold uppercase text-slate-500 mb-3 tracking-widest flex justify-between">
                            <span>Quick Actions</span>
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-white/5 border border-white/10 rounded group hover:border-primary transition-colors cursor-pointer">
                                <p className="text-[10px] font-bold text-slate-500 mb-1">FORCE REFRESH</p>
                                <p className="text-xs font-mono text-primary">RE-SYNC FEED</p>
                            </div>
                            <div className="p-4 bg-white/5 border border-white/10 rounded group hover:border-primary transition-colors cursor-pointer">
                                <p className="text-[10px] font-bold text-slate-500 mb-1">AGENT LOGS</p>
                                <p className="text-xs font-mono text-primary">VIEW RAW</p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <StatsBar />
        </div>
    );
}
