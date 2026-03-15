"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAgentStore } from "@/lib/store";
import { wsManager } from "@/lib/websocket";
import Link from "next/link";

export default function PreferencesPage() {
    const router = useRouter();
    const { setPreferences, sessionId } = useAgentStore();
    const [prefs, setLocalPrefs] = useState({
        role: "Senior React Developer",
        min_salary: "180k",
        job_type: "Remote",
        posted_within: "24 Hours",
        platforms: ["LinkedIn", "Indeed"],
        skip_conditions: ["No remote", "Less than 100k"]
    });

    const handleLaunch = () => {
        setPreferences(prefs);
        if (sessionId) {
            wsManager.connect(sessionId);
        }
        router.push("/dashboard");
    };

    return (
        <div className="bg-background-dark min-h-screen pt-24 pb-12 px-6 selection:bg-primary selection:text-black">
            <main className="max-w-4xl mx-auto py-12">
                <div className="flex items-center gap-4 mb-8">
                    <p className="font-mono text-sm font-bold uppercase tracking-widest bg-primary text-black px-2 py-0.5">STEP 02 OF 02</p>
                    <h1 className="text-4xl md:text-6xl font-bold text-white uppercase tracking-tighter italic">SET AGENT RULES</h1>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                    <div className="space-y-8">
                        {/* Role Field */}
                        <div className="group">
                            <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 transition-colors group-focus-within:text-primary">Target Job Role</label>
                            <input
                                type="text"
                                value={prefs.role}
                                onChange={(e) => setLocalPrefs({ ...prefs, role: e.target.value })}
                                className="w-full bg-transparent border-b-4 border-white/10 text-3xl font-bold py-2 focus:outline-none focus:border-primary transition-colors text-white uppercase"
                            />
                        </div>

                        {/* Salary Field */}
                        <div className="group">
                            <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 transition-colors group-focus-within:text-primary">Min Salary (Annual)</label>
                            <input
                                type="text"
                                value={prefs.min_salary}
                                onChange={(e) => setLocalPrefs({ ...prefs, min_salary: e.target.value })}
                                className="w-full bg-transparent border-b-4 border-white/10 text-3xl font-bold py-2 focus:outline-none focus:border-primary transition-colors text-white uppercase tabular-nums"
                            />
                        </div>

                        {/* Job Type */}
                        <div className="flex gap-4">
                            {["Remote", "On-site", "Hybrid"].map(type => (
                                <button
                                    key={type}
                                    onClick={() => setLocalPrefs({ ...prefs, job_type: type })}
                                    className={`flex-1 py-3 border-2 font-bold uppercase tracking-widest transition-all ${prefs.job_type === type ? "bg-primary border-primary text-black" : "border-white/10 text-white/40 hover:border-white/20"}`}
                                >
                                    {type}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="relative">
                        <div className="absolute inset-0 border-4 border-primary translate-x-4 translate-y-4 -z-10 opacity-20"></div>
                        <div className="bg-neutral-dark border-4 border-primary/30 p-8 h-full">
                            <h3 className="text-xl font-bold uppercase tracking-tight text-white mb-6">Agent Preview</h3>
                            <div className="space-y-6 font-mono text-sm leading-relaxed">
                                <p className="text-primary/60"><span className="text-white">STATUS:</span> CALIBRATED</p>
                                <p className="text-slate-400">If job title contains <span className={`text-primary font-bold ${prefs.role ? "bg-primary/10" : ""}`}>"{prefs.role}"</span> and salary is above <span className={`text-primary font-bold ${prefs.min_salary ? "bg-primary/10" : ""}`}>"{prefs.min_salary}"</span>, execute application sequence.</p>
                                <p className="text-slate-400">Otherwise, log as <span className="text-red-400 font-bold uppercase">SKIPPED</span> and proceed to next target.</p>
                                <div className="pt-6 border-t border-white/5 space-y-2">
                                    <p className="text-xs text-slate-500 uppercase font-black tracking-widest">Active Platforms</p>
                                    <div className="flex flex-wrap gap-2">
                                        {["LinkedIn", "Indeed", "Glassdoor"].map(p => (
                                            <span key={p} className="bg-white/5 px-3 py-1 text-[10px] font-bold text-white/50">{p}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-16">
                    <button
                        onClick={handleLaunch}
                        className="w-full bg-primary text-black text-2xl font-black py-8 uppercase tracking-tighter flex items-center justify-center gap-4 hover:scale-[1.02] transition-transform shadow-[8px_8px_0px_#ffffff20]"
                    >
                        UNLEASH THE AGENT
                        <span className="material-symbols-outlined text-4xl">bolt</span>
                    </button>
                    <p className="text-center mt-6 text-slate-500 text-xs font-bold uppercase tracking-widest animate-pulse">
                        READY TO SCRAPE • READY TO APPLY • READY TO WIN
                    </p>
                </div>
            </main>
        </div>
    );
}
