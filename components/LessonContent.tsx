import { useState } from 'react';
import { LessonData } from '@/lib/api';

interface LessonItem {
  type: string
  category: string
  concept: string
  data: {
    reading: string
    meaning: string
  }
}

interface Lesson {
  review: LessonItem[]
  new_content: LessonItem[]
  exercises: Array<{
    type: string
    category: string
    question: string
    options: string[]
    correct: string
  }>
  duration: number
}

interface LessonContentProps {
  lesson: LessonData;
  onComplete: (score: number, exerciseResults: Array<{
    word: string;
    is_correct: boolean;
    question: string;
  }>) => void;
}

export function LessonContent({ lesson, onComplete }: LessonContentProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [showingHiragana, setShowingHiragana] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [exerciseResults, setExerciseResults] = useState<Array<{
    word: string;
    is_correct: boolean;
    question: string;
  }>>([]);

  if (!lesson || !lesson.exercises || lesson.exercises.length === 0) {
    return <div className="text-center text-zinc-400">No lesson content available</div>;
  }

  const currentQuestion = lesson.exercises[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / lesson.exercises.length) * 100;

  const handleAnswer = (answer: string) => {
    if (isAnswered) return;

    const isCorrect = answer === currentQuestion.correct;
    setSelectedAnswer(answer);
    setIsAnswered(true);

    if (isCorrect) {
      setCorrectAnswers(prev => prev + 1);
    }

    // Record exercise result
    setExerciseResults(prev => [...prev, {
      word: currentQuestion.word,
      is_correct: isCorrect,
      question: currentQuestion.question
    }]);
  };

  const handleNext = () => {
    if (currentQuestionIndex === lesson.exercises.length - 1) {
      // Lesson complete
      const score = Math.round((correctAnswers / lesson.exercises.length) * 100);
      onComplete(score, exerciseResults);
    } else {
      setCurrentQuestionIndex(prev => prev + 1);
      setSelectedAnswer(null);
      setIsAnswered(false);
      setShowingHiragana(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Progress bar */}
      <div className="w-full bg-zinc-800 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Question card */}
      <div className="card glass-card animate-fade-in p-6">
        {/* Word display */}
        <div className="flex items-center justify-center space-x-4 mb-8">
          <h2 className="text-4xl font-bold text-center">
            {showingHiragana ? currentQuestion.reading : currentQuestion.word}
          </h2>
          <button
            onClick={() => setShowingHiragana(!showingHiragana)}
            className="p-2 rounded-full hover:bg-zinc-700 transition-colors"
          >
            <span className="sr-only">Toggle reading</span>
            👁️
          </button>
          {currentQuestion.audio_url && (
            <button
              onClick={() => new Audio(currentQuestion.audio_url).play()}
              className="p-2 rounded-full hover:bg-zinc-700 transition-colors"
            >
              <span className="sr-only">Play audio</span>
              🔊
            </button>
          )}
        </div>

        {/* Question */}
        <p className="text-lg text-center mb-8 text-zinc-300">
          {currentQuestion.question}
        </p>

        {/* Options */}
        <div className="grid gap-4">
          {currentQuestion.options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleAnswer(option)}
              disabled={isAnswered}
              className={`
                p-4 rounded-lg text-left transition-all
                ${isAnswered
                  ? option === currentQuestion.correct
                    ? 'bg-green-500/20 border-green-500'
                    : option === selectedAnswer
                      ? 'bg-red-500/20 border-red-500'
                      : 'bg-zinc-800 border-transparent opacity-50'
                  : 'bg-zinc-800 hover:bg-zinc-700 border-transparent'
                }
                ${selectedAnswer === option ? 'border-2' : 'border-2'}
              `}
            >
              {option}
            </button>
          ))}
        </div>

        {/* Feedback */}
        {isAnswered && (
          <div className="mt-8 space-y-4">
            {currentQuestion.context && (
              <div className="text-sm space-y-2">
                <p className="text-zinc-400">{currentQuestion.context}</p>
                {currentQuestion.context_en && (
                  <p className="text-zinc-500 italic">{currentQuestion.context_en}</p>
                )}
              </div>
            )}
            <button
              onClick={handleNext}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 rounded-lg transition-colors"
            >
              {currentQuestionIndex === lesson.exercises.length - 1 ? 'Complete Lesson' : 'Next Question'}
            </button>
          </div>
        )}
      </div>

      {/* Question counter */}
      <p className="text-center text-sm text-zinc-500">
        Question {currentQuestionIndex + 1} of {lesson.exercises.length}
      </p>
    </div>
  );
}
