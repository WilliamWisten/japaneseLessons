import { initializeApp, getApps } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyDXAq_0HsStXWjq-2oro1pXKRl1jeLZn2I",
    authDomain: "japanesetutor-27910.firebaseapp.com",
    projectId: "japanesetutor-27910",
    storageBucket: "japanesetutor-27910.firebasestorage.app",
    messagingSenderId: "802697635139",
    appId: "1:802697635139:web:2ec7d98351b295db793bf6",
    measurementId: "G-V4NXBG0T3J"
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
export const auth = getAuth(app); 