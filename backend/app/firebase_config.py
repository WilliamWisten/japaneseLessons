import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import json
import requests
from typing import Optional, Dict
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import secrets
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, auth_callback, *args, **kwargs):
        self.auth_callback = auth_callback
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/callback'):
            # Parse the URL parameters
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            # Send response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
            
            # Call the callback with the auth code
            if 'code' in params:
                self.auth_callback(params['code'][0])

class FirebaseManager:
    def __init__(self):
        # Get the credentials file path from environment variable or use default
        creds_file = os.getenv('FIREBASE_CREDENTIALS', 'firebase_credentials.json')
        web_config_file = os.getenv('FIREBASE_WEB_CONFIG', 'firebase_web_config.json')
        
        # Initialize Firebase Admin SDK
        try:
            cred = credentials.Certificate(creds_file)
            bucket_name = 'japanesetutor-27910.firebasestorage.app'
            if not firebase_admin._apps:  # Only initialize if not already initialized
                firebase_admin.initialize_app(cred, {
                    'storageBucket': bucket_name
                })
            self.db = firestore.client()
            self.storage = storage.bucket(bucket_name)
            
            # Load web credentials for client auth
            with open(web_config_file, 'r') as f:
                self.web_config = json.load(f)
            
            self.current_user = None
            self.auth_code = None
            self.server = None
            
        except Exception as e:
            print(f"Error initializing Firebase: {str(e)}")
            raise
        
    def start_auth_server(self):
        """Start local server to handle OAuth callback"""
        # Try ports in sequence instead of random
        ports = [8000, 8100, 8200, 8300, 8400, 8500, 8600, 8700, 8800, 8900]
        
        for port in ports:
            try:
                handler = lambda *args: OAuthCallbackHandler(self.handle_auth_code, *args)
                self.server = socketserver.TCPServer(("", port), handler)
                
                # Start server in a separate thread
                server_thread = threading.Thread(target=self.server.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                return port
            except OSError:
                continue  # Port is in use, try next one
        
        raise RuntimeError("Could not find an available port")
    
    def handle_auth_code(self, code):
        """Handle the authentication code from Google"""
        self.auth_code = code
        # Start server shutdown in a separate thread
        threading.Thread(target=self._shutdown_server).start()
    
    def _shutdown_server(self):
        """Shutdown the server in a non-blocking way"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
    
    def sign_in_with_google(self) -> Optional[Dict]:
        """Handle Google Sign-in using browser"""
        try:
            print("Starting Google Sign-in process...")
            # Start local server for OAuth callback
            port = self.start_auth_server()
            print(f"OAuth callback server started on port {port}")
            
            # Construct OAuth URL
            oauth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={self.web_config['clientId']}&"
                "response_type=code&"
                f"redirect_uri=http://localhost:{port}/callback&"
                "scope=email%20profile&"
                "access_type=offline"
            )
            
            print("Opening browser for authentication...")
            webbrowser.open(oauth_url)
            
            # Wait for authentication
            timeout = 300  # 5 minutes
            start_time = time.time()
            while not self.auth_code and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.auth_code:
                print("Authentication timed out")
                raise Exception("Authentication timed out")
            
            print("Got auth code, exchanging for tokens...")
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": self.auth_code,
                "client_id": self.web_config['clientId'],
                "client_secret": self.web_config['clientSecret'],
                "redirect_uri": f"http://localhost:{port}/callback",
                "grant_type": "authorization_code"
            }
            
            response = requests.post(token_url, data=token_data)
            print(f"Token exchange response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Token exchange failed: {response.text}")
                raise Exception("Failed to get access token")
            
            tokens = response.json()
            print("Successfully got access token")
            
            # Get user info
            print("Getting user info...")
            user_info_response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            
            if user_info_response.status_code != 200:
                print(f"Failed to get user info: {user_info_response.text}")
                raise Exception("Failed to get user info")
            
            user_info = user_info_response.json()
            print(f"Got user info for: {user_info.get('email')}")
            
            # Sign in with Google OAuth token directly
            print("Signing in to Firebase...")
            response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.web_config['apiKey']}",
                json={
                    "requestUri": f"http://localhost:{port}/callback",
                    "postBody": f"access_token={tokens['access_token']}&providerId=google.com",
                    "returnSecureToken": True,
                    "returnIdpCredential": True
                }
            )
            
            if response.status_code != 200:
                error_data = response.json()
                print(f"Firebase sign-in failed: {error_data}")
                raise Exception(f"Failed to sign in: {error_data.get('error', {}).get('message', 'Unknown error')}")
            
            firebase_user = response.json()
            print("Successfully signed in to Firebase")
            
            self.current_user = {
                'localId': firebase_user['localId'],
                'idToken': firebase_user['idToken'],
                'email': user_info['email'],
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', '')
            }
            
            # Create or update user document
            print("Updating user document in Firestore...")
            self.update_user_data(self.current_user)
            print("User document updated")
            
            return self.current_user
            
        except Exception as e:
            print(f"Error during authentication: {str(e)}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            return None
        finally:
            # Remove server shutdown from here since it's handled in handle_auth_code
            pass
    
    def update_user_data(self, user_data: Dict):
        """Update or create user document in Firestore"""
        user_ref = self.db.collection('users').document(user_data['localId'])
        user_ref.set({
            'email': user_data['email'],
            'displayName': user_data.get('name', ''),
            'picture': user_data.get('picture', ''),
            'lastLogin': firestore.SERVER_TIMESTAMP
        }, merge=True)
    
    def save_word(self, user_id: str, word_data: Dict):
        """Save a word to user's vocabulary"""
        word_ref = (self.db.collection('users')
                   .document(user_id)
                   .collection('vocabulary')
                   .document(word_data['word']))
        
        word_ref.set({
            'reading': word_data['reading'],
            'meaning': word_data['meaning'],
            'context': word_data.get('context', ''),
            'encounter_count': firestore.Increment(1),
            'last_seen': firestore.SERVER_TIMESTAMP,
            'confidence_level': word_data.get('confidence_level', 0),
            'notes': word_data.get('notes', '')
        }, merge=True)
    
    def get_user_words(self, user_id: str, limit: int = 50) -> list:
        """Get user's saved words"""
        words_ref = (self.db.collection('users')
                    .document(user_id)
                    .collection('vocabulary')
                    .order_by('last_seen', direction=firestore.Query.DESCENDING)
                    .limit(limit))
        
        return [doc.to_dict() for doc in words_ref.stream()]
    
    def save_lesson_progress(self, user_id: str, lesson_data: Dict):
        """Save user's lesson progress"""
        progress_ref = (self.db.collection('users')
                       .document(user_id)
                       .collection('lesson_progress')
                       .document(str(lesson_data['lesson_number'])))
        
        progress_ref.set({
            'completed': lesson_data['completed'],
            'score': lesson_data.get('score', 0),
            'timestamp': firestore.SERVER_TIMESTAMP
        }, merge=True) 