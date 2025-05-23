from flask import Flask, jsonify, request
from flask_cors import CORS
from grok_enhanced_tutor import JapaneseTutor
from firebase_config import FirebaseManager
from podcast_processor import PodcastProcessor
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

firebase = FirebaseManager()
tutor = JapaneseTutor(
    api_key=os.getenv('OPENAI_API_KEY'),
    firebase_manager=firebase,
    api_provider="openai"
)
podcast_processor = PodcastProcessor(os.getenv('OPENAI_API_KEY'))

@app.route('/lesson', methods=['GET'])
def get_lesson():
    user_id = request.args.get('user_id', default='default_user', type=str)
    lesson_number = request.args.get('lesson_number', default=1, type=int)
    lesson = tutor.create_lesson(user_id, lesson_number)
    return jsonify(lesson)

@app.route('/podcast-lesson', methods=['GET'])
def get_podcast_lesson():
    user_id = request.args.get('user_id', default='default_user', type=str)
    episode_number = request.args.get('episode_number', default=1, type=int)
    lesson = tutor.create_podcast_lesson(user_id, episode_number)
    return jsonify(lesson)

@app.route('/process-spotify-podcast', methods=['POST'])
def process_spotify_podcast():
    user_id = request.json.get('user_id', 'default_user')
    spotify_url = request.json.get('spotify_url')
    
    if not spotify_url:
        return jsonify({"error": "Missing spotify_url parameter"}), 400
    
    try:
        # Process the podcast
        result = podcast_processor.process_spotify_episode(spotify_url)
        
        # Create a lesson from the processed podcast
        lesson = tutor.create_podcast_lesson(user_id, result['episode_id'])
        
        return jsonify({
            "status": "success",
            "episode_id": result['episode_id'],
            "lesson": lesson
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progress', methods=['POST'])
def save_progress():
    data = request.get_json()
    user_id = data.get('user_id', 'default_user')
    lesson_type = data.get('lesson_type', 'regular')
    tutor.save_lesson_progress(user_id, data, lesson_type)
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(debug=True)