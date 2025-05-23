# Japanese Lessons Application

This is a full-stack application for Japanese language learning, featuring a Next.js frontend and a FastAPI backend.

## Prerequisites

- Node.js (v18 or higher)
- Python (v3.8 or higher)
- pnpm (for frontend package management)
- pip (for Python package management)

## Project Structure

```
japaneseLessons/
├── app/                 # Next.js frontend app directory
├── components/          # React components
├── styles/             # CSS and styling files
├── public/             # Static assets
├── backend/            # FastAPI backend
│   ├── app/           # Backend application code
│   └── requirements.txt # Python dependencies
└── package.json        # Frontend dependencies
```

## Setup and Running

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows (Git Bash):
     ```bash
     source venv/Scripts/activate
     ```
   - Windows (PowerShell):
     ```bash
     .\venv\Scripts\Activate.ps1
     ```
   - Unix/MacOS:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the backend directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   FIREBASE_CREDENTIALS=path_to_firebase_credentials.json
   FIREBASE_WEB_CONFIG=path_to_firebase_web_config.json
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   GOOGLE_APPLICATION_CREDENTIALS=path_to_google_cloud_credentials.json
   ```

6. Navigate to the app directory and run the backend server:
   ```bash
   cd app
   python -m uvicorn main:app --reload --port 8000
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the project root directory:
   ```bash
   cd japaneseLessons
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Run the development server:
   ```bash
   pnpm dev
   ```

The frontend will be available at `http://localhost:3000`

## Development

- Backend API documentation is available at `http://localhost:8000/docs` when the backend is running
- Frontend development server includes hot reloading
- Backend server includes auto-reload on code changes

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
pnpm test
``` 