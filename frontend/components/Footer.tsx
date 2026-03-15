"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Footer() {
    const pathname = usePathname();
    const isDashboard = pathname === "/dashboard";
    const isLanding = pathname === "/";

    if (isDashboard) {
        return (
            <footer className="bg-primary overflow-hidden py-2 select-none border-t border-black">
                <div className="flex whitespace-nowrap items-center animate-marquee">
                    <div className="flex items-center gap-8 px-4">
                        <span className="text-background-dark font-black text-xs uppercase italic tracking-tighter">7 Applied</span>
                        <span className="text-background-dark/40">•</span>
                        <span className="text-background-dark font-black text-xs uppercase italic tracking-tighter">4 Skipped</span>
                        <span className="text-background-dark/40">•</span>
                        <span className="text-background-dark font-black text-xs uppercase italic tracking-tighter">2 Min Elapsed</span>
                        <span className="text-background-dark/40">•</span>
                        <span className="text-background-dark font-black text-xs uppercase italic tracking-tighter">LinkedIn Complete → Switching to Naukri</span>
                    </div>
                </div>
                <style jsx>{`
          @keyframes marquee {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
          .animate-marquee {
            display: flex;
            animation: marquee 20s linear infinite;
          }
        `}</style>
            </footer>
        );
    }

    return (
        <footer className="bg-black py-12 px-6 border-t-2 border-primary/20">
            <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-2xl text-primary">bolt</span>
                    <span className="font-bebas text-2xl tracking-tighter text-white">ResumeApply</span>
                </div>
                <div className="flex gap-8 text-slate-500 font-bold uppercase text-xs tracking-widest">
                    <Link href="#" className="hover:text-primary">Privacy</Link>
                    <Link href="#" className="hover:text-primary">Terms</Link>
                    <Link href="#" className="hover:text-primary">Twitter</Link>
                    <Link href="#" className="hover:text-primary">LinkedIn</Link>
                </div>
                <p className="text-slate-600 text-xs font-mono">©2024 RESUMEAPPLY_AGENT_CORE_v2.0.1</p>
            </div>
        </footer>
    );
}
