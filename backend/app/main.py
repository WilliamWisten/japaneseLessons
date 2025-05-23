from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from grok_enhanced_tutor import JapaneseTutor
from firebase_config import FirebaseManager
from podcast_processor import PodcastProcessor
from dotenv import load_dotenv
import os
from typing import Optional
from pydantic import BaseModel
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # More permissive for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
firebase = FirebaseManager()
tutor = JapaneseTutor(
    api_key=os.getenv('OPENAI_API_KEY'),
    firebase_manager=firebase,
    api_provider="openai"
)
podcast_processor = PodcastProcessor(os.getenv('OPENAI_API_KEY'))

# Request models
class SpotifyPodcastRequest(BaseModel):
    user_id: str = "default_user"
    spotify_url: str

class ProgressRequest(BaseModel):
    user_id: str = "default_user"
    lesson_type: str = "regular"
    data: dict

@app.get("/lesson")
async def get_lesson(user_id: str = "default_user", lesson_number: int = 1):
    lesson = tutor.create_lesson(user_id, lesson_number)
    return lesson

@app.get("/podcast-lesson")
async def get_podcast_lesson(user_id: str = "default_user", episode_id: str = None):
    if not episode_id:
        raise HTTPException(status_code=400, detail="Missing episode_id parameter")
    lesson = tutor.create_podcast_lesson(user_id, episode_id)
    return lesson

@app.post("/process-spotify-podcast")
async def process_spotify_podcast(request: SpotifyPodcastRequest):
    if not request.spotify_url:
        raise HTTPException(status_code=400, detail="Missing spotify_url parameter")
    
    try:
        # Only process the podcast, don't create a lesson yet
        result = podcast_processor.process_spotify_episode(request.spotify_url)
        
        return {
            "status": "success",
            "episode_id": result['episode_id']
        }
    except Exception as e:
        logger.error(f"Error processing podcast: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/progress")
async def save_progress(request: ProgressRequest):
    try:
        # Save overall lesson progress
        tutor.save_lesson_progress(request.user_id, request.data, request.lesson_type)
        
        # Update progress for each word
        for exercise in request.data.get('exercises', []):
            if 'word' in exercise and 'is_correct' in exercise:
                # Determine question type (meaning or reading)
                question_type = 'reading' if 'read' in exercise['question'].lower() else 'meaning'
                tutor.update_word_progress(
                    request.user_id,
                    exercise['word'],
                    exercise['is_correct'],
                    question_type
                )
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/podcasts")
async def get_podcasts(user_id: str = None):
    """Get all processed podcasts"""
    try:
        podcasts = []
        podcast_docs = firebase.db.collection('podcast_lessons').stream()
        
        # Get user's word progress if user_id is provided
        encountered_words = set()
        mastered_words = set()
        if user_id:
            # Get encountered words
            word_progress_docs = firebase.db.collection('users').document(user_id).collection('word_progress').stream()
            encountered_words = {doc.id for doc in word_progress_docs}
            
            # Get mastered words - a word is mastered if it has been correctly answered 5 times in a row
            mastered_docs = firebase.db.collection('users').document(user_id).collection('word_progress').stream()
            for doc in mastered_docs:
                data = doc.to_dict()
                if data.get('meaning_correct_streak', 0) >= 5:
                    mastered_words.add(doc.id)
        
        for doc in podcast_docs:
            data = doc.to_dict()
            if data:
                data['id'] = doc.id
                vocab_items = data.get('vocabulary_items', [])
                vocab_words = {item['word'] for item in vocab_items}
                
                # Calculate encountered and mastered words for this podcast
                data['wordsEncountered'] = len(vocab_words & encountered_words) if user_id else 0
                data['wordsMastered'] = len(vocab_words & mastered_words) if user_id else 0
                data['totalWords'] = len(vocab_items)
                
                podcasts.append(data)
                
        return {"podcasts": podcasts}
    except Exception as e:
        logger.error(f"Error getting podcasts: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 