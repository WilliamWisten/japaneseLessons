import Link from "next/link"

interface HeaderProps {
  lessonNumber: number | null
}

export function Header({ lessonNumber }: HeaderProps) {
  return (
    <header className="border-b border-zinc-800 bg-black/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-baseline justify-between">
          <div>
            <Link
              href="/"
              className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400 hover:opacity-90 transition-opacity"
            >
              Japanese Tutor
            </Link>
            {lessonNumber && <p className="text-zinc-400 mt-1">Lesson {lessonNumber}</p>}
          </div>
        </div>
      </div>
    </header>
  )
}
