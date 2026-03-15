"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface TickerProps {
    children: React.ReactNode;
    speed?: number;
    className?: string;
    reverse?: boolean;
}

export default function Ticker({
    children,
    speed = 15,
    className,
    reverse = false,
}: TickerProps) {
    const tickerRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!tickerRef.current || !contentRef.current) return;

        const ctx = gsap.context(() => {
            gsap.to(contentRef.current, {
                xPercent: reverse ? 50 : -50,
                ease: "none",
                duration: speed,
                repeat: -1,
            });
        }, tickerRef);

        return () => ctx.revert();
    }, [speed, reverse]);

    const handleMouseEnter = () => {
        gsap.to(gsap.getTweensOf(contentRef.current), {
            timeScale: 0.3,
            duration: 0.5,
            overwrite: true,
        });
    };

    const handleMouseLeave = () => {
        gsap.to(gsap.getTweensOf(contentRef.current), {
            timeScale: 1,
            duration: 0.5,
            overwrite: true,
        });
    };

    return (
        <div
            ref={tickerRef}
            className={cn("ticker-wrap w-full select-none cursor-default", className)}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <div ref={contentRef} className="flex whitespace-nowrap items-center w-max">
                <div className="flex items-center">{children}</div>
                <div className="flex items-center">{children}</div>
            </div>
        </div>
    );
}
