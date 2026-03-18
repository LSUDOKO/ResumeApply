import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://resumeapply-backend-811871648603.us-central1.run.app'

export async function POST(req: Request) {
    try {
        const body = await req.json()
        const res = await fetch(`${BACKEND_URL}/api/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        const data = await res.json()
        return NextResponse.json(data, { status: res.status })
    } catch (error) {
        return NextResponse.json({ error: 'Failed to create session' }, { status: 500 })
    }
}
