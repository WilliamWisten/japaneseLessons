"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/Header"
import { LessonContent } from "@/components/LessonContent"
import { ExerciseSection } from "@/components/ExerciseSection"
import { LessonComplete } from "@/components/LessonComplete"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"

interface Lesson {
  review: Array<{
    type: string
    category: string
    concept: string
    data: {
      reading: string
      meaning: string
    }
  }>
  new_content: Array<{
    type: string
    category: string
    concept: string
    data: {
      reading: string
      meaning: string
    }
  }>
  exercises: Array<{
    type: string
    category: string
    question: string
    options: string[]
    correct: string
  }>
  duration: number
}

export default function JapaneseTutor() {
  const [currentLesson, setCurrentLesson] = useState<Lesson | null>(null)
  const [currentExercise, setCurrentExercise] = useState(0)
  const [lessonNumber, setLessonNumber] = useState(1)
  const [progress, setProgress] = useState(0)
  const [lessonComplete, setLessonComplete] = useState(false)

  const fetchLesson = async (lessonNum: number) => {
    try {
      const response = await fetch(`/api/lesson?lesson_number=${lessonNum}`)
      const data = await response.json()
      setCurrentLesson(data)
    } catch (error) {
      console.error("Error fetching lesson:", error)
      setCurrentLesson({
        review: [
          {
            type: "review",
            category: "vocabulary",
            concept: "こんにちは",
            data: { reading: "konnichiwa", meaning: "hello" },
          },
        ],
        new_content: [
          {
            type: "new",
            category: "vocabulary",
            concept: "猫",
            data: { reading: "neko", meaning: "cat" },
          },
        ],
        exercises: [
          {
            type: "multiple_choice",
            category: "vocabulary",
            question: "What is the meaning of こんにちは?",
            options: ["hello", "goodbye", "morning", "evening"],
            correct: "hello",
          },
        ],
        duration: 20,
      })
    }
  }

  useEffect(() => {
    fetchLesson(lessonNumber)
  }, [lessonNumber])

  const handleExerciseComplete = (isCorrect: boolean) => {
    setTimeout(() => {
      if (currentExercise + 1 < currentLesson.exercises.length) {
        setCurrentExercise((prev) => prev + 1)
        // Update progress based on words completed
        const totalWords = currentLesson.exercises.length
        const wordsCompleted = currentExercise + 1
        setProgress((wordsCompleted * 100) / totalWords)
      } else {
        setLessonComplete(true)
        setProgress(100) // Ensure the progress bar is full when lesson is complete
      }
    }, 1500)
  }

  const handleStartNewLesson = () => {
    setCurrentExercise(0)
    setLessonComplete(false)
    setProgress(0)
    setLessonNumber((prev) => prev + 1)
  }

  if (!currentLesson) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0f0f0f]">
        <div className="text-zinc-300 animate-pulse">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
      <Header lessonNumber={lessonNumber} />
      <main className="max-w-4xl mx-auto p-4">
        <div className="flex justify-between items-center mb-4">
          <Link href="/" className="text-zinc-400 hover:text-blue-400 flex items-center gap-1 transition-colors">
            <ArrowLeft size={16} />
            <span>Back to Home</span>
          </Link>
        </div>
        <div className="card">
          <div className="p-6">
            <div className="progress-container mb-6">
              <div className="progress-bar" style={{ width: `${progress}%` }}></div>
            </div>

            {!lessonComplete ? (
              <>
                <LessonContent currentLesson={currentLesson} currentExercise={currentExercise} />

                {currentExercise >= 2 && (
                  <ExerciseSection
                    exercise={currentLesson.exercises[currentExercise - 2]}
                    onComplete={handleExerciseComplete}
                  />
                )}

                <div className="flex justify-between mt-6">
                  <button
                    className="btn btn-outline"
                    onClick={() => setCurrentExercise((prev) => Math.max(0, prev - 1))}
                    disabled={currentExercise === 0}
                  >
                    Previous
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      setCurrentExercise((prev) => {
                        const newExercise = prev + 1
                        // Update progress when moving through content
                        if (newExercise >= 2) {
                          const totalWords = currentLesson.exercises.length
                          const wordsCompleted = Math.min(newExercise - 2, totalWords)
                          setProgress((wordsCompleted * 100) / totalWords)
                        }
                        return newExercise
                      })
                    }}
                    disabled={currentExercise >= currentLesson.exercises.length + 2}
                  >
                    Next
                  </button>
                </div>
              </>
            ) : (
              <LessonComplete onStartNewLesson={handleStartNewLesson} />
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
