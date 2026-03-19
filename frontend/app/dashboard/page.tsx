"use client";

import { useEffect, useState } from "react";
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
        totalApplied, totalSkipped, setElapsed,
        agentLogs, addLog, setSessionStartTime,
        addApplication, incrementApplied, incrementSkipped
    } = useAgentStore();
    const router = useRouter();

    const [isPaused, setIsPaused] = useState(false);
    const [interventionMsg, setInterventionMsg] = useState<string | null>(null);
    const [interventionInput, setInterventionInput] = useState("");
    const [showLogs, setShowLogs] = useState(false);

    useEffect(() => {
        if (!sessionId) {
            router.push('/upload');
            return;
        }

        wsManager.connect(sessionId);

        const unsubComplete = wsManager.on('agent_complete', () => {
            setAgentStatus('complete');
            setTimeout(() => router.push('/tracker'), 3000);
        });

        const unsubApplied = wsManager.on('job_applied', (data: any) => {
            addApplication(data);
            incrementApplied();
        });

        const unsubSkipped = wsManager.on('job_skipped', (data: any) => {
            addApplication(data);
            incrementSkipped();
        });

        // CAPTCHA / intervention pause
        const unsubPaused = wsManager.on('agent_paused', (data: any) => {
            setIsPaused(true);
            setAgentStatus('paused');
            setInterventionMsg(data.message || 'Agent needs your attention.');
            setInterventionInput("");
        });

        // Log every WS event
        const unsubAll = wsManager.on('*', (data: any) => {
            const ts = new Date().toLocaleTimeString();
            addLog(`[${ts}] ${data.type}: ${data.message || data.context || data.error || data.text || ''}`);
        });

        // Elapsed time counter
        setSessionStartTime(Date.now());
        let seconds = 0;
        const timer = setInterval(() => {
            seconds++;
            setElapsed(seconds);
        }, 1000);

        return () => {
            unsubComplete();
            unsubApplied();
            unsubSkipped();
            unsubPaused();
            unsubAll();
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

    const handlePause = async () => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        if (isPaused) {
            await fetch(`${apiUrl}/api/agent/resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
            wsManager.send({ type: 'resume', session_id: sessionId });
            setIsPaused(false);
            setAgentStatus('running');
        } else {
            await fetch(`${apiUrl}/api/agent/pause`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message: 'Paused by user.' })
            });
            wsManager.send({ type: 'pause', session_id: sessionId });
            setIsPaused(true);
            setAgentStatus('paused');
        }
    };

    const handleInterventionDone = () => {
        wsManager.send({
            type: 'intervention_response',
            status: 'resolved',
            session_id: sessionId,
            value: interventionInput  // sends password / answer back to agent
        });
        setInterventionMsg(null);
        setInterventionInput("");
        setIsPaused(false);
        setAgentStatus('running');
    };

    const handleForceRefresh = () => {
        // Re-request latest screenshot by asking agent status
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        fetch(`${apiUrl}/api/agent/status/${sessionId}`)
            .then(r => r.json())
            .then(d => addLog(`[REFRESH] Agent running: ${d.running}`));
        // Also re-sync results
        wsManager.send({ type: 'ping', session_id: sessionId });
    };

    return (
        <div className="bg-background-dark min-h-screen pt-24 flex flex-col overflow-hidden text-slate-100 selection:bg-primary selection:text-black">

            {/* CAPTCHA / Intervention Overlay */}
            {interventionMsg && (
                <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center">
                    <div className="bg-background-dark border-4 border-primary p-10 max-w-lg w-full mx-4 shadow-[8px_8px_0px_rgba(255,255,255,0.1)]">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-primary mb-3">Agent Needs You</p>
                        <h2 className="text-2xl font-black uppercase text-white mb-4">{interventionMsg}</h2>
                        <p className="text-slate-400 text-sm mb-4">
                            Resolve the issue in the browser feed on the left, or type your response below, then click Done.
                        </p>
                        <input
                            type="text"
                            value={interventionInput}
                            onChange={e => setInterventionInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleInterventionDone()}
                            placeholder="Type password or answer (if needed)..."
                            className="w-full bg-black border-2 border-white/20 text-white px-4 py-3 mb-6 text-sm font-mono focus:outline-none focus:border-primary placeholder:text-white/30"
                        />
                        <button
                            onClick={handleInterventionDone}
                            className="w-full py-4 bg-primary text-black font-black uppercase tracking-widest text-lg hover:brightness-110 transition-all"
                        >
                            DONE — RESUME AGENT
                        </button>
                    </div>
                </div>
            )}

            {/* Agent Logs Modal */}
            {showLogs && (
                <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center" onClick={() => setShowLogs(false)}>
                    <div className="bg-background-dark border-4 border-primary p-6 max-w-2xl w-full mx-4 max-h-[70vh] flex flex-col" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center mb-4">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-primary">Agent Logs</p>
                            <button onClick={() => setShowLogs(false)} className="text-white/40 hover:text-white text-xl font-bold">✕</button>
                        </div>
                        <div className="overflow-y-auto flex-1 font-mono text-xs text-slate-300 space-y-1">
                            {agentLogs.length === 0
                                ? <p className="text-white/30 italic">No logs yet.</p>
                                : agentLogs.map((log, i) => <p key={i} className="border-b border-white/5 pb-1">{log}</p>)
                            }
                        </div>
                    </div>
                </div>
            )}

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
                        <button
                            onClick={handlePause}
                            className={`flex-1 py-4 border-2 font-black uppercase tracking-widest text-lg transition-all ${isPaused
                                    ? 'border-primary text-primary hover:bg-primary hover:text-black'
                                    : 'border-white/10 text-white/40 hover:border-primary/40 hover:text-white'
                                }`}
                        >
                            {isPaused ? 'RESUME SESSION' : 'PAUSE SESSION'}
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
                            <div
                                onClick={handleForceRefresh}
                                className="p-4 bg-white/5 border border-white/10 rounded group hover:border-primary transition-colors cursor-pointer"
                            >
                                <p className="text-[10px] font-bold text-slate-500 mb-1">FORCE REFRESH</p>
                                <p className="text-xs font-mono text-primary">RE-SYNC FEED</p>
                            </div>
                            <div
                                onClick={() => setShowLogs(true)}
                                className="p-4 bg-white/5 border border-white/10 rounded group hover:border-primary transition-colors cursor-pointer"
                            >
                                <p className="text-[10px] font-bold text-slate-500 mb-1">AGENT LOGS</p>
                                <p className="text-xs font-mono text-primary">VIEW RAW ({agentLogs.length})</p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <StatsBar />
        </div>
    );
}
