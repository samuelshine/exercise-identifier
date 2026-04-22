# Project Context: Exercise Identifier

## 1. Project Overview
This project is a Progressive Web App (PWA) designed to help gym-goers identify exercises they don't know the name of. Users can input a natural language description or capture a short video, and the app will return the exact exercise along with form instructions, 3D visualizations, and alternatives.

**Target Output:** A highly responsive, mobile-first PWA accessible via smartphone browsers and laptops without requiring app store downloads.

## 2. Tech Stack Architecture
- **Frontend (UI/UX):** Next.js (React) configured as a PWA for installability.
- **Backend (API & Logic):** Python with FastAPI.
- **Database:** PostgreSQL for user data and exercise taxonomy.
- **AI / Search Engine:** - Semantic Text Search: LLM + Vector Database (e.g., Pinecone).
  - Video Identification: Computer Vision model (MediaPipe / YOLO-Pose) running on cloud servers.
- **Infrastructure:** Vercel (Frontend hosting), AWS (Backend/ML inference and ephemeral video storage).
- **Visual Assets:** Licensed 3D exercise API (e.g., Muscle and Motion) to avoid expensive custom rendering.

## 3. Core Features
- **Multimodal Search:**
  - Text input ("lying on back pushing dumbbells").
  - Video capture using HTML5 `<video>` and `MediaDevices.getUserMedia()`.
- **Results Engine:** Returns top 3-5 probable exercise matches.
- **Exercise Detail Page (EDP):**
  - **Header:** Standard name & alternate/colloquial names.
  - **Visuals:** Auto-looping 3D avatar demonstrating perfect form.
  - **Anatomy:** Glowing 3D muscle map highlighting primary and secondary targeted muscles.
  - **Stats:** Difficulty level and required equipment.
  - **Alternatives:** Biomechanically sound alternative exercises filtered by available equipment.

## 4. Development Guidelines & System Prompt for Claude
When assisting with this project, adhere to the following rules:
- **Role:** Act as a Senior Full-Stack Next.js Developer, Solutions Architect, and AI Engineer.
- **Mobile-First & Responsive:** Always prioritize mobile viewport layouts. For desktop, default to a split-screen layout (search on left, EDP on right).
- **Performance:** Keep the Next.js frontend lightweight. All heavy ML processing (pose estimation, video analysis) MUST be routed to the FastAPI backend. Do not suggest client-side TensorFlow.js for video processing due to battery and thermal constraints on mobile.
- **Privacy:** When handling the video capture logic, ensure the file is sent securely to the backend and explicitly mention that it is ephemeral (deleted immediately after processing).
- **Code Style:** Use modern React paradigms (Hooks, App Router if applicable in Next.js), strict TypeScript for prop validation, and Tailwind CSS for styling dark-mode, high-contrast UI elements.