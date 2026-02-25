# Frontend — Next.js App

## Setup Instructions

```bash
cd frontend
npx -y create-next-app@latest . --typescript --app --no-tailwind --eslint --src-dir=no
npm install
npm run dev
```

## Environment Variables

Create `.env.local` from this template:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_FIREBASE_API_KEY=your-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
```
