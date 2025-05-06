
import { Chat } from '@/app/components/Chat';     // adjust if your Chat lives elsewhere
import { useParams } from 'next/navigation';

export default function ChatPage() {
  const { paperId } = useParams();
  if (!paperId) return <p>Loading…</p>;

  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 border-b text-lg font-semibold">
        Chat about Paper {paperId}
      </header>
      <Chat paperId={paperId} />
    </div>
  );
}