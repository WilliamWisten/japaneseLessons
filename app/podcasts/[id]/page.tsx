"use client"

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'
import { api, LessonData } from '@/lib/api'
import { LessonContent } from '@/components/LessonContent'
import { LessonComplete } from '@/components/LessonComplete'
import { Header } from '@/components/Header'

export default function PodcastLessonPage() {
    const { user } = useAuth();
    const params = useParams();
    const router = useRouter();
    const [lesson, setLesson] = useState<LessonData | null>(null);
    const [isComplete, setIsComplete] = useState(false);
    const [score, setScore] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!user || !params.id) return;

        const loadLesson = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const lessonData = await api.getPodcastLesson(user.uid, params.id as string);
                setLesson(lessonData);
            } catch (err) {
                setError('Failed to load lesson. Please try again.');
                console.error('Error loading lesson:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadLesson();
    }, [user, params.id]);

    const handleComplete = async (finalScore: number, exerciseResults: Array<{
        word: string;
        is_correct: boolean;
        question: string;
    }>) => {
        if (!user || !lesson) return;

        try {
            setScore(finalScore);
            setIsComplete(true);

            await api.saveProgress(user.uid, {
                lesson_id: params.id as string,
                completed: true,
                score: finalScore,
                questions_total: lesson.exercises.length,
                questions_correct: Math.round((finalScore / 100) * lesson.exercises.length),
                timestamp: new Date().toISOString(),
                exercises: exerciseResults
            }, 'podcast');
        } catch (err) {
            console.error('Error saving progress:', err);
            // Continue showing completion screen even if save fails
        }
    };

    const handleNextLesson = () => {
        router.push('/podcasts'); // Return to podcast library
    };

    if (!user) {
        return (
            <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
                <Header lessonNumber={null} />
                <div className="max-w-4xl mx-auto p-4 text-center">
                    <p className="text-zinc-400 mt-8">Please log in to access lessons.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
            <Header lessonNumber={null} />
            <main className="max-w-4xl mx-auto p-4">
                {isLoading ? (
                    <div className="text-center mt-8">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                        <p className="text-zinc-400 mt-4">Loading lesson...</p>
                    </div>
                ) : error ? (
                    <div className="text-center mt-8">
                        <p className="text-red-500">{error}</p>
                        <button
                            onClick={() => router.push('/podcasts')}
                            className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
                        >
                            Return to Library
                        </button>
                    </div>
                ) : isComplete ? (
                    <LessonComplete score={score} onNextLesson={handleNextLesson} />
                ) : lesson ? (
                    <LessonContent lesson={lesson} onComplete={handleComplete} />
                ) : null}
            </main>
        </div>
    );
} 