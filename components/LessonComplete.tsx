"use client"
import { Sparkles } from "lucide-react"

interface LessonCompleteProps {
  onStartNewLesson: () => void
}

export function LessonComplete({ onStartNewLesson }: LessonCompleteProps) {
  return (
    <div className="card glass-card text-center animate-fade-in">
      <div className="card-header">
        <h3 className="card-title text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400 flex items-center justify-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-400" />
          Lesson Complete!
        </h3>
      </div>
      <div className="card-content">
        <p className="mb-6 text-lg text-zinc-400">Congratulations on finishing the lesson!</p>
        <button onClick={onStartNewLesson} className="btn btn-primary text-lg px-8 py-3">
          Start New Lesson
        </button>
      </div>
    </div>
  )
}
