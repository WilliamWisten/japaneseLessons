import Link from "next/link"
import Image from "next/image"
import { Play } from "lucide-react"

interface PodcastItemProps {
  podcast: {
    id: number
    title: string
    description: string
    duration: string
    wordsEncountered: number
    totalWords: number
    wordsMastered: number
    imageUrl: string
  }
}

export function PodcastItem({ podcast }: PodcastItemProps) {
  const encounterPercentage = (podcast.wordsEncountered / podcast.totalWords) * 100
  const masteredPercentage = (podcast.wordsMastered / podcast.totalWords) * 100

  // No level colors needed since we're removing the badges

  return (
    <div className="card glass-card hover-card transition-all">
      <div className="p-4">
        <div className="flex gap-4">
          <div className="flex-shrink-0 relative group">
            <Image
              src={podcast.imageUrl || "/placeholder.svg"}
              alt={podcast.title}
              width={80}
              height={80}
              className="rounded-md object-cover"
            />
            <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-md">
              <Play className="w-8 h-8 text-white" />
            </div>
          </div>

          <div className="flex-1">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-semibold text-zinc-100">{podcast.title}</h3>
                <p className="text-zinc-400 text-sm">{podcast.description}</p>
              </div>
              <div className="text-right text-sm">
                <div className="text-zinc-400">{podcast.duration}</div>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-zinc-400">Words Encountered</span>
                  <span className="text-zinc-300">
                    {podcast.wordsEncountered}/{podcast.totalWords}
                  </span>
                </div>
                <div className="progress-container h-2">
                  <div className="progress-bar" style={{ width: `${encounterPercentage}%` }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-zinc-400">Words Mastered</span>
                  <span className="text-zinc-300">
                    {podcast.wordsMastered}/{podcast.totalWords}
                  </span>
                </div>
                <div className="progress-container h-2">
                  <div className="progress-bar-green" style={{ width: `${masteredPercentage}%` }}></div>
                </div>
              </div>
            </div>

            <div className="mt-4">
              <Link href={`/podcasts/${podcast.id}`}>
                <button className="btn btn-primary">Start Lesson</button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
