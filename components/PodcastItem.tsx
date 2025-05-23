import Link from "next/link"
import Image from "next/image"
import { Play, Loader2, AlertCircle } from "lucide-react"
import { api } from "@/lib/api"
import { useState } from "react"

interface PodcastItemProps {
  podcast: {
    id: string
    title: string
    description: string
    duration: string
    wordsEncountered: number
    totalWords: number
    wordsMastered: number
    imageUrl: string
    status: 'queued' | 'processing' | 'completed' | 'error'
    error?: string
    show_name: string
    show_publisher: string
    release_date: string
  }
  onRefresh: () => void
}

export function PodcastItem({ podcast, onRefresh }: PodcastItemProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const encounterPercentage = (podcast.wordsEncountered / podcast.totalWords) * 100
  const masteredPercentage = (podcast.wordsMastered / podcast.totalWords) * 100

  const handleStartProcessing = async () => {
    try {
      setIsProcessing(true)
      setError(null)
      await api.processQueue(1) // Process one item at a time
      await onRefresh() // Refresh the list after processing
    } catch (err) {
      console.error('Error processing podcast:', err)
      setError('Failed to process podcast. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const getStatusDisplay = () => {
    switch (podcast.status) {
      case 'queued':
        return {
          text: 'Queued for processing',
          color: 'text-yellow-400',
          icon: <Loader2 className="w-4 h-4 animate-spin" />
        }
      case 'processing':
        return {
          text: 'Processing...',
          color: 'text-blue-400',
          icon: <Loader2 className="w-4 h-4 animate-spin" />
        }
      case 'completed':
        return {
          text: 'Ready',
          color: 'text-green-400',
          icon: <Play className="w-4 h-4" />
        }
      case 'error':
        return {
          text: 'Error',
          color: 'text-red-400',
          icon: <AlertCircle className="w-4 h-4" />
        }
      default:
        return {
          text: 'Unknown',
          color: 'text-zinc-400',
          icon: null
        }
    }
  }

  const status = getStatusDisplay()

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
            {podcast.status === 'completed' && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-md">
                <Play className="w-8 h-8 text-white" />
              </div>
            )}
          </div>

          <div className="flex-1">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-semibold text-zinc-100">{podcast.title}</h3>
                <div className="text-zinc-400 text-sm mb-1">
                  <span>{podcast.show_name}</span>
                  {podcast.show_publisher && (
                    <>
                      <span className="mx-1">•</span>
                      <span>{podcast.show_publisher}</span>
                    </>
                  )}
                  {podcast.release_date && (
                    <>
                      <span className="mx-1">•</span>
                      <span>{new Date(podcast.release_date).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
                <p className="text-zinc-400 text-sm line-clamp-2">{podcast.description}</p>
              </div>
              <div className="text-right text-sm">
                <div className="text-zinc-400">{podcast.duration}</div>
                <div className={`flex items-center gap-1 mt-1 ${status.color}`}>
                  {status.icon}
                  <span>{status.text}</span>
                </div>
              </div>
            </div>

            {podcast.status === 'queued' && (
              <div className="mt-4">
                <button
                  onClick={handleStartProcessing}
                  disabled={isProcessing}
                  className="btn btn-primary w-full"
                >
                  {isProcessing ? 'Processing...' : 'Start Processing'}
                </button>
                {error && (
                  <p className="text-sm text-red-400 mt-2">{error}</p>
                )}
              </div>
            )}

            {podcast.status === 'completed' && (
              <>
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
              </>
            )}

            {podcast.status === 'error' && podcast.error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-md">
                <p className="text-sm text-red-400">{podcast.error}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
