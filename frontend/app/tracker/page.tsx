"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import SplitType from "split-type";
import Link from "next/link";
import { useAgentStore } from "@/lib/store";

gsap.registerPlugin(ScrollTrigger);

export default function TrackerPage() {
    const mainRef = useRef<HTMLDivElement>(null);
    const { sessionId, totalApplied, totalSkipped, applications: storeApps } = useAgentStore();
    const [results, setResults] = useState<any[]>(storeApps);

    useEffect(() => {
        const fetchResults = async () => {
            if (!sessionId) return;
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            try {
                const response = await fetch(`${apiUrl}/api/agent/results/${sessionId}`);
                const data = await response.json();
                setResults(data.applications || storeApps);
            } catch (error) {
                console.error("Failed to fetch results", error);
            }
        };

        fetchResults();

        const ctx = gsap.context(() => {
            gsap.from(".stat-card", {
                y: 40,
                opacity: 0,
                stagger: 0.15,
                duration: 0.8,
                ease: "power2.out",
            });

            document.querySelectorAll(".stat-number").forEach((el) => {
                gsap.from(el, {
                    innerText: 0,
                    duration: 1.5,
                    snap: { innerText: 1 },
                    scrollTrigger: {
                        trigger: el,
                        start: "top 80%",
                    },
                });
            });

            gsap.from("tbody tr", {
                x: -20,
                opacity: 0,
                stagger: 0.08,
                duration: 0.5,
                scrollTrigger: {
                    trigger: "table",
                    start: "top 80%",
                },
            });

            const ctaHeadline = new SplitType(".final-cta-headline", { types: "chars" });
            gsap.from(ctaHeadline.chars, {
                y: 100,
                opacity: 0,
                rotationX: 90,
                stagger: 0.04,
                duration: 1,
                ease: "expo.out",
                scrollTrigger: {
                    trigger: ".final-cta-section",
                    start: "top 70%",
                }
            });
        }, mainRef);

        return () => ctx.revert();
    }, [sessionId]);

    const displayResults = results;

    return (
        <div ref={mainRef} className="bg-background-light min-h-screen pt-24 transition-colors duration-300">
            <div className="max-w-7xl mx-auto w-full px-6 py-12">
                <h1 className="text-[8vw] font-bold leading-none tracking-tighter text-background-dark mb-12 uppercase italic">
                    YOUR APPLICATIONS.<br />FILED.
                </h1>

                {/* Stat Blocks */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border-4 border-background-dark mb-16">
                    <div className="stat-card bg-background-dark p-8 border-b-4 md:border-b-0 md:border-r-4 border-white/10">
                        <p className="text-white/60 text-sm font-bold tracking-widest uppercase mb-2">Applied</p>
                        <p className="stat-number text-primary text-8xl font-bold leading-none">{totalApplied || displayResults.filter(r => r.status === 'applied').length}</p>
                    </div>
                    <div className="stat-card bg-background-dark p-8 border-b-4 md:border-b-0 md:border-r-4 border-white/10">
                        <p className="text-white/60 text-sm font-bold tracking-widest uppercase mb-2">Skipped</p>
                        <p className="stat-number text-primary text-8xl font-bold leading-none">{totalSkipped || displayResults.filter(r => r.status === 'skipped').length}</p>
                    </div>
                    <div className="stat-card bg-background-dark p-8">
                        <p className="text-white/60 text-sm font-bold tracking-widest uppercase mb-2">Active Time</p>
                        <div className="flex items-baseline gap-1">
                            <span className="stat-number text-primary text-8xl font-bold leading-none">08:12</span>
                        </div>
                    </div>
                </div>

                {/* Brutalist Table */}
                <div className="w-full overflow-x-auto">
                    <table className="w-full border-4 border-background-dark text-left border-collapse">
                        <thead>
                            <tr className="bg-background-dark text-white uppercase text-sm font-bold tracking-widest">
                                <th className="p-6 border-r-4 border-white/10">Company</th>
                                <th className="p-6 border-r-4 border-white/10">Role</th>
                                <th className="p-6 border-r-4 border-white/10">Match %</th>
                                <th className="p-6 border-r-4 border-white/10">Status</th>
                                <th className="p-6">Time</th>
                            </tr>
                        </thead>
                        <tbody className="text-background-dark font-medium">
                            {displayResults.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-12 text-center text-background-dark/50 italic border-b-4 border-background-dark text-xl">
                                        No applications processed yet. Check the agent's live view.
                                    </td>
                                </tr>
                            ) : (
                                displayResults.map((row, i) => (
                                    <tr key={i} className="border-b-4 border-background-dark hover:bg-white transition-colors cursor-pointer group">
                                        <td className="p-6 border-r-4 border-background-dark font-bold">{row.company}</td>
                                        <td className="p-6 border-r-4 border-background-dark">{row.job_title}</td>
                                        <td className="p-6 border-r-4 border-background-dark text-3xl font-bold text-background-dark bg-primary/20">{row.match_score || 'N/A'}%</td>
                                        <td className="p-6 border-r-4 border-background-dark">
                                            <span className={`px-4 py-1 text-xs font-bold uppercase ${row.status === "applied" ? "bg-background-dark text-white" : "bg-red-500 text-white"}`}>
                                                {row.status}
                                            </span>
                                        </td>
                                        <td className="p-6 italic">{new Date(row.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Bottom Section (Black Background) */}
            <div className="bg-background-dark py-24 px-6 border-t-8 border-primary final-cta-section">
                <div className="max-w-7xl mx-auto flex flex-col items-center text-center">
                    <h2 className="final-cta-headline text-white text-[7vw] font-bold leading-none tracking-tighter mb-12 uppercase">
                        WANT TO RUN AGAIN?
                    </h2>
                    <div className="flex flex-col md:flex-row gap-6 w-full max-w-2xl mb-16">
                        <Link href="/upload" className="flex-1 bg-primary text-black font-black text-2xl py-6 flex items-center justify-center gap-3 hover:scale-105 transition-transform group">
                            NEW SEARCH
                            <span className="material-symbols-outlined font-black group-hover:translate-x-2 transition-transform">arrow_forward</span>
                        </Link>
                        <Link href="/preferences" className="flex-1 bg-transparent border-4 border-white text-white font-black text-2xl py-6 hover:bg-white hover:text-black transition-colors text-center">
                            EDIT PREFERENCES
                        </Link>
                    </div>

                    <div className="border-4 border-white/20 p-8 inline-block">
                        <p className="text-white/50 text-sm font-bold tracking-widest uppercase mb-4">Rate limit refresh</p>
                        <div className="flex items-center gap-4">
                            <span className="material-symbols-outlined text-primary text-4xl">schedule</span>
                            <p className="text-white text-4xl md:text-6xl font-display font-bold tabular-nums">NEXT SESSION IN: 08:00:00</p>
                        </div>
                    </div>
                    <div className="mt-24 text-white/30 text-xs font-bold tracking-widest uppercase flex flex-wrap justify-center gap-8">
                        <span>© 2024 RESUMEAPPLY AGENT</span>
                        <span>SYSTEM STATUS: OPTIMIZED</span>
                        <span>API LATENCY: 42MS</span>
                    </div>
                </div>
            </div>
        </div >
    );
}
