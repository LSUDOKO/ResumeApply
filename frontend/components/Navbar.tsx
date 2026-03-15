"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
    const navRef = useRef<HTMLElement>(null);
    const pathname = usePathname();
    const isLanding = pathname === "/";

    useEffect(() => {
        const handleScroll = () => {
            if (!navRef.current) return;
            if (window.scrollY > 80) {
                gsap.to(navRef.current, {
                    backgroundColor: isLanding ? "#000000" : "rgba(15, 15, 15, 0.8)",
                    paddingTop: "12px",
                    paddingBottom: "12px",
                    borderBottom: "1px solid rgba(200, 255, 0, 0.1)",
                    duration: 0.3,
                    ease: "power2.out",
                });
            } else {
                gsap.to(navRef.current, {
                    backgroundColor: isLanding ? "transparent" : "rgba(26, 26, 26, 0.5)",
                    paddingTop: "24px",
                    paddingBottom: "24px",
                    borderBottom: "1px solid rgba(200, 255, 0, 0)",
                    duration: 0.3,
                    ease: "power2.out",
                });
            }
        };

        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, [isLanding]);

    useEffect(() => {
        // Initial reveal
        const ctx = gsap.context(() => {
            const tl = gsap.timeline();
            tl.from(".nav-logo", { y: -20, opacity: 0, duration: 0.6 })
                .from(".nav-link", { y: -10, opacity: 0, stagger: 0.1, duration: 0.4 }, "-=0.4");
        }, navRef);
        return () => ctx.revert();
    }, []);

    return (
        <nav
            ref={navRef}
            className={`fixed top-0 left-0 w-full z-50 flex items-center justify-between px-6 py-6 md:px-12 transition-all duration-300 ${isLanding ? "border-b-2 border-black" : "bg-neutral-dark/50 backdrop-blur-md border-b border-primary/10"}`}
        >
            <Link href="/" className="flex items-center gap-3 group cursor-pointer nav-logo">
                <div className={isLanding ? "text-black" : "bg-primary p-1 rounded-sm"}>
                    <span className="material-symbols-outlined text-4xl md:text-2xl font-bold">
                        {isLanding ? "bolt" : "robot_2"}
                    </span>
                </div>
                <h1 className={`text-xl font-bold tracking-tighter uppercase italic ${isLanding ? "text-black font-bebas text-3xl" : "text-white"}`}>
                    ResumeApply <span className={isLanding ? "" : "text-primary"}>Agent</span>
                </h1>
            </Link>

            <div className="hidden md:flex gap-12 items-center">
                <Link href="#how-it-works" className={`nav-link font-bold uppercase tracking-widest text-sm hover:underline decoration-2 ${isLanding ? "text-black" : "text-white"}`}>
                    How it works
                </Link>
                <Link href="#pricing" className={`nav-link font-bold uppercase tracking-widest text-sm hover:underline decoration-2 ${isLanding ? "text-black" : "text-white"}`}>
                    Pricing
                </Link>
                <Link href="/upload" className={`nav-link bg-black text-primary px-8 py-3 rounded-full font-bebas text-xl tracking-wide hover:scale-105 transition-transform ${isLanding ? "" : "hidden"}`}>
                    TRY NOW
                </Link>
                {!isLanding && (
                    <div className="flex items-center gap-8 nav-link">
                        <div className="flex items-center gap-2">
                            <span className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
                            </span>
                            <span className="text-xs font-bold tracking-widest text-primary uppercase">Agent Running</span>
                        </div>
                        <div className="h-10 w-10 bg-primary/20 border border-primary/50 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-2xl">person</span>
                        </div>
                    </div>
                )}
            </div>

            <button className={`md:hidden ${isLanding ? "text-black" : "text-white"} nav-link`}>
                <span className="material-symbols-outlined text-3xl">menu</span>
            </button>
        </nav>
    );
}
