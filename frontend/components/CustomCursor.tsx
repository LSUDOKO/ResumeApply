"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";

export default function CustomCursor() {
    const cursorRef = useRef<HTMLDivElement>(null);
    const ringRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const cursor = cursorRef.current;
        const ring = ringRef.current;
        if (!cursor || !ring) return;

        const onMouseMove = (e: MouseEvent) => {
            const { clientX: x, clientY: y } = e;

            gsap.to(cursor, {
                x,
                y,
                duration: 0,
            });

            gsap.to(ring, {
                x,
                y,
                duration: 0.15,
                ease: "power2.out",
            });
        };

        const onMouseDown = () => {
            gsap.to([cursor, ring], { scale: 0.8, duration: 0.1 });
        };

        const onMouseUp = () => {
            gsap.to([cursor, ring], { scale: 1, duration: 0.1 });
        };

        const onMouseEnterLink = () => {
            gsap.to(cursor, { scale: 0, opacity: 0, duration: 0.2 });
            gsap.to(ring, {
                scale: 2,
                backgroundColor: "rgba(200, 255, 0, 0.15)",
                borderColor: "rgba(200, 255, 0, 0.5)",
                duration: 0.2,
            });
        };

        const onMouseLeaveLink = () => {
            gsap.to(cursor, { scale: 1, opacity: 1, duration: 0.2 });
            gsap.to(ring, {
                scale: 1,
                backgroundColor: "transparent",
                borderColor: "#c8ff00",
                duration: 0.2,
            });
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mousedown", onMouseDown);
        window.addEventListener("mouseup", onMouseUp);

        const links = document.querySelectorAll("a, button, [role='button']");
        links.forEach((link) => {
            link.addEventListener("mouseenter", onMouseEnterLink);
            link.addEventListener("mouseleave", onMouseLeaveLink);
        });

        return () => {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mousedown", onMouseDown);
            window.removeEventListener("mouseup", onMouseUp);
            links.forEach((link) => {
                link.removeEventListener("mouseenter", onMouseEnterLink);
                link.removeEventListener("mouseleave", onMouseLeaveLink);
            });
        };
    }, []);

    return (
        <>
            <div
                ref={cursorRef}
                className="fixed top-0 left-0 w-2.5 h-2.5 bg-primary rounded-full pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden md:block"
            />
            <div
                ref={ringRef}
                className="fixed top-0 left-0 w-8 h-8 border-2 border-primary rounded-full pointer-events-none z-[9998] -translate-x-1/2 -translate-y-1/2 hidden md:block"
            />
        </>
    );
}
