// src/app/chat/[paperId]/page.tsx
import { Chat } from '@/app/components/Chat';

// Next.js 15 now makes params a Promise you must await.
interface ChatPageProps {
  params: { paperId: string } | Promise<{ paperId: string }>;
}

export default async function ChatPage({ params }: ChatPageProps) {
  // await the params before using them
  const { paperId } = await params;

  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 border-b text-lg font-semibold">
        Chat about Paper {paperId}
      </header>
      <Chat paperId={paperId} />
    </div>
  );
}