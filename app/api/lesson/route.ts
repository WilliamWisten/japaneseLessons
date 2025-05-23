import { NextResponse } from 'next/server'

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url)
    const lessonNumber = searchParams.get('lesson_number')
    const userId = searchParams.get('user_id') || 'default_user' // For now, using a default user

    try {
        const response = await fetch(`http://localhost:8000/lesson?user_id=${userId}&lesson_number=${lessonNumber}`)

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error('Error fetching lesson:', error)
        return NextResponse.json(
            { error: 'Failed to fetch lesson' },
            { status: 500 }
        )
    }
} 