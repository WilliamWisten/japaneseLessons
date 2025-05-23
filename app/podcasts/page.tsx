"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/Header"
import { PodcastItem } from "@/components/PodcastItem"
import Link from "next/link"
import { ArrowLeft, Plus, X, RefreshCw } from "lucide-react"
import { useAuth } from "@/components/AuthProvider"
import { api, PodcastData } from "@/lib/api"

export default function PodcastLibrary() {
  const { user } = useAuth();
  const [podcasts, setPodcasts] = useState<PodcastData[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPodcastUrl, setNewPodcastUrl] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (!user) return;
    loadPodcasts();
  }, [user]);

  const loadPodcasts = async () => {
    try {
      setError(null);
      const podcastData = await api.getPodcasts(user?.uid);
      setPodcasts(podcastData);
    } catch (err) {
      console.error('Error loading podcasts:', err);
      setError('Failed to load podcasts. Please try again.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadPodcasts();
  };

  const handleAddPodcast = async () => {
    if (!newPodcastUrl.trim() || !user) return;

    try {
      setIsProcessing(true);
      setError(null);
      await api.processSpotifyPodcast(user.uid, newPodcastUrl);
      await loadPodcasts(); // Refresh the list
      setNewPodcastUrl("");
      setShowAddForm(false);
    } catch (err) {
      console.error('Error adding podcast:', err);
      setError('Failed to add podcast. Please check the URL and try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
        <Header lessonNumber={null} />
        <div className="max-w-4xl mx-auto p-4 text-center">
          <p className="text-zinc-400 mt-8">Please log in to access podcasts.</p>
        </div>
      </div>
    );
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
              <div className="flex gap-2">
                <button
                  className="btn btn-outline flex items-center gap-1"
                  onClick={handleRefresh}
                  disabled={isRefreshing || isProcessing}
                >
                  <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
                  {isRefreshing ? 'Refreshing...' : 'Refresh'}
                </button>
                <button
                  className={`btn ${showAddForm ? "btn-outline" : "btn-primary"} flex items-center gap-1`}
                  onClick={() => setShowAddForm(!showAddForm)}
                  disabled={isProcessing}
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
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 mb-4 text-red-400">
                {error}
              </div>
            )}

            {showAddForm && (
              <div className="card glass-card p-4 mb-6 animate-fade-in">
                <h3 className="text-lg font-semibold mb-3 text-zinc-200">Add New Podcast</h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter Spotify podcast episode URL"
                    className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    value={newPodcastUrl}
                    onChange={(e) => setNewPodcastUrl(e.target.value)}
                    disabled={isProcessing}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handleAddPodcast}
                    disabled={isProcessing}
                  >
                    {isProcessing ? 'Processing...' : 'Add'}
                  </button>
                </div>
                <p className="text-sm text-zinc-500 mt-2">
                  Paste a Spotify podcast episode URL to add it to your library
                </p>
              </div>
            )}

            {isLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                <p className="text-zinc-400 mt-4">Loading podcasts...</p>
              </div>
            ) : podcasts.length === 0 ? (
              <div className="text-center py-8 text-zinc-400">
                <p>No podcasts added yet. Add your first podcast to get started!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {podcasts.map((podcast) => (
                  <PodcastItem
                    key={podcast.id}
                    podcast={{
                      id: podcast.id,
                      title: podcast.name,
                      description: podcast.description,
                      duration: "N/A",
                      show_name: podcast.show_name,
                      show_publisher: podcast.show_publisher || "Unknown",
                      release_date: podcast.release_date,
                      totalWords: podcast.totalWords,
                      wordsEncountered: podcast.wordsEncountered,
                      wordsMastered: podcast.wordsMastered,
                      imageUrl: podcast.image_url || "/placeholder.svg",
                      status: 'completed'
                    }}
                    onRefresh={handleRefresh}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
