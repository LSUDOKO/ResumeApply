import { NextResponse } from 'next/server'

export async function POST(req: Request) {
    try {
        const { system_prompt } = await req.json()

        // In a real hackathon scenario, this would call the Google Gemini Live API
        // and return a WebRTC offer. For this implementation, we return a mock
        // success to allow the frontend UI to flow.
        return NextResponse.json({
            offer: { type: 'offer', sdp: 'mock-sdp' },
            sessionId: 'mock-session-id'
        })
    } catch (error) {
        return NextResponse.json({ error: 'Failed to create session' }, { status: 500 })
    }
}
