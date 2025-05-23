"use client"

import { CheckCircle, XCircle } from "lucide-react"

interface ExerciseSectionProps {
  exercise: {
    question: string
    options: string[]
    correct: string
  }
  onAnswer: (answer: string, correct: boolean) => void
  selectedAnswer: string | null
}

export function ExerciseSection({ exercise, onAnswer, selectedAnswer }: ExerciseSectionProps) {
  const handleAnswerSubmit = (answer: string) => {
    const isCorrect = answer === exercise.correct
    onAnswer(answer, isCorrect)
  }

  return (
    <div className="card glass-card animate-fade-in">
      <div className="card-header">
        <h3 className="card-title text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400">Exercise</h3>
      </div>
      <div className="card-content">
        <p className="mb-6 text-lg">{exercise.question}</p>
        <div className="grid grid-cols-2 gap-4">
          {exercise.options.map((option: string, index: number) => {
            const isSelected = selectedAnswer === option
            const isCorrect = option === exercise.correct

            let buttonClass = "btn btn-outline h-16 text-lg hover:bg-zinc-800"

            if (selectedAnswer !== null) {
              if (isSelected && isCorrect) {
                buttonClass = "btn h-16 text-lg bg-emerald-900/30 border-emerald-700 text-emerald-400"
              } else if (isSelected && !isCorrect) {
                buttonClass = "btn h-16 text-lg bg-red-900/30 border-red-700 text-red-400"
              } else if (isCorrect) {
                buttonClass = "btn h-16 text-lg bg-emerald-900/30 border-emerald-700 text-emerald-400"
              }
            }

            return (
              <button
                key={index}
                onClick={() => handleAnswerSubmit(option)}
                className={buttonClass}
                disabled={selectedAnswer !== null}
              >
                {option}
                {selectedAnswer !== null && isCorrect && <CheckCircle className="ml-2 h-5 w-5 text-emerald-400" />}
                {selectedAnswer === option && !isCorrect && <XCircle className="ml-2 h-5 w-5 text-red-400" />}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
