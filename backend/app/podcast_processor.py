import json
from typing import List, Dict, Optional
import requests
from firebase_config import FirebaseManager
from tqdm import tqdm
from grok_enhanced_tutor import JapaneseTutor
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import whisper
import tempfile
import os
from pydub import AudioSegment
import shutil
from pydub.utils import which
from google.cloud import firestore
from google.api_core import retry
from google.api_core import exceptions
import time

class PodcastProcessor:
    def __init__(self, api_key: str, api_provider: str = "openai"):
        self.firebase = FirebaseManager()
        self.tutor = JapaneseTutor(api_key, self.firebase, api_provider)
        
        # Initialize Spotify client
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
        
        # Initialize Whisper model for transcription
        self.whisper_model = whisper.load_model("medium")
        
        # Set ffmpeg paths
        ffmpeg_base_path = r"C:\ffmpeg"
        ffmpeg_exe = os.path.join(ffmpeg_base_path, "ffmpeg.exe")
        ffprobe_exe = os.path.join(ffmpeg_base_path, "ffprobe.exe")
        
        if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
            # Add ffmpeg directory to PATH
            os.environ["PATH"] += os.pathsep + ffmpeg_base_path
            
            # Set environment variables
            os.environ["FFMPEG_BINARY"] = ffmpeg_exe
            os.environ["FFPROBE_BINARY"] = ffprobe_exe
            
            # Set pydub paths
            AudioSegment.converter = ffmpeg_exe
            AudioSegment.ffmpeg = ffmpeg_exe
            AudioSegment.ffprobe = ffprobe_exe
            
            print(f"Found ffmpeg tools at: {ffmpeg_base_path}")
            print(f"ffmpeg: {ffmpeg_exe}")
            print(f"ffprobe: {ffprobe_exe}")
        else:
            raise ValueError(
                "ffmpeg/ffprobe not found. Please install ffmpeg:\n"
                "1. Download from: https://github.com/BtbN/FFmpeg-Builds/releases\n"
                "2. Extract to C:\\ffmpeg\n"
                "3. Ensure both ffmpeg.exe and ffprobe.exe are in C:\\ffmpeg"
            )
    
    def convert_to_wav(self, input_path: str) -> str:
        """Convert audio file to WAV format using pydub"""
        output_path = input_path.rsplit('.', 1)[0] + '.wav'
        try:
            print(f"Converting {input_path} to WAV format...")
            
            # Load the audio file
            audio = AudioSegment.from_mp3(input_path)
            
            # Convert to mono and set sample rate
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            
            # Export as WAV with explicit parameters
            audio.export(
                output_path,
                format='wav',
                parameters=[
                    "-acodec", "pcm_s16le",  # Use standard PCM codec
                    "-ac", "1",              # mono
                    "-ar", "16000"           # 16kHz
                ]
            )
            
            if not os.path.exists(output_path):
                raise ValueError("WAV file was not created")
            
            print(f"Conversion successful. WAV file size: {os.path.getsize(output_path)} bytes")
            return output_path
            
        except Exception as e:
            print(f"Conversion error: {str(e)}")
            print(f"Input file exists: {os.path.exists(input_path)}")
            if os.path.exists(input_path):
                print(f"Input file size: {os.path.getsize(input_path)} bytes")
                print(f"Input file permissions: {oct(os.stat(input_path).st_mode)[-3:]}")
            print(f"Current ffmpeg path: {AudioSegment.converter}")
            print(f"Current ffprobe path: {AudioSegment.ffprobe}")
            raise
    
    def extract_episode_id(self, spotify_url: str) -> str:
        """Extract episode ID from Spotify URL"""
        # Handle both URL formats:
        # https://open.spotify.com/episode/5pstuxpo2H56lqdZqvprKw?si=5f83bafcec994c50
        # https://open.spotify.com/episode/5pstuxpo2H56lqdZqvprKw
        
        try:
            # Split URL by '?' to remove query parameters
            base_url = spotify_url.split('?')[0]
            # Get the last part of the URL which should be the episode ID
            episode_id = base_url.split('/')[-1]
            
            if not episode_id:
                raise ValueError("Could not extract episode ID from URL")
                
            print(f"Extracted episode ID: {episode_id}")
            return episode_id
            
        except Exception as e:
            raise ValueError(f"Invalid Spotify episode URL: {str(e)}")
    
    def get_episode_info(self, episode_id: str) -> Dict:
        """Get episode information from Spotify"""
        try:
            print(f"Fetching episode info for ID: {episode_id}")
            episode = self.spotify.episode(episode_id)
            
            # Get the highest quality image URL available
            image_url = None
            if episode.get('images'):
                # Sort images by size (width) in descending order and take the first one
                sorted_images = sorted(episode['images'], key=lambda x: x.get('width', 0), reverse=True)
                if sorted_images:
                    image_url = sorted_images[0]['url']
            
            info = {
                'name': episode['name'],
                'description': episode['description'],
                'duration_ms': episode['duration_ms'],
                'language': episode.get('language', 'ja'),  # Assume Japanese if not specified
                'preview_url': episode.get('audio_preview_url'),
                'show_name': episode['show']['name'],  # Add show name
                'show_id': episode['show']['id'],      # Add show ID
                'release_date': episode['release_date'],  # Add release date
                'show_publisher': episode['show'].get('publisher', 'Unknown'),  # Add publisher
                'image_url': image_url  # Add image URL
            }
            
            print(f"Found episode: {info['name']}")
            if not info['preview_url']:
                print("Warning: No preview URL available")
            if not info['image_url']:
                print("Warning: No image URL available")
                
            return info
            
        except Exception as e:
            raise ValueError(f"Failed to fetch episode info: {str(e)}")
    
    def transcribe_episode(self, episode_id: str) -> str:
        """Transcribe a Spotify episode using Whisper"""
        # First check if we already have this episode transcribed
        episode_ref = self.firebase.db.collection('podcast_lessons').document(episode_id)
        episode_doc = episode_ref.get()
        
        if episode_doc.exists:
            data = episode_doc.to_dict()
            if data.get('transcript'):
                return data['transcript']
        
        # Get episode info and preview URL
        episode_info = self.get_episode_info(episode_id)
        preview_url = episode_info.get('preview_url')
        
        if not preview_url:
            raise ValueError("No preview URL available for this episode. Try another episode.")
        
        print("Downloading audio preview...")
        # Download audio preview
        response = requests.get(preview_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download audio preview (Status code: {response.status_code})")
        
        # Create a temporary directory that will persist during transcription
        temp_dir = tempfile.mkdtemp()
        mp3_path = os.path.join(temp_dir, f'podcast_{episode_id}.mp3')
        wav_path = None
        
        try:
            # Save the audio file
            print(f"Saving audio to temporary file: {mp3_path}")
            with open(mp3_path, 'wb') as f:
                f.write(response.content)
            
            # Verify file exists and has content
            if not os.path.exists(mp3_path):
                raise ValueError("Failed to save audio file")
            
            file_size = os.path.getsize(mp3_path)
            print(f"Audio file saved successfully ({file_size} bytes)")
            
            # Convert to WAV
            wav_path = self.convert_to_wav(mp3_path)
            if not os.path.exists(wav_path):
                raise ValueError("WAV conversion failed - output file not found")
            
            wav_size = os.path.getsize(wav_path)
            print(f"WAV file created successfully ({wav_size} bytes)")
            
            print("Starting transcription with Whisper...")
            try:
                result = self.whisper_model.transcribe(
                    wav_path,
                    language='ja',
                    task='transcribe',
                    fp16=False  # Explicitly disable FP16 to avoid warning
                )
                if not result or 'text' not in result:
                    raise ValueError("Transcription failed - no result returned")
                    
                transcript = result['text']
                print("Transcription complete!")
                
                # Store in Firebase
                episode_ref.set({
                    'episode_id': episode_id,
                    'name': episode_info['name'],
                    'description': episode_info['description'],
                    'transcript': transcript,
                    'show_name': episode_info['show_name'],
                    'show_id': episode_info['show_id'],
                    'release_date': episode_info['release_date'],
                    'show_publisher': episode_info['show_publisher'],
                    'processed_date': firestore.SERVER_TIMESTAMP
                }, merge=True)
                
                return transcript
                
            except Exception as e:
                print(f"Whisper transcription error: {str(e)}")
                print(f"WAV file exists: {os.path.exists(wav_path)}")
                print(f"WAV file size: {os.path.getsize(wav_path) if os.path.exists(wav_path) else 'N/A'}")
                print(f"WAV file permissions: {oct(os.stat(wav_path).st_mode)[-3:] if os.path.exists(wav_path) else 'N/A'}")
                raise Exception(f"Whisper transcription failed: {str(e)}")
            
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            raise Exception(f"Error during transcription: {str(e)}")
        finally:
            # Clean up temp directory and its contents
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                if wav_path and os.path.exists(wav_path):
                    os.remove(wav_path)
                os.rmdir(temp_dir)
                print("Temporary files cleaned up")
            except Exception as e:
                print(f"Warning: Could not remove temporary files: {str(e)}")
        
        return None

    def extract_vocabulary(self, transcript: str) -> List[Dict]:
        """Extract vocabulary items from transcript using AI"""
        import re  # Move import to top of function
        
        prompt = """As a Japanese language expert, analyze this short transcript section and create a vocabulary list.

Input transcript section:
```
%s
```

Create a JSON array containing EVERY word and phrase from the transcript above. Include:
- Individual words (e.g., こんにちは, 仕事)
- Particles (は, が, を, etc.)
- Verb forms (e.g., します)
- Adjectives (e.g., いい)
- Common phrases (e.g., よろしく)

Format your response as a JSON array like this:
[
    {
        "word": "こんにちは",
        "reading": "こんにちは",
        "meaning": "hello, good afternoon",
        "part_of_speech": "greeting",
        "importance_level": "1",
        "importance_reason": "Essential greeting",
        "context": "%s"
    }
]

Important: Return ONLY the JSON array with complete entries."""
        
        # Process the transcript in smaller chunks
        chunk_size = 50  # Smaller chunks for more reliable processing
        chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
        all_vocabulary = []
        self.vocabulary_list = []  # Global list to track all words
        
        print(f"\nProcessing transcript in {len(chunks)} chunks...")
        
        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue
                
            print(f"\nProcessing chunk {i}/{len(chunks)}...")
            print(f"Chunk content: {chunk}")
            
            # Use % formatting instead of template strings to avoid JSON confusion
            current_prompt = prompt % (chunk, chunk)
            
            try:
                response = self.tutor.call_api(current_prompt)
                print(f"\nGot response of length: {len(response)}")
                print(f"Response preview: {response[:200]}")
                
                # Clean the response
                response = response.strip()
                
                # Find the complete JSON array
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    try:
                        json_content = response[json_start:json_end]
                        
                        # Validate JSON structure before parsing
                        open_braces = json_content.count('{')
                        close_braces = json_content.count('}')
                        if open_braces != close_braces:
                            print(f"Mismatched braces: {open_braces} open vs {close_braces} close")
                            continue
                            
                        print("\nExtracted JSON content:")
                        print(json_content)
                        
                        chunk_vocabulary = json.loads(json_content)
                        if not isinstance(chunk_vocabulary, list):
                            print(f"Expected JSON array but got {type(chunk_vocabulary)}")
                            continue
                        
                        # Process each word with more lenient validation
                        extracted_words = []
                        for word_data in chunk_vocabulary:
                            if not isinstance(word_data, dict):
                                continue
                                
                            word = word_data.get('word')
                            if not word:  # Skip entries without a word
                                continue
                                
                            # Skip non-Japanese words
                            if not any(c for c in word if '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff'):
                                continue
                                
                            # Ensure minimum required fields
                            if 'reading' not in word_data:
                                word_data['reading'] = word
                            if 'meaning' not in word_data:
                                word_data['meaning'] = ''
                            if 'part_of_speech' not in word_data:
                                word_data['part_of_speech'] = 'unknown'
                            if 'importance_level' not in word_data:
                                word_data['importance_level'] = '3'
                            if 'importance_reason' not in word_data:
                                word_data['importance_reason'] = 'Automatically categorized'
                            if 'context' not in word_data:
                                word_data['context'] = chunk
                                
                            # Add to extracted words for this chunk
                            extracted_words.append(word_data)
                        
                        # Process chunk with duplicate checking and common words
                        new_words = self.process_chunk(chunk, extracted_words, self.vocabulary_list)
                        
                        if new_words:
                            print(f"Added {len(new_words)} new words from chunk {i}")
                            print("New words:", ", ".join(new_words))
                        
                        # Show words that might have been missed
                        chunk_words = re.findall(r'[一-龯ぁ-んァ-ン]+[ー]*[一-龯ぁ-んァ-ン]*', chunk)
                        missed_words = [w for w in chunk_words if w not in new_words and w not in [v['word'] for v in self.vocabulary_list]]
                        if missed_words:
                            print("\nPotentially missed words:")
                            print(", ".join(missed_words))
                        
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing error in chunk {i}: {str(e)}")
                        print(f"Problematic JSON content: {json_content}")
                        continue
                else:
                    print(f"No valid JSON array found in response for chunk {i}")
                    print(f"Response content: {response}")
                    continue
                
            except Exception as e:
                print(f"Error processing chunk {i}: {str(e)}")
                continue
        
        # Use the vocabulary list we've built up
        all_vocabulary = self.vocabulary_list
        
        if not all_vocabulary:
            print("\nNo vocabulary extracted through AI. Using fallback method...")
            words = re.findall(r'[一-龯ぁ-んァ-ン]+[ー]*[一-龯ぁ-んァ-ン]*', transcript)
            for word in set(words):
                word_data = {
                    "word": word,
                    "reading": word,
                    "meaning": "",
                    "part_of_speech": "unknown",
                    "importance_level": "3",
                    "importance_reason": "Automatically extracted",
                    "context": ""
                }
                all_vocabulary.append(word_data)
        
        # Sort all vocabulary by importance level
        all_vocabulary.sort(key=lambda x: int(x['importance_level']))
        
        # Print detailed statistics
        importance_counts = {}
        for word in all_vocabulary:
            level = word['importance_level']
            importance_counts[level] = importance_counts.get(level, 0) + 1
        
        print("\nVocabulary Statistics:")
        print(f"Total unique words extracted: {len(all_vocabulary)}")
        for level in sorted(importance_counts.keys()):
            print(f"Level {level} words: {importance_counts[level]}")
        
        # Print some example words from each level
        print("\nExample words from each level:")
        for level in sorted(importance_counts.keys()):
            examples = [w['word'] for w in all_vocabulary if w['importance_level'] == str(level)][:3]
            if examples:
                print(f"Level {level}: {', '.join(examples)}")
        
        return all_vocabulary

    def process_chunk(self, chunk, extracted_words, vocabulary_list):
        """Process a chunk of text, checking for duplicates and common words
        
        Args:
            chunk: The text chunk to process
            extracted_words: List of word dictionaries from AI extraction
            vocabulary_list: Global list of all words seen so far
            
        Returns:
            List of new words added from this chunk
        """
        # Add duplicate check
        new_words = []
        for word_data in extracted_words:
            word = word_data['word']
            if word not in [w['word'] for w in vocabulary_list]:
                new_words.append(word)
                vocabulary_list.append(word_data)
        
        # Add common particles and verbs
        common_words = ["とか", "あと", "何", "その", "ですね", "が", "は", "を", "に", "へ", "で", "から", "まで", "より", 
                       "ます", "ました", "です", "でした", "ある", "ない", "なかった", "ありました", "がいます"]
        
        for word in common_words:
            if word in chunk and word not in [w['word'] for w in vocabulary_list]:
                # Create a basic word entry for common words
                word_data = {
                    "word": word,
                    "reading": word,
                    "meaning": "Common word/particle",
                    "part_of_speech": "particle/auxiliary",
                    "importance_level": "2",
                    "importance_reason": "Common Japanese word",
                    "context": chunk
                }
                new_words.append(word)
                vocabulary_list.append(word_data)
        
        return new_words

    def process_spotify_episode(self, spotify_url: str) -> Dict:
        """Process a Spotify podcast episode and create a lesson"""
        print(f"Processing Spotify episode URL: {spotify_url}")
        
        try:
            # Extract episode ID and get transcript
            episode_id = self.extract_episode_id(spotify_url)
            
            # Check if we already have this episode processed
            episode_ref = self.firebase.db.collection('podcast_lessons').document(episode_id)
            episode_doc = episode_ref.get()
            
            if episode_doc.exists:
                data = episode_doc.to_dict()
                if data.get('transcript') and data.get('vocabulary_items'):
                    print("Found existing processed episode, returning cached data")
                    return {
                        'episode_id': episode_id,
                        'vocabulary': data['vocabulary_items'],
                        'transcript': data['transcript']
                    }
            
            print("Starting new episode processing...")
            # Get episode info first to have access to metadata
            episode_info = self.get_episode_info(episode_id)
            transcript = self.transcribe_episode(episode_id)
            if not transcript:
                raise ValueError("Failed to get transcript from episode")
            
            print("Extracting vocabulary...")
            vocabulary = self.extract_vocabulary(transcript)
            if not vocabulary:
                raise ValueError("Failed to extract vocabulary from transcript")
            
            # Generate audio URLs for all vocabulary items first
            print("Generating audio URLs for vocabulary items...")
            for word_data in vocabulary:
                word = word_data['word']
                if not word_data.get('audio_url'):
                    audio_url = self.tutor.generate_audio(word)
                    if audio_url:
                        word_data['audio_url'] = audio_url
            
            # Store complete data in Firebase with a single merge operation
            episode_ref.set({
                'vocabulary_items': vocabulary,
                'processed_date': firestore.SERVER_TIMESTAMP,
                'name': episode_info['name'],
                'description': episode_info['description'],
                'show_name': episode_info['show_name'],
                'show_publisher': episode_info['show_publisher'],
                'release_date': episode_info['release_date'],
                'image_url': episode_info.get('image_url'),  # Include the image URL
                'transcript': transcript
            }, merge=True)
            
            print("Episode processing complete!")
            return {
                'episode_id': episode_id,
                'vocabulary': vocabulary,
                'transcript': transcript,
                'image_url': episode_info.get('image_url')  # Include the image URL in the response
            }
            
        except Exception as e:
            print(f"Error processing episode: {str(e)}")
            raise


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Example usage:
    spotify_urls = [
        'https://open.spotify.com/episode/1234567890abcdef',
        'https://open.spotify.com/episode/0987654321fedcba',
        # Add more URLs here
    ]
    
    process_all_episodes(os.getenv("OPENAI_API_KEY"), spotify_urls) 