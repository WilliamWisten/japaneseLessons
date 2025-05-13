interface LessonContentProps {
  currentLesson: any
  currentExercise: number
}

export function LessonContent({ currentLesson, currentExercise }: LessonContentProps) {
  return (
    <div className="space-y-6">
      {currentExercise === 0 && (
        <div className="card glass-card animate-fade-in">
          <div className="card-header">
            <h3 className="card-title text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400">
              Review
            </h3>
          </div>
          <div className="card-content">
            {currentLesson.review.map((item: any, index: number) => (
              <div key={index} className="mb-4 last:mb-0">
                <p className="text-4xl font-bold mb-4">{item.concept}</p>
                <div className="space-y-2 text-zinc-400">
                  <p className="flex items-center">
                    <span className="text-xs uppercase tracking-wider mr-2">Reading:</span>
                    <span className="text-zinc-200">{item.data.reading}</span>
                  </p>
                  <p className="flex items-center">
                    <span className="text-xs uppercase tracking-wider mr-2">Meaning:</span>
                    <span className="text-zinc-200">{item.data.meaning}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentExercise === 1 && (
        <div className="card glass-card animate-fade-in">
          <div className="card-header">
            <h3 className="card-title text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400">
              New Content
            </h3>
          </div>
          <div className="card-content">
            {currentLesson.new_content.map((item: any, index: number) => (
              <div key={index} className="mb-4 last:mb-0">
                <p className="text-4xl font-bold mb-4">{item.concept}</p>
                <div className="space-y-2 text-zinc-400">
                  <p className="flex items-center">
                    <span className="text-xs uppercase tracking-wider mr-2">Reading:</span>
                    <span className="text-zinc-200">{item.data.reading}</span>
                  </p>
                  <p className="flex items-center">
                    <span className="text-xs uppercase tracking-wider mr-2">Meaning:</span>
                    <span className="text-zinc-200">{item.data.meaning}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
