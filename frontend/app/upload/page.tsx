"use client";

import { useState, useRef, useEffect } from "react";
import gsap from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
import Ticker from "@/components/Ticker";
import Link from "next/link";
import { useAgentStore } from "@/lib/store";

gsap.registerPlugin(TextPlugin);

export default function UploadPage() {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploaded, setIsUploaded] = useState(false);
    const dropZoneRef = useRef<HTMLDivElement>(null);
    const dataRef = useRef<HTMLDivElement>(null);

    const { setProfile: storeProfile, setSessionId } = useAgentStore();
    const [uploading, setUploading] = useState(false);
    const [profile, setProfile] = useState<any>(null);
    const [manualMode, setManualMode] = useState(false);

    const handleUpload = async (uploadedFile: File) => {
        setUploading(true);
        setIsUploaded(true);

        const formData = new FormData();
        formData.append('file', uploadedFile);

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        try {
            const response = await fetch(`${apiUrl}/api/resume/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 429) {
                    if (confirm(`${errorData.detail}\n\nWould you like to manually fill your profile data to continue?`)) {
                        setManualMode(true);
                        setIsUploaded(true);
                        setUploading(false);
                        return;
                    }
                }
                alert(`Error: ${errorData.detail || "Upload failed"}`);
                setUploading(false);
                setIsUploaded(false);
                return;
            }

            const data = await response.json();
            if (!data || !data.profile) {
                console.error("Invalid profile data received", data);
                return;
            }

            setProfile(data.profile);
            storeProfile(data.profile);
            setSessionId(data.session_id);

            // Animation for data reveal
            const ctx = gsap.context(() => {
                const tl = gsap.timeline();
                const p = data.profile;
                tl.from(".extraction-card", { y: 20, opacity: 0, duration: 0.5 })
                    .to(".data-row-1", { text: `NAME: ${p.name || "Extracted Name"}`, duration: 1 })
                    .from(".check-1", { scale: 0, opacity: 0, duration: 0.3, ease: "back.out(2)" })
                    .to(".data-row-2", { text: `ROLE: ${p.current_role || "Extracted Role"}`, duration: 1.2 })
                    .from(".check-2", { scale: 0, opacity: 0, duration: 0.3, ease: "back.out(2)" })
                    .to(".data-row-3", { text: `EXP: ${p.years_experience || "N/A"} years`, duration: 0.8 })
                    .from(".check-3", { scale: 0, opacity: 0, duration: 0.3, ease: "back.out(2)" })
                    .to(".data-row-4", { text: `SKILLS: ${(p.skills || []).slice(0, 3).join(", ")}`, duration: 1.2 })
                    .from(".check-4", { scale: 0, opacity: 0, duration: 0.3, ease: "back.out(2)" })
                    .from(".confirm-btn", { y: 20, opacity: 0, duration: 0.5, ease: "power2.out" });
            }, dataRef);
        } catch (error) {
            console.error("Upload failed", error);
        } finally {
            setUploading(false);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
        gsap.to(dropZoneRef.current, { scale: 1.02, duration: 0.2 });
    };

    const handleDragLeave = () => {
        setIsDragging(false);
        gsap.to(dropZoneRef.current, { scale: 1, duration: 0.2 });
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    };

    return (
        <div className="bg-primary min-h-screen flex flex-col pt-24 overflow-hidden selection:bg-black selection:text-primary">
            <main className="flex-1 flex flex-col items-center justify-center px-6 py-12 max-w-4xl mx-auto w-full">
                <p className="font-mono text-sm font-bold mb-4 uppercase tracking-widest bg-black text-primary px-2 py-0.5">STEP 01 OF 02</p>
                <h1 className="text-6xl md:text-8xl font-bold leading-none text-center uppercase tracking-tighter mb-12 text-black">
                    DROP YOUR <br /> RESUM*
                </h1>

                <div className="w-full space-y-8" ref={dataRef}>
                    <div
                        ref={dropZoneRef}
                        className={`relative group cursor-pointer transition-all duration-300`}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => dropZoneRef.current?.querySelector('input')?.click()}
                    >
                        <input
                            type="file"
                            className="hidden"
                            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                        />
                        <div className="absolute inset-0 border-4 border-black translate-x-2 translate-y-2"></div>
                        <div className={`relative border-4 ${isDragging ? "border-solid bg-primary/80" : "border-dashed bg-primary"} border-black p-12 flex flex-col items-center gap-6 transition-transform group-hover:-translate-x-1 group-hover:-translate-y-1`}>
                            <span className="material-symbols-outlined text-6xl text-black">description</span>
                            <div className="text-center text-black">
                                <p className="text-2xl font-bold uppercase tracking-tight mb-2">PDF or DOCX</p>
                                <p className="font-medium">{uploading ? "Analyzing..." : "Gemini reads it instantly"}</p>
                            </div>
                            <button className="bg-black text-primary px-8 py-3 font-bold uppercase tracking-wider hover:bg-white hover:text-black transition-colors">
                                {uploading ? "ALYZING..." : "Select File"}
                            </button>
                        </div>
                    </div>

                    {isUploaded && !manualMode && (
                        <div className="extraction-card w-full bg-black text-primary p-8 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]">
                            <div className="flex justify-between items-center mb-6 border-b border-primary/30 pb-4">
                                <h3 className="text-xl font-bold uppercase tracking-tight">Extracted Data</h3>
                                <span className="font-mono text-xs bg-primary text-black px-2 py-1">AI ANALYZED</span>
                            </div>
                            <div className="font-mono space-y-4 text-sm md:text-base">
                                {[1, 2, 3, 4].map((i) => (
                                    <div key={i} className="flex justify-between items-center border-b border-primary/10 pb-2">
                                        <span className={`data-row-${i} font-bold min-h-[1.5rem]`}></span>
                                        <span className={`check-${i} material-symbols-outlined text-sm opacity-0`}>check_circle</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {isUploaded && manualMode && (
                        <div className="w-full bg-white border-4 border-black p-8 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]">
                            <h3 className="text-2xl font-bold uppercase mb-6 text-black border-b-2 border-black pb-2">Manual Profile Setup</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-1">
                                    <label className="block font-bold uppercase text-[10px] text-black/60">Full Name</label>
                                    <input
                                        type="text"
                                        className="w-full border-2 border-black p-2 bg-transparent focus:bg-primary/20 outline-none text-black font-bold"
                                        placeholder="Arpit Gupta"
                                        onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="block font-bold uppercase text-[10px] text-black/60">Target Role</label>
                                    <input
                                        type="text"
                                        className="w-full border-2 border-black p-2 bg-transparent focus:bg-primary/20 outline-none text-black font-bold"
                                        placeholder="Product Engineer"
                                        onChange={(e) => setProfile({ ...profile, current_role: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-1 md:col-span-2">
                                    <label className="block font-bold uppercase text-[10px] text-black/60">Skills (Comma separated)</label>
                                    <input
                                        type="text"
                                        className="w-full border-2 border-black p-2 bg-transparent focus:bg-primary/20 outline-none text-black font-bold"
                                        placeholder="React, Python, Playwright"
                                        onChange={(e) => setProfile({ ...profile, skills: e.target.value.split(",") })}
                                    />
                                </div>
                            </div>
                            <button
                                onClick={() => {
                                    if (!profile?.name) return alert("Name required");
                                    storeProfile(profile);
                                    setSessionId("manual-" + Date.now());
                                    window.location.href = "/preferences";
                                }}
                                className="mt-8 w-full bg-black text-primary font-bold py-4 uppercase hover:bg-white hover:text-black border-2 border-black transition-all"
                            >
                                CONTINUE TO PREFERENCES
                            </button>
                        </div>
                    )}

                    {isUploaded && profile && !manualMode && (
                        <Link href="/preferences" className="confirm-btn block w-full bg-black text-primary text-xl font-bold py-6 uppercase tracking-tighter text-center hover:bg-white hover:text-black transition-all border-4 border-black">
                            Confirm & Set Preferences
                            <span className="material-symbols-outlined align-middle ml-4">arrow_forward</span>
                        </Link>
                    )}
                </div>
            </main>

            <footer className="mt-auto border-t-4 border-black bg-black py-4">
                <Ticker speed={25} className="text-primary font-mono font-bold text-sm uppercase tracking-widest py-1">
                    Gemini reading your resume • Extracting skills • Matching job patterns • Building your profile •
                </Ticker>
            </footer>
        </div>
    );
}
