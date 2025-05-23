"use client"
import { Header } from "@/components/Header"
import Link from "next/link"
import { useAuth } from "@/components/AuthProvider"

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[#0f0f0f] bg-gradient-to-b from-black to-zinc-900">
      <Header lessonNumber={null} />
      <main className="max-w-4xl mx-auto p-4">
        <div className="card mt-8 overflow-hidden">
          <div className="card-content p-8 text-center">
            <h2 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-sky-400 mb-6">
              Welcome to Japanese Tutor
            </h2>
            <p className="text-zinc-300 text-lg mb-8 max-w-2xl mx-auto">
              Your personalized Japanese learning experience. Choose from structured lessons or learn through podcasts.
              {!user && <span className="block mt-2 text-zinc-400">Please log in to access lessons and podcasts.</span>}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
              <div className={`block ${!user && 'opacity-50'}`}>
                <div className="card hover-card p-6 h-full">
                  <h3 className="text-2xl font-bold text-blue-400 mb-3">Structured Lessons</h3>
                  <p className="text-zinc-400 mb-4">Learn Japanese through our carefully designed curriculum</p>
                  <Link href={user ? "/lesson" : "#"} className={`block w-full ${!user && 'pointer-events-none'}`}>
                    <button className="btn btn-primary w-full mt-auto" disabled={!user}>Start Learning</button>
                  </Link>
                </div>
              </div>

              <div className={`block ${!user && 'opacity-50'}`}>
                <div className="card hover-card p-6 h-full">
                  <h3 className="text-2xl font-bold text-blue-400 mb-3">Podcast Library</h3>
                  <p className="text-zinc-400 mb-4">Learn from real Japanese conversations and content</p>
                  <Link href={user ? "/podcasts" : "#"} className={`block w-full ${!user && 'pointer-events-none'}`}>
                    <button className="btn btn-primary w-full mt-auto" disabled={!user}>Browse Podcasts</button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
