import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface LessonData {
    exercises: Array<{
        type: string;
        word: string;
        reading: string;
        meaning: string;
        question: string;
        options: string[];
        correct: string;
        context?: string;
        context_en?: string;
        audio_url?: string;
    }>;
    lesson_number?: number;
    episode_number?: number;
}

export interface ProgressData {
    lesson_number?: number;
    lesson_id?: string;
    completed: boolean;
    score: number;
    questions_total: number;
    questions_correct: number;
    timestamp: any;
    exercises: Array<{
        word: string;
        is_correct: boolean;
        question: string;
    }>;
}

export interface PodcastData {
    id: string;
    name: string;
    show_name: string;
    show_publisher: string;
    description: string;
    release_date: string;
    vocabulary_items: Array<{
        word: string;
        reading: string;
        meaning: string;
        audio_url?: string;
    }>;
}

export const api = {
    // Get a regular lesson
    getLesson: async (userId: string, lessonNumber: number = 1): Promise<LessonData> => {
        const response = await axios.get(`${API_BASE_URL}/lesson`, {
            params: { user_id: userId, lesson_number: lessonNumber }
        });
        return response.data;
    },

    // Get a podcast lesson
    getPodcastLesson: async (userId: string, episodeId: string): Promise<LessonData> => {
        const response = await axios.get(`${API_BASE_URL}/podcast-lesson`, {
            params: { user_id: userId, episode_id: episodeId }
        });
        return response.data;
    },

    // Process a Spotify podcast
    processSpotifyPodcast: async (userId: string, spotifyUrl: string) => {
        const response = await axios.post(`${API_BASE_URL}/process-spotify-podcast`, {
            user_id: userId,
            spotify_url: spotifyUrl
        });
        return response.data;
    },

    // Save lesson progress
    saveProgress: async (userId: string, data: ProgressData, lessonType: 'regular' | 'podcast' = 'regular') => {
        const response = await axios.post(`${API_BASE_URL}/progress`, {
            user_id: userId,
            lesson_type: lessonType,
            data
        });
        return response.data;
    },

    // Get all processed podcasts
    getPodcasts: async (userId?: string): Promise<PodcastData[]> => {
        const response = await axios.get(`${API_BASE_URL}/podcasts`, {
            params: userId ? { user_id: userId } : undefined
        });
        return response.data.podcasts;
    }
}; 