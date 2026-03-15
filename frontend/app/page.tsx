"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import SplitType from "split-type";
import Ticker from "@/components/Ticker";
import Link from "next/link";

gsap.registerPlugin(ScrollTrigger);

export default function LandingPage() {
  const mainRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Hero Animation
      const heroText = new SplitType(".hero-headline", { types: "chars" });

      const tl = gsap.timeline();

      tl.from(".hero-subtext", {
        x: -60,
        opacity: 0,
        duration: 0.7,
        ease: "power3.out",
        delay: 0.5
      })
        .from(heroText.chars, {
          y: 120,
          opacity: 0,
          rotationX: 90,
          stagger: 0.04,
          duration: 1,
          ease: "expo.out"
        })
        .from(".hero-cta", {
          scale: 0.8,
          opacity: 0,
          duration: 0.6,
          ease: "back.out(1.7)"
        }, "-=0.2")
        .from(".hero-ticker", {
          y: 40,
          opacity: 0,
          duration: 0.6
        }, "-=0.4");

      // Count up effect for ticker
      const countObj = { val: 0 };
      gsap.to(countObj, {
        val: 2847,
        duration: 2,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".hero-ticker",
          start: "top bottom",
        },
        onUpdate: () => {
          const el = document.querySelector(".count-up");
          if (el) el.textContent = Math.floor(countObj.val).toLocaleString();
        }
      });

      // Hero Parallax
      gsap.to(".hero-headline", {
        y: -80,
        scrollTrigger: {
          trigger: ".hero-section",
          start: "top top",
          end: "bottom top",
          scrub: true,
        }
      });

      // Feature Reveal
      const highlight = document.querySelector(".ai-highlight");
      if (highlight) {
        gsap.from(highlight, {
          scaleX: 0,
          transformOrigin: "left center",
          duration: 0.8,
          ease: "power3.inOut",
          scrollTrigger: {
            trigger: highlight,
            start: "top 80%",
          }
        });
      }

      gsap.from(".feature-card", {
        y: 60,
        opacity: 0,
        stagger: 0.2,
        duration: 0.8,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".features-grid",
          start: "top 80%",
        }
      });

      // How It Works Step Counter
      document.querySelectorAll(".step-number").forEach((num) => {
        const val = num.getAttribute("data-value");
        gsap.from(num, {
          innerText: 0,
          duration: 1,
          snap: { innerText: 1 },
          scrollTrigger: {
            trigger: num,
            start: "top 90%",
          }
        });
        gsap.to(num, {
          opacity: 0.15,
          duration: 0.5,
          scrollTrigger: {
            trigger: num,
            start: "top 90%",
          }
        });
      });

      // Mockup Entry
      gsap.from(".product-mockup", {
        y: 80,
        opacity: 0,
        rotation: -2,
        duration: 1,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ".product-mockup",
          start: "top 80%",
        }
      });

      // Floating animation for mockup
      gsap.to(".product-mockup", {
        y: -8,
        duration: 3,
        ease: "sine.inOut",
        yoyo: true,
        repeat: -1
      });

      // Stacked cards reveal
      gsap.from(".wave-card", {
        y: 100,
        opacity: 0,
        stagger: 0.15,
        scrollTrigger: {
          trigger: ".cards-stack",
          start: "top 80%",
        }
      });

      // CTA Line Split
      const ctaLines = new SplitType(".cta-headline", { types: "lines" });
      gsap.from(ctaLines.lines, {
        x: -80,
        opacity: 0,
        stagger: 0.15,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ".cta-section",
          start: "top 70%",
        }
      });

    }, mainRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={mainRef} className="overflow-x-hidden">
      {/* Section 1: Hero */}
      <section className="hero-section bg-primary min-h-screen flex flex-col relative overflow-hidden border-b-4 border-black pt-24">
        <div className="flex-grow flex flex-col justify-center items-center text-center px-4 py-20">
          <p className="hero-subtext font-bold text-black uppercase tracking-widest text-lg md:text-xl mb-4">
            Your job search,
          </p>
          <h1 className="hero-headline font-bebas text-[15vw] leading-[0.8] text-black uppercase">
            AUTOMAT*D
          </h1>
          <div className="hero-cta mt-12">
            <Link href="/upload" className="bg-black text-primary px-12 py-6 rounded-full font-bebas text-4xl tracking-wider hover:bg-slate-900 transition-colors inline-block">
              START THE AGENT — FREE
            </Link>
          </div>
        </div>

        {/* Hero Ticker */}
        <div className="hero-ticker bg-black py-4 border-t-2 border-black">
          <Ticker speed={20}>
            <span className="text-primary font-bebas text-2xl tracking-widest flex items-center gap-4 px-12">
              APPLICATIONS FILED TODAY ↗ <span className="count-up">2,847</span> <span className="text-white">|</span> SR. REACT DEV... · COMPANY: **** · STATUS: APPLIED ✓
            </span>
          </Ticker>
        </div>
      </section>

      {/* Section 2: Features */}
      <section className="bg-white py-32 px-6 md:px-12 border-b-4 border-black">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-bebas text-6xl md:text-8xl text-black leading-none mb-20 max-w-4xl uppercase">
            RESUMEAPPLY IS AN <span className="relative inline-block"><span className="ai-highlight absolute inset-0 bg-primary -z-10"></span><span className="px-4">AI-FIRST</span></span> JOB APPLICATION AGENT
          </h2>
          <div className="features-grid grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: "edit_note", title: "Zero manual form filling", desc: "Our neural engine interprets every complex field, from 'Why us?' to multi-step logic forms." },
              { icon: "speed", title: "Applies to 10 jobs in 2 minutes", desc: "Parallel processing allows the agent to navigate Workday, Greenhouse, and Lever simultaneously." },
              { icon: "settings_voice", title: "One voice command", desc: "\"Apply to senior react roles in NYC with salary over 180k.\" Done. Watch it happen live." }
            ].map((f, i) => (
              <div key={i} className="feature-card flex flex-col gap-6 p-8 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] bg-white">
                <span className="material-symbols-outlined text-6xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>{f.icon}</span>
                <h3 className="font-bebas text-4xl text-black uppercase tracking-tight">{f.title}</h3>
                <p className="text-xl text-slate-700 leading-relaxed font-medium">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 3: How it Works */}
      <section id="how-it-works" className="bg-[#0f0f0f] py-32 px-6 md:px-12 border-b-4 border-black overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-bebas text-primary text-6xl md:text-9xl mb-24">HOW IT WORKS</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-16 mb-24">
            {[
              { num: "01", title: "UPLOAD RESUME", desc: "PDF or Docx. Our parser extracts 100+ data points for perfect mapping." },
              { num: "02", title: "SPEAK YOUR COMMAND", desc: "Define roles, locations, and deal-breakers in plain natural language." },
              { num: "03", title: "WATCH IT APPLY", desc: "The dashboard reflects live browser sessions as the agent works." }
            ].map((s, i) => (
              <div key={i} className="relative">
                <span className="step-number font-bebas text-[10rem] text-primary absolute -top-24 -left-4 pointer-events-none opacity-10" data-value={s.num}>{s.num}</span>
                <div className="relative z-10">
                  <h3 className="font-bebas text-4xl text-white mb-4">{s.title}</h3>
                  <p className="text-slate-400 text-lg font-medium">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Product Mockup */}
          <div className="product-mockup w-full border-4 border-primary p-4 md:p-8 bg-black/50 aspect-video relative group overflow-hidden">
            <div className="flex items-center gap-2 mb-6 border-b-2 border-primary/20 pb-4">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <div className="ml-4 px-3 py-1 bg-primary/10 text-primary font-mono text-xs uppercase">LIVE_SESSION: WORKDAY_INSTANCE_442</div>
            </div>
            <div className="grid grid-cols-12 gap-6 h-full opacity-60">
              <div className="col-span-8 bg-primary/5 border border-primary/30 p-4">
                <div className="h-4 w-3/4 bg-primary/20 mb-4"></div>
                <div className="h-4 w-1/2 bg-primary/20 mb-12"></div>
                <div className="space-y-4">
                  <div className="h-12 w-full border border-primary/40 bg-black"></div>
                  <div className="h-12 w-full border border-primary/40 bg-black"></div>
                  <div className="h-32 w-full border border-primary/40 bg-black"></div>
                </div>
              </div>
              <div className="col-span-4 space-y-4">
                <div className="h-32 w-full bg-primary border-4 border-black text-black p-4 font-bold uppercase">
                  MATCH: 98%
                </div>
                <div className="h-auto w-full border border-primary/30 p-4 font-mono text-[10px] text-primary overflow-hidden">
                  [AGENT] Reading Job Description...<br />
                  [AGENT] Extracting Skills: React, TypeScript, GraphQL...<br />
                  [AGENT] Generating Cover Letter...<br />
                  [AGENT] Filling Form Step 1/4...
                </div>
              </div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span className="font-bebas text-primary/20 text-[15vw] rotate-[-15deg] group-hover:scale-110 transition-transform duration-500">AGENT ACTIVE</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Agent Features (Overlapping Cards) */}
      <section className="bg-black py-32 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-bebas text-white text-6xl md:text-9xl text-center mb-32 leading-none uppercase">AGENT INTELLIGENCE<br />AT EVERY STEP</h2>
          <div className="cards-stack relative h-[800px] flex flex-col items-center">
            {[
              { title: "Resume Parsing", icon: "description", desc: "Beyond keywords. We understand context, career progression, and unwritten skills that HR systems look for.", color: "bg-primary text-black" },
              { title: "Visual Job Reading", icon: "visibility", desc: "The agent actually \"sees\" the web page to identify non-standard form components and dynamic elements.", color: "bg-[#333] text-white", translate: "translate-x-4" },
              { title: "Smart Matching", icon: "balance", desc: "Automatically filter out low-salary listings, toxic Glassdoor reviews, and non-remote roles before applying.", color: "bg-[#666] text-white", translate: "-translate-x-4" },
              { title: "Cover Letter Gen", icon: "history_edu", desc: "Hyper-personalized cover letters written for each specific role based on your unique career highlights.", color: "bg-[#999] text-black", translate: "translate-y-4" }
            ].map((card, idx) => (
              <div key={idx} className={`wave-card sticky top-${20 + idx * 20} w-full max-w-4xl brutalist-border p-12 mb-[-600px] z-${(idx + 1) * 10} ${card.color} ${card.translate || ""} hover:-translate-y-2 transition-transform duration-300`}>
                <div className="flex justify-between items-start">
                  <h3 className="font-bebas text-6xl uppercase">{card.title}</h3>
                  <span className="material-symbols-outlined text-5xl">{card.icon}</span>
                </div>
                <p className="text-2xl mt-8 max-w-2xl leading-tight font-medium">{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 5: CTA */}
      <section className="cta-section bg-[#F2F2EE] py-32 px-6 md:px-12 border-t-4 border-black overflow-hidden relative">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center gap-20">
          <div className="flex-1 text-center md:text-left">
            <h2 className="cta-headline font-bebas text-7xl md:text-9xl text-black leading-none mb-12">START YOUR JOB SEARCH—<br />HANDS FREE.</h2>
            <Link href="/upload" className="bg-primary text-black px-12 py-6 rounded-full font-bebas text-3xl tracking-widest border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-all inline-block">
              TRY RESUMEAPPLY FREE
            </Link>
            <p className="mt-8 font-bold text-black/40 uppercase tracking-widest">NO CREDIT CARD REQUIRED — 5 FREE APPLICATIONS</p>
          </div>

          <div className="flex-1 relative">
            <div className="product-mockup w-72 h-[550px] bg-black border-8 border-slate-900 rounded-[3rem] mx-auto shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 w-full h-8 bg-black flex justify-center items-center">
                <div className="w-16 h-4 bg-slate-800 rounded-full"></div>
              </div>
              <div className="p-6 pt-12 text-white h-full flex flex-col">
                <div className="flex justify-between items-center mb-8">
                  <span className="font-bebas text-2xl tracking-widest">STATUS</span>
                  <span className="px-3 py-1 bg-primary text-black font-bold text-xs">LIVE</span>
                </div>
                <div className="space-y-4 flex-grow">
                  <div className="bg-primary/10 border border-primary/40 p-4">
                    <p className="text-[10px] text-primary/60 uppercase font-bold">Applications Sent</p>
                    <p className="font-bebas text-5xl text-primary">42</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-4">
                    <p className="text-[10px] text-white/40 uppercase font-bold">Interviews Booked</p>
                    <p className="font-bebas text-5xl text-white">03</p>
                  </div>
                  <div className="flex-grow flex flex-col justify-end gap-2">
                    <div className="h-1 bg-primary w-full"></div>
                    <div className="h-1 bg-primary w-2/3"></div>
                    <div className="h-1 bg-primary/20 w-1/2"></div>
                  </div>
                </div>
                <div className="mt-8">
                  <div className="h-12 w-full bg-primary rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined text-black">pause</span>
                  </div>
                </div>
              </div>
            </div>
            {/* Accent circles */}
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-primary/20 rounded-full -z-10 blur-3xl"></div>
            <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-primary/20 rounded-full -z-10 blur-3xl"></div>
          </div>
        </div>
      </section>
    </div>
  );
}
