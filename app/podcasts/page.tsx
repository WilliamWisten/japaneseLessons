"use client"

import { useState } from "react"
import { Header } from "@/components/Header"
import { PodcastItem } from "@/components/PodcastItem"
import Link from "next/link"
import { ArrowLeft, Plus, X } from "lucide-react"

// Sample podcast data
const samplePodcasts = [
  {
    id: 1,
    title: "Daily Japanese Conversation",
    description: "Learn everyday Japanese phrases and vocabulary",
    duration: "24:15",
    wordsEncountered: 45,
    totalWords: 60,
    wordsMastered: 32,
    imageUrl: "/placeholder.svg?key=b6ra4",
  },
  {
    id: 2,
    title: "Japanese Culture Talk",
    description: "Discussions about Japanese traditions and modern culture",
    duration: "32:40",
    wordsEncountered: 78,
    totalWords: 120,
    wordsMastered: 45,
    imageUrl: "/placeholder.svg?key=wu21u",
  },
  {
    id: 3,
    title: "Business Japanese",
    description: "Essential vocabulary for professional settings",
    duration: "18:50",
    wordsEncountered: 95,
    totalWords: 95,
    wordsMastered: 80,
    imageUrl: "/placeholder.svg?key=hyyys",
  },
]

export default function PodcastLibrary() {
  const [podcasts, setPodcasts] = useState(samplePodcasts)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newPodcastUrl, setNewPodcastUrl] = useState("")

  const handleAddPodcast = () => {
    if (!newPodcastUrl.trim()) return

    // In a real app, you would process the podcast URL here
    // For now, we'll just add a dummy podcast
    const newPodcast = {
      id: podcasts.length + 1,
      title: `New Podcast ${podcasts.length + 1}`,
      description: "Recently added podcast",
      duration: "20:00",
      wordsEncountered: 0,
      totalWords: 50,
      wordsMastered: 0,
      imageUrl: "/placeholder.svg?key=44of6",
    }

    setPodcasts([...podcasts, newPodcast])
    setNewPodcastUrl("")
    setShowAddForm(false)
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
      <Header lessonNumber={null} />
      <main className="max-w-4xl mx-auto p-4">
        <div className="flex justify-between items-center mb-4">
          <Link href="/" className="text-zinc-400 hover:text-blue-400 flex items-center gap-1 transition-colors">
            <ArrowLeft size={16} />
            <span>Back to Home</span>
          </Link>
        </div>

        <div className="card mb-6">
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400">
                Podcast Library
              </h2>
              <button
                className={`btn ${showAddForm ? "btn-outline" : "btn-primary"} flex items-center gap-1`}
                onClick={() => setShowAddForm(!showAddForm)}
              >
                {showAddForm ? (
                  <>
                    <X size={16} /> Cancel
                  </>
                ) : (
                  <>
                    <Plus size={16} /> Add Podcast
                  </>
                )}
              </button>
            </div>

            {showAddForm && (
              <div className="card glass-card p-4 mb-6 animate-fade-in">
                <h3 className="text-lg font-semibold mb-3 text-zinc-200">Add New Podcast</h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter podcast URL"
                    className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    value={newPodcastUrl}
                    onChange={(e) => setNewPodcastUrl(e.target.value)}
                  />
                  <button className="btn btn-primary" onClick={handleAddPodcast}>
                    Add
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-4">
              {podcasts.map((podcast) => (
                <PodcastItem key={podcast.id} podcast={podcast} />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
