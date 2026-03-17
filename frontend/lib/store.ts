import { create } from 'zustand'

interface ResumeProfile {
    name: string
    email: string
    phone: string
    current_role: string
    years_experience: number
    skills: string[]
    education: string
    summary: string
}

interface Application {
    job_title: string
    company: string
    status: 'applied' | 'skipped'
    match_score: number
    reason?: string
    cover_letter?: string
    timestamp: string
}

interface AgentStore {
    sessionId: string | null
    setSessionId: (id: string) => void
    profile: ResumeProfile | null
    setProfile: (p: ResumeProfile) => void
    preferences: Record<string, any>
    setPreferences: (p: Record<string, any>) => void
    agentStatus: 'idle' | 'running' | 'paused' | 'complete'
    setAgentStatus: (s: 'idle' | 'running' | 'paused' | 'complete') => void
    currentScreenshot: string | null
    setCurrentScreenshot: (s: string | null) => void
    currentUrl: string
    setCurrentUrl: (u: string) => void
    agentThinking: string
    setAgentThinking: (t: string) => void
    applications: Application[]
    addApplication: (a: Application) => void
    totalApplied: number
    totalSkipped: number
    elapsedSeconds: number
    incrementApplied: () => void
    incrementSkipped: () => void
    setElapsed: (s: number) => void
    lastVoiceCommand: string
    setLastVoiceCommand: (c: string) => void
    agentLogs: string[]
    addLog: (msg: string) => void
    sessionStartTime: number | null
    setSessionStartTime: (t: number) => void
}

export const useAgentStore = create<AgentStore>((set) => ({
    sessionId: null,
    setSessionId: (id) => set({ sessionId: id }),
    profile: null,
    setProfile: (p) => set({ profile: p }),
    preferences: {},
    setPreferences: (p) => set({ preferences: p }),
    agentStatus: 'idle',
    setAgentStatus: (s) => set({ agentStatus: s }),
    currentScreenshot: null,
    setCurrentScreenshot: (s) => set({ currentScreenshot: s }),
    currentUrl: '',
    setCurrentUrl: (u) => set({ currentUrl: u }),
    agentThinking: '',
    setAgentThinking: (t) => set({ agentThinking: t }),
    applications: [],
    addApplication: (a) => set((state) => ({
        applications: [a, ...state.applications]
    })),
    totalApplied: 0,
    totalSkipped: 0,
    elapsedSeconds: 0,
    incrementApplied: () => set((s) => ({ totalApplied: s.totalApplied + 1 })),
    incrementSkipped: () => set((s) => ({ totalSkipped: s.totalSkipped + 1 })),
    setElapsed: (s) => set({ elapsedSeconds: s }),
    lastVoiceCommand: '',
    setLastVoiceCommand: (c) => set({ lastVoiceCommand: c }),
    agentLogs: [],
    addLog: (msg) => set((s) => ({ agentLogs: [msg, ...s.agentLogs].slice(0, 200) })),
    sessionStartTime: null,
    setSessionStartTime: (t) => set({ sessionStartTime: t }),
}))
