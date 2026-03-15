"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { usePathname } from "next/navigation";

export default function PageTransition({ children }: { children: React.ReactNode }) {
    const overlayRef = useRef<HTMLDivElement>(null);
    const pathname = usePathname();

    useEffect(() => {
        const overlay = overlayRef.current;
        if (!overlay) return;

        const tl = gsap.timeline();

        // Entrance animation (overlay sliding up out of view)
        tl.set(overlay, { y: "0%" });
        tl.to(overlay, {
            y: "-100%",
            duration: 0.8,
            ease: "power3.inOut",
            delay: 0.1,
        });

    }, [pathname]);

    return (
        <>
            <div
                ref={overlayRef}
                className="fixed inset-0 bg-primary z-[9999] pointer-events-none"
                style={{ transform: "translateY(0%)" }}
            />
            {children}
        </>
    );
}
