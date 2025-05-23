import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from datetime import datetime
import sqlite3
import requests
from collections import defaultdict
import re
import time
from firebase_admin import firestore
from google.cloud import texttospeech
import base64
import os
import urllib.parse
import random

@dataclass
class VocabularyItem:
    word: str
    reading: str
    meaning: str
    frequency_rank: Optional[int] = None
    context: Optional[str] = None
    audio_url: Optional[str] = None

class JapaneseTutor:
    def __init__(self, api_key: str, firebase_manager, api_provider: Literal["openai", "deepseek"] = "openai"):
        self.api_key = api_key
        self.firebase = firebase_manager
        self.api_provider = api_provider
        self.tts_client = None
        try:
            self.tts_client = texttospeech.TextToSpeechClient()
        except Exception as e:
            print(f"Warning: Could not initialize Text-to-Speech client: {e}")
        
    def call_api(self, prompt: str) -> str:
        """Call API with proper error handling and retries"""
        print("\nCalling API...")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.api_provider == "openai":
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            api_url = "https://api.openai.com/v1/chat/completions"
        else:  # deepseek
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            api_url = "https://api.deepseek.com/v1/chat/completions"
        
        max_retries = 3
        timeout = 30
        
        for attempt in range(max_retries):
            try:
                print(f"API attempt {attempt + 1}/{max_retries}")
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 5))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                if response.status_code != 200:
                    print(f"API error: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    raise Exception(f"API error: {response.text}")
                
                content = response.json()["choices"][0]["message"]["content"]
                print(f"API call successful, got response of length: {len(content)}")
                return content
                
            except requests.exceptions.Timeout:
                print(f"Timeout occurred on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise Exception(f"API timeout after {max_retries} attempts")
                print(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"API request failed: {str(e)}")
                print(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)

    def get_user_mastered_words(self, user_id: str) -> set:
        """Get set of words mastered by the user"""
        mastered_docs = (self.firebase.db.collection('users')
                        .document(user_id)
                        .collection('mastered_words')
                        .stream())
        return {doc.id for doc in mastered_docs}

    def record_word_mastery(self, user_id: str, word: str, source: str):
        """Record a word as mastered by the user"""
        # First, find the word's document by querying
        word_query = (self.firebase.db.collection('frequency_dictionary')
                     .where('word', '==', word)
                     .limit(1)
                     .stream())
        
        try:
            word_doc = next(word_query)
            word_data = word_doc.to_dict()
        except StopIteration:
            # If not found by 'word' field, try direct document lookup
            word_doc = self.firebase.db.collection('frequency_dictionary').document(word).get()
            if not word_doc.exists:
                print(f"Warning: Word '{word}' not found in frequency dictionary")
                return
            word_data = word_doc.to_dict()
        
        # Save mastery record using actual word
        self.firebase.db.collection('users')\
            .document(user_id)\
            .collection('mastered_words')\
            .document(word)\
            .set({
                'mastered_date': firestore.SERVER_TIMESTAMP,
                'source': source,
                'review_count': 0,
                'reading': word_data.get('reading', ''),
                'meaning': word_data.get('meaning', '')
            })

    def get_next_words_to_learn(self, user_id: str, count: int = 5) -> List[VocabularyItem]:
        """Get next words to learn based on frequency, user's mastery, and learning progress"""
        # Get mastered words
        mastered_words = self.get_user_mastered_words(user_id)
        print(f"User has mastered {len(mastered_words)} words")
        
        # Get user's word progress
        current_time = datetime.now().timestamp()
        cutoff_time = current_time - (24 * 60 * 60)  # 24 hours ago
        
        # Get all word progress
        progress_ref = (self.firebase.db.collection('users')
                       .document(user_id)
                       .collection('word_progress')
                       .stream())
        
        word_progress = {}
        recent_words = set()
        
        for doc in progress_ref:
            data = doc.to_dict()
            # Convert Firestore timestamp to Unix timestamp if it exists
            last_seen = data.get('last_seen')
            if hasattr(last_seen, 'timestamp'):
                last_seen = last_seen.timestamp()
                # Check if word was used recently
                if last_seen > cutoff_time:
                    recent_words.add(doc.id)
            elif not last_seen:
                last_seen = 0
                
            word_progress[doc.id] = {
                'total_meaning_attempts': data.get('total_meaning_attempts', 0),
                'meaning_correct_count': data.get('meaning_correct_count', 0),
                'meaning_correct_streak': data.get('meaning_correct_streak', 0),
                'total_reading_attempts': data.get('total_reading_attempts', 0),
                'reading_correct_count': data.get('reading_correct_count', 0),
                'reading_correct_streak': data.get('reading_correct_streak', 0),
                'last_seen': last_seen
            }
        
        print(f"Found {len(recent_words)} recently used words to exclude")
        
        # Keep track of seen words to avoid duplicates
        seen_words = set()
        words = []
        last_rank = 0
        batch_size = 50  # Process words in batches
        
        while len(words) < count and last_rank < 5000:  # Limit to first 5000 most frequent words
            # Get next batch of words ordered by frequency_rank
            words_ref = (self.firebase.db.collection('frequency_dictionary')
                        .where('frequency_rank', '>', last_rank)
                        .order_by('frequency_rank')
                        .limit(batch_size))
            
            batch = list(words_ref.stream())
            if not batch:
                break
            
            for doc in batch:
                data = doc.to_dict()
                # Use document ID as word if 'word' field is missing
                actual_word = data.get('word', doc.id)
                current_rank = data.get('frequency_rank', float('inf'))
                
                # Update last_rank for next iteration
                last_rank = current_rank
                
                # Skip if we've seen this word before (avoid duplicates)
                if actual_word in seen_words:
                    continue
                seen_words.add(actual_word)
                
                # Skip if word was used recently
                if actual_word in recent_words:
                    print(f"Skipping recently used word: {actual_word}")
                    continue
                
                if actual_word not in mastered_words:
                    # Calculate word score based on detailed learning progress
                    progress = word_progress.get(actual_word, {})
                    
                    # Calculate separate accuracy rates for meaning and reading
                    meaning_attempts = progress.get('total_meaning_attempts', 0)
                    meaning_correct = progress.get('meaning_correct_count', 0)
                    meaning_accuracy = (meaning_correct / meaning_attempts) if meaning_attempts > 0 else 0
                    
                    reading_attempts = progress.get('total_reading_attempts', 0)
                    reading_correct = progress.get('reading_correct_count', 0)
                    reading_accuracy = (reading_correct / reading_attempts) if reading_attempts > 0 else 0
                    
                    # Calculate time since last practice
                    time_factor = 0
                    if progress.get('last_seen'):
                        days_since_practice = (current_time - progress['last_seen']) / (24 * 60 * 60)
                        # Increase priority for words not practiced in 3-7 days
                        if 3 <= days_since_practice <= 7:
                            time_factor = 500
                    
                    # Base score from frequency
                    score = 1000 - (current_rank / 10)
                    
                    if meaning_attempts == 0 or reading_attempts == 0:
                        # Highest priority for new words
                        score += 2000
                    else:
                        # Priority based on accuracy - focus on words with low accuracy
                        meaning_priority = 1000 * (1 - meaning_accuracy)
                        reading_priority = 1000 * (1 - reading_accuracy)
                        
                        # Give extra weight to the type with lower accuracy
                        score += max(meaning_priority, reading_priority)
                        
                        # Add bonus for words that need practice in both areas
                        if meaning_accuracy < 0.7 and reading_accuracy < 0.7:
                            score += 500
                        
                        # Consider streaks - prioritize words where streaks were recently broken
                        if progress.get('meaning_correct_streak', 0) == 0 and meaning_attempts > 0:
                            score += 300
                        if progress.get('reading_correct_streak', 0) == 0 and reading_attempts > 0:
                            score += 300
                    
                    # Add time factor
                    score += time_factor
                    
                    # Add some randomness to break ties and provide variety
                    score += random.uniform(0, 100)
                    
                    print(f"Word: {actual_word}, Score: {score:.2f} (Meaning acc: {meaning_accuracy:.2f}, Reading acc: {reading_accuracy:.2f}, Attempts: {meaning_attempts}/{reading_attempts})")
                    
                    # Generate audio URL if not present
                    if not data.get('audio_url'):
                        audio_url = self.generate_audio(actual_word)
                        if audio_url:
                            data['audio_url'] = audio_url
                            # Update the frequency dictionary with the audio URL
                            doc.reference.update({'audio_url': audio_url})
                    
                    # Add word to list with its score
                    words.append((score, VocabularyItem(
                        word=actual_word,
                        reading=data.get('reading', ''),
                        meaning=data.get('meaning', ''),
                        audio_url=data.get('audio_url'),
                        frequency_rank=current_rank
                    )))
                    
                    if len(words) >= count:
                        break
        
        print(f"Found {len(words)} candidate words to learn")
        
        # Sort words by score (highest first) and take top count words
        words.sort(key=lambda x: x[0], reverse=True)
        selected_words = [word for score, word in words[:count]]
        
        print(f"Selected {len(selected_words)} words based on learning progress and frequency")
        return selected_words

    def update_word_progress(self, user_id: str, word: str, is_correct: bool, question_type: str):
        """Update progress for a specific word"""
        # Get or create word progress document
        word_ref = (self.firebase.db.collection('users')
                   .document(user_id)
                   .collection('word_progress')
                   .document(word))
        
        word_doc = word_ref.get()
        if word_doc.exists:
            data = word_doc.to_dict()
        else:
            # Get word details from frequency dictionary
            word_details = None
            try:
                word_query = (self.firebase.db.collection('frequency_dictionary')
                            .where('word', '==', word)
                            .limit(1)
                            .stream())
                word_details = next(word_query).to_dict()
            except StopIteration:
                try:
                    word_doc = self.firebase.db.collection('frequency_dictionary').document(word).get()
                    if word_doc.exists:
                        word_details = word_doc.to_dict()
                except:
                    pass
            
            # Initialize new word progress
            data = {
                'word': word,
                'reading': word_details.get('reading', '') if word_details else '',
                'meaning': word_details.get('meaning', '') if word_details else '',
                'meaning_correct_streak': 0,
                'reading_correct_streak': 0,
                'total_meaning_attempts': 0,
                'total_reading_attempts': 0,
                'meaning_correct_count': 0,
                'reading_correct_count': 0,
                'first_seen': firestore.SERVER_TIMESTAMP,
                'last_seen': firestore.SERVER_TIMESTAMP,
                'mastered': False
            }
        
        # Update streaks and counts
        streak_field = f'{question_type}_correct_streak'
        attempts_field = f'total_{question_type}_attempts'
        correct_field = f'{question_type}_correct_count'
        
        if is_correct:
            data[streak_field] = data.get(streak_field, 0) + 1
            data[correct_field] = data.get(correct_field, 0) + 1
        else:
            data[streak_field] = 0
        
        data[attempts_field] = data.get(attempts_field, 0) + 1
        data['last_seen'] = firestore.SERVER_TIMESTAMP
        
        # Check if word should be mastered (3 correct in a row for both meaning and reading)
        if (data.get('meaning_correct_streak', 0) >= 3 and 
            data.get('reading_correct_streak', 0) >= 3 and 
            not data.get('mastered', False)):
            data['mastered'] = True
            data['mastered_date'] = firestore.SERVER_TIMESTAMP
            # Also record in mastered_words collection
            self.record_word_mastery(user_id, word, 'practice')
        
        # Update progress
        word_ref.set(data, merge=True)
        
        return data

    def validate_exercise(self, exercise):
        """Validate that an exercise is properly formatted"""
        required_fields = ['type', 'question', 'correct', 'options']
        for field in required_fields:
            if field not in exercise:
                print(f"Exercise missing required field: {field}")
                return False
                
        if not isinstance(exercise['options'], list):
            print("Exercise options must be a list")
            return False
            
        if len(exercise['options']) != 4:
            print(f"Exercise must have exactly 4 options, got {len(exercise['options'])}")
            return False
            
        if exercise['correct'] not in exercise['options']:
            print("Exercise correct answer not in options")
            return False
            
        return True
        
    def generate_audio(self, text: str, language_code: str = "ja-JP") -> Optional[str]:
        """Generate audio for text and return a Firebase Storage URL"""
        if not self.tts_client:
            print("Text-to-Speech client not initialized")
            return None
            
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name="ja-JP-Neural2-B",  # Using a neural voice for better quality
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.85  # Slightly slower for learning
            )
            
            # Generate audio
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            try:
                # Save to Firebase Storage
                audio_path = f"audio/{base64.urlsafe_b64encode(text.encode()).decode()}.mp3"
                blob = self.firebase.storage.blob(audio_path)
                
                # Upload audio content
                blob.upload_from_string(
                    response.audio_content,
                    content_type='audio/mpeg'
                )
                
                # Make public and get URL
                blob.make_public()
                # Get the public URL directly from the blob
                return blob.public_url
                
            except Exception as storage_error:
                print(f"Storage error details: {storage_error}")
                return None
            
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None

    def create_lesson(self, user_id: str, lesson_number: int = 1) -> Dict:
        """Create a personalized lesson with frequency-based vocabulary"""
        print("\nCreating new lesson...")
        
        # Get next words to learn
        new_words = self.get_next_words_to_learn(user_id)
        print(f"Got {len(new_words)} words to learn")
        
        # Generate audio for words that don't have it yet
        word_audio_urls = {}  # Store audio URLs for each word
        for word in new_words:
            if not hasattr(word, 'audio_url') or not word.audio_url:
                audio_url = self.generate_audio(word.word)
                if audio_url:
                    word.audio_url = audio_url
                    word_audio_urls[word.word] = audio_url
                    # Save audio URL to frequency dictionary
                    word_ref = self.firebase.db.collection('frequency_dictionary').document(word.word)
                    word_ref.update({'audio_url': audio_url})
        
        if not new_words:
            print("No suitable words found in frequency dictionary!")
            return None
        
        print("\nSelected words for this lesson:")
        for word in new_words:
            print(f"- {word.word} ({word.reading}) - {word.meaning}")
            print(f"  Audio URL: {getattr(word, 'audio_url', 'None')}")
        
        # Generate lesson content using AI
        prompt = f"""
        Create a Japanese lesson with multiple-choice questions using these words.
        For each word, create both a meaning question and a reading question.
        
        Words to learn:
        {', '.join([f"{w.word} ({w.reading}) - {w.meaning}" for w in new_words])}
        
        Return a JSON object with this structure:
        {{
            "exercises": [
                {{
                    "type": "multiple_choice",
                    "word": "<japanese_word>",
                    "reading": "<reading>",
                    "meaning": "<english_meaning>",
                    "question": "<question in English>",
                    "options": ["<option1>", "<option2>", "<option3>", "<option4>"],
                    "correct": "<correct answer>"
                }}
            ]
        }}
        
        For each word, create two types of questions:
        1. Meaning question: "What does [japanese_word] mean?"
        2. Reading question:
           - If the word contains kanji: "How do you read [japanese_word]?" with hiragana options
           - If the word is only hiragana: "How do you write [japanese_word] in romaji?" with romaji options
        """
        
        print("\nCalling API to generate lesson content...")
        lesson_content = self.call_api(prompt)
        print(f"Got response of length: {len(lesson_content)}")
        
        try:
            json_start = lesson_content.find('{')
            json_end = lesson_content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                lesson_json = lesson_content[json_start:json_end]
                lesson_data = json.loads(lesson_json)
                
                # Add audio URLs to exercises
                for exercise in lesson_data.get('exercises', []):
                    word = exercise.get('word')
                    if word in word_audio_urls:
                        exercise['audio_url'] = word_audio_urls[word]
                
                # Validate each exercise
                print("\nValidating exercises...")
                for i, exercise in enumerate(lesson_data.get('exercises', [])):
                    print(f"\nExercise {i+1}:")
                    print(f"Question: {exercise['question']}")
                    print(f"Options: {exercise['options']}")
                    print(f"Correct: {exercise['correct']}")
                    print(f"Audio URL: {exercise.get('audio_url', 'None')}")
                    if exercise['correct'] not in exercise['options']:
                        print(f"Warning: Correct answer not in options, fixing...")
                        exercise['options'][-1] = exercise['correct']
                
                return lesson_data
            else:
                print("Error: No JSON found in API response")
                print(f"Raw content: {lesson_content}")
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"\nError parsing lesson content: {str(e)}")
            print(f"Raw content: {lesson_content}")
            raise

    def get_user_seen_words(self, user_id: str) -> set:
        """Get set of words the user has seen in any lesson"""
        progress_docs = (self.firebase.db.collection('users')
                        .document(user_id)
                        .collection('word_progress')
                        .stream())
        return {doc.id for doc in progress_docs}

    def validate_and_fix_exercises(self, lesson_data: Dict) -> Dict:
        """Validate exercises and fix any issues with options/answers"""
        if 'exercises' not in lesson_data:
            raise ValueError("No exercises found in lesson data")
            
        fixed_exercises = []
        for exercise in lesson_data['exercises']:
            # Ensure we have all required fields
            required_fields = ['type', 'word', 'question', 'options', 'correct']
            if not all(field in exercise for field in required_fields):
                print(f"Exercise missing required fields: {exercise}")
                continue
                
            # Ensure we have exactly 4 options
            while len(exercise['options']) < 4:
                if exercise['question'].lower().startswith('how do you pronounce'):
                    # Add dummy romaji options
                    dummy_options = ['ka', 'ki', 'ku', 'ke', 'ko', 'sa', 'shi', 'su', 'se', 'so']
                    for opt in dummy_options:
                        if opt not in exercise['options'] and opt != exercise['correct']:
                            exercise['options'].append(opt)
                            if len(exercise['options']) == 4:
                                break
                else:
                    # Add dummy meaning options
                    dummy_options = ['thing', 'place', 'action', 'time', 'person', 'object', 'idea', 'feeling']
                    for opt in dummy_options:
                        if opt not in exercise['options'] and opt != exercise['correct']:
                            exercise['options'].append(opt)
                            if len(exercise['options']) == 4:
                                break
            
            # Trim if we somehow got more than 4 options
            exercise['options'] = exercise['options'][:4]
            
            # Ensure correct answer is in options
            if exercise['correct'] not in exercise['options']:
                # Replace last option with correct answer
                exercise['options'][-1] = exercise['correct']
            
            # Shuffle options to avoid correct answer always being last
            random.shuffle(exercise['options'])
            
            fixed_exercises.append(exercise)
        
        lesson_data['exercises'] = fixed_exercises
        return lesson_data

    def create_podcast_lesson(self, user_id: str, episode_number: int) -> Dict:
        """Create a lesson based on a podcast episode"""
        # Get episode transcript and vocabulary
        episode_ref = (self.firebase.db.collection('podcast_lessons')
                      .document(str(episode_number)))
        episode_doc = episode_ref.get()
        
        if not episode_doc.exists:
            raise ValueError(f"Episode {episode_number} not found")
            
        episode_data = episode_doc.to_dict()
        transcript = episode_data.get('transcript', '')
        
        # Get user's mastered and seen words
        mastered_words = self.get_user_mastered_words(user_id)
        seen_words = self.get_user_seen_words(user_id)
        
        # Get recently used words (from the last 24 hours)
        current_time = datetime.now().timestamp()
        recent_progress = (self.firebase.db.collection('users')
                         .document(user_id)
                         .collection('word_progress')
                         .where('last_seen', '>=', 
                               datetime.now().timestamp() - (24 * 60 * 60))
                         .stream())
        recently_used = {doc.id for doc in recent_progress}
        
        # Get all available vocabulary items from the episode
        vocab_items = episode_data.get('vocabulary_items', [])
        
        # Score and sort vocabulary items
        scored_vocab = []
        for word_data in vocab_items:
            word = word_data['word']
            if word not in mastered_words:  # Skip mastered words
                score = 0
                # Prioritize unseen words
                if word not in seen_words:
                    score += 100
                # Deprioritize recently used words
                if word in recently_used:
                    score -= 50
                # Add some randomness to avoid same order
                score += random.uniform(0, 10)
                
                scored_vocab.append((score, word_data))
        
        # Sort by score (highest first) and take top 5
        scored_vocab.sort(reverse=True)
        vocab = [word_data for _, word_data in scored_vocab[:5]]
        
        # If we don't have enough words, add some seen but unmastered words
        if len(vocab) < 5:
            remaining_needed = 5 - len(vocab)
            seen_words_vocab = [
                word_data for word_data in vocab_items
                if word_data['word'] in seen_words 
                and word_data['word'] not in mastered_words
                and word_data not in vocab  # Avoid duplicates
                and word_data['word'] not in recently_used  # Avoid recently used
            ]
            # Add randomness to selection of remaining words
            random.shuffle(seen_words_vocab)
            vocab.extend(seen_words_vocab[:remaining_needed])
        
        # Generate audio for words that don't have it
        word_audio_urls = {}  # Store audio URLs for each word
        updated_vocab = []  # Track any vocabulary updates
        
        for word_data in vocab:
            word = word_data['word']
            if not word_data.get('audio_url'):
                audio_url = self.generate_audio(word)
                if audio_url:
                    word_data['audio_url'] = audio_url
                    word_audio_urls[word] = audio_url
                    updated_vocab.append(word_data)
            else:
                word_audio_urls[word] = word_data['audio_url']
        
        # If we generated any new audio URLs, update the vocabulary items in Firebase
        if updated_vocab:
            # Get current vocabulary items
            current_vocab = episode_data.get('vocabulary_items', [])
            # Update items with new audio URLs
            vocab_dict = {item['word']: item for item in current_vocab}
            for updated_item in updated_vocab:
                vocab_dict[updated_item['word']] = updated_item
            # Save back to Firebase
            episode_ref.set({
                'vocabulary_items': list(vocab_dict.values())
            }, merge=True)
        
        # Generate lesson using AI
        prompt = f"""
        Create a Japanese lesson based on these vocabulary items from a podcast.
        For each word, create both a meaning question and a reading question.
        
        Words to learn:
        {', '.join([f"{w['word']} ({w['reading']}) - {w['meaning']}" for w in vocab])}
        
        Return a JSON object with this structure:
        {{
            "vocabulary": [
                {{
                    "word": "<japanese>",
                    "reading": "<hiragana>",
                    "romaji": "<romaji>",
                    "meaning": "<english>",
                    "context": "<japanese sentence from transcript>",
                    "context_en": "<english translation>",
                    "explanation": "<usage explanation>"
                }}
            ],
            "exercises": [
                {{
                    "type": "multiple_choice",
                    "word": "<japanese_word>",
                    "reading": "<hiragana>",
                    "romaji": "<romaji>",
                    "meaning": "<english_meaning>",
                    "question": "<question in English>",
                    "options": ["<option1>", "<option2>", "<option3>", "<option4>"],
                    "correct": "<correct answer>",
                    "context": "<example sentence>",
                    "context_en": "<english translation>"
                }}
            ]
        }}
        
        For each word, create two types of questions:
        1. Meaning question: "What does [japanese_word] mean?"
        2. Reading question: "How do you pronounce [japanese_word]?"
           - Always use romaji for pronunciation answers
           - Include both hiragana and romaji in the question data
        
        IMPORTANT RULES:
        1. Each question MUST have exactly 4 options
        2. The correct answer MUST be included in the options
        3. For meaning questions, use English words as options
        4. For reading questions, use ONLY romaji options
        5. Always include the Japanese word in the question
        6. Include relevant example sentences from the transcript when possible
        7. Provide clear, natural English translations
        """
        
        lesson_content = self.call_api(prompt)
        try:
            json_start = lesson_content.find('{')
            json_end = lesson_content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                lesson_json = lesson_content[json_start:json_end]
                lesson_json = re.sub(r'\([^)]*\)', '', lesson_json)
                lesson_json = re.sub(r'\s+', ' ', lesson_json)
                lesson_data = json.loads(lesson_json)
                
                # Validate and fix exercises
                lesson_data = self.validate_and_fix_exercises(lesson_data)
                
                # Add audio URLs to exercises and vocabulary
                for exercise in lesson_data.get('exercises', []):
                    word = exercise.get('word')
                    if word in word_audio_urls:
                        exercise['audio_url'] = word_audio_urls[word]
                
                for vocab_item in lesson_data.get('vocabulary', []):
                    word = vocab_item.get('word')
                    if word in word_audio_urls:
                        vocab_item['audio_url'] = word_audio_urls[word]
                
                # Add episode info
                lesson_data['episode_number'] = episode_number
                lesson_data['transcript'] = transcript
                
                return lesson_data
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"Error parsing lesson content: {e}")
            print(f"Raw content: {lesson_content}")
            raise

    def save_lesson_progress(self, user_id: str, lesson_data: Dict, lesson_type: str = 'regular'):
        """Save user's lesson progress and update word mastery"""
        # Save lesson completion
        collection_name = 'lesson_progress' if lesson_type == 'regular' else 'podcast_progress'
        lesson_number = lesson_data.get('lesson_number', lesson_data.get('episode_number'))
        
        progress_ref = (self.firebase.db.collection('users')
                       .document(user_id)
                       .collection(collection_name)
                       .document(str(lesson_number)))
        
        progress_ref.set({
            'completed': True,
            'score': lesson_data.get('score', 100),
            'timestamp': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        # Update word mastery for completed words
        for word in lesson_data.get('completed_words', []):
            self.record_word_mastery(user_id, word, lesson_type)

# Example usage:
if __name__ == "__main__":
    from firebase_config import FirebaseManager
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    firebase = FirebaseManager()
    tutor = JapaneseTutor(
        api_key=os.getenv("OPENAI_API_KEY"),
        firebase_manager=firebase,
        api_provider="openai"
    )
    
    # Create an enhanced lesson
    lesson = tutor.create_lesson("user_id")
