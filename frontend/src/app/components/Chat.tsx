'use client';

import { useState, useRef, FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ChatResponse, Citation } from '../types/chat';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
};

interface ChatProps { paperId: string; }

export function Chat({ paperId }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  // 1️⃣ POST to /api/chat
  async function fetchChat(query: string) {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paperId, query }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<ChatResponse>;
  }

  // 2️⃣ React Query mutation
  const mutation = useMutation(fetchChat, {
    onMutate: (query) => {
      setMessages((msgs) => [
        ...msgs,
        { id: `u${Date.now()}`, role: 'user', content: query },
      ]);
      setInput('');
    },
    onSuccess: ({ answer, citations }) => {
      setMessages((msgs) => [
        ...msgs,
        { id: `a${Date.now()}`, role: 'assistant', content: answer, citations },
      ]);
    },
    onError: (err) => {
      setMessages((msgs) => [
        ...msgs,
        {
          id: `e${Date.now()}`,
          role: 'assistant',
          content: `⚠ ${(err as Error).message}`,
        },
      ]);
    },
    onSettled: () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }),
  });

  // 3️⃣ Handle form submit
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    mutation.mutate(input);
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Message List ── */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`
              max-w-[70%] p-3 rounded-lg
              ${m.role === 'user' ? 'self-end bg-blue-200' : 'self-start bg-gray-100'}
            `}
          >
            <p>{m.content}</p>
            {m.citations && (
              <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                {m.citations.map((c,i) => (
                  <li key={i}>
                    Page {c.page}: “{c.textSnippet}”
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {mutation.isLoading && (
          <div className="self-start p-3 rounded-lg bg-gray-100 flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" />
            <span>Loading…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Bar ── */}
      <form onSubmit={handleSubmit} className="border-t p-4 flex space-x-2">
        <input
          className="flex-1 border rounded px-3 py-2"
          placeholder="Ask a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={mutation.isLoading}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          disabled={mutation.isLoading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
