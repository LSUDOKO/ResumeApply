import type { Metadata } from "next";
import { Space_Grotesk, Bebas_Neue, Space_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import CustomCursor from "@/components/CustomCursor";
import PageTransition from "@/components/PageTransition";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const bebasNeue = Bebas_Neue({
  variable: "--font-bebas-neue",
  subsets: ["latin"],
  weight: "400",
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "ResumeApply | AI-First Job Application Agent",
  description: "Your job search, AUTOMAT*D. ResumeApply is an AI-first job application agent that applies to 10 jobs in 2 minutes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap"
        />
      </head>
      <body
        className={`${spaceGrotesk.variable} ${bebasNeue.variable} ${spaceMono.variable} antialiased font-display relative min-h-screen flex flex-col`}
      >
        <CustomCursor />
        <PageTransition>
          <Navbar />
          <main className="flex-1">
            {children}
          </main>
          <Footer />
        </PageTransition>
      </body>
    </html>
  );
}
