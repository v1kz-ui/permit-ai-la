"use client";

import { useEffect, useRef, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { MOCK_PROJECTS } from "@/lib/mockData";

interface Project {
  id: string;
  address?: string;
  project_address?: string;
  pathway?: string;
  status?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  sourcesOpen?: boolean;
}

const pathwayColors: Record<string, string> = {
  standard: "bg-indigo-100 text-indigo-700",
  eo1: "bg-violet-100 text-violet-700",
  eo8: "bg-purple-100 text-purple-700",
  coastal: "bg-cyan-100 text-cyan-700",
  hillside: "bg-amber-100 text-amber-700",
};

const GENERIC_QUESTIONS = [
  "What clearances are still pending?",
  "Which department is causing the most delays?",
  "Is this project eligible for EO1 pathway?",
  "What are the next required inspections?",
];

function getSuggestedQuestions(project: Project | null): string[] {
  if (!project) return GENERIC_QUESTIONS;

  const address = project.address || project.project_address || "this project";
  const pathway = project.pathway?.toUpperCase() || null;
  const status = project.status?.replace(/_/g, " ") || null;

  const questions: string[] = [];

  // Pathway-specific questions
  if (pathway) {
    questions.push(`What are the ${pathway} pathway requirements for ${address}?`);
    if (pathway !== "EO1") {
      questions.push(`Is ${address} eligible for the EO1 fast-track pathway?`);
    }
  } else {
    questions.push(`Which permit pathway applies to ${address}?`);
  }

  // Status-specific questions
  if (status) {
    questions.push(`What is needed to move ${address} past the "${status}" stage?`);
  } else {
    questions.push(`What clearances are still pending for ${address}?`);
  }

  // Always useful
  questions.push(`Which department is causing the most delays for ${address}?`);
  questions.push(`What are the next required inspections for ${address}?`);

  return questions.slice(0, 4);
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
        AI
      </div>
      <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function MessageBubble({ msg, index, onToggleSources }: { msg: Message; index: number; onToggleSources: (i: number) => void }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex items-end gap-3 mb-4 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0 ${
        isUser ? "bg-slate-200 text-slate-600" : "bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
      }`}>
        {isUser ? "You" : "AI"}
      </div>
      <div className={`max-w-[72%] flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap rounded-2xl ${
          isUser
            ? "bg-indigo-600 text-white rounded-br-sm"
            : "bg-slate-100 text-slate-800 rounded-bl-sm"
        }`}>
          {msg.content}
        </div>
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="w-full">
            <button onClick={() => onToggleSources(index)}
              className="text-xs text-indigo-500 hover:text-indigo-700 flex items-center gap-1.5 transition-colors font-medium"
              aria-expanded={msg.sourcesOpen}
              aria-label={`${msg.sourcesOpen ? "Hide" : "View"} ${msg.sources.length} source${msg.sources.length !== 1 ? "s" : ""}`}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
            </button>
            {msg.sourcesOpen && (
              <ul className="mt-1.5 space-y-1">
                {msg.sources.map((src, si) => (
                  <li key={si} className="text-xs text-slate-500 bg-white border border-slate-200 rounded-lg px-3 py-1.5 truncate">
                    {src}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const MAX_MESSAGES_PER_HOUR = 20;

export default function ChatPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [search, setSearch] = useState("");
  const [messageCount, setMessageCount] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.projects.list()
      .then((data) => {
        const list = Array.isArray(data) ? data : (data as any).items || [];
        setProjects(list.length > 0 ? list : MOCK_PROJECTS.items);
      })
      .catch(() => setProjects(MOCK_PROJECTS.items))
      .finally(() => setProjectsLoading(false));
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, typing]);

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || !selectedProject || typing) return;
    const userMsg: Message = { role: "user", content: msg };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setTyping(true);
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessageCount((c) => c + 1);
    try {
      const res = await api.chat.send(selectedProject.id, msg, history);
      setMessages((prev) => [...prev, { role: "assistant", content: res.response, sources: res.sources, sourcesOpen: false }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Sorry, I encountered an error: ${err.message}` }]);
    } finally {
      setTyping(false);
    }
  }

  function toggleSources(index: number) {
    setMessages((prev) => prev.map((m, i) => i === index ? { ...m, sourcesOpen: !m.sourcesOpen } : m));
  }

  function selectProject(p: Project) {
    setSelectedProject(p);
    setMessages([]);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  const projectAddress = (p: Project) => p.address || p.project_address || p.id;
  const filteredProjects = projects.filter((p) =>
    !search || projectAddress(p).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-screen min-h-screen overflow-hidden">
      <Sidebar />

      {/* Project list panel */}
      <aside className="w-72 border-r border-slate-200 bg-white flex flex-col flex-shrink-0">
        <div className="px-4 py-5 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-800">AI Assistant</h2>
          <p className="text-xs text-slate-500 mt-0.5">Select a project to start chatting</p>
        </div>
        <div className="px-3 py-3 border-b border-slate-100">
          <div className="relative">
            <svg className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="w-full pl-8 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {projectsLoading ? (
            <div className="p-4 space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />)}
            </div>
          ) : filteredProjects.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No projects found</p>
          ) : (
            filteredProjects.map((p) => (
              <button
                key={p.id}
                onClick={() => selectProject(p)}
                className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors relative ${
                  selectedProject?.id === p.id ? "bg-indigo-50/60" : ""
                }`}
              >
                {selectedProject?.id === p.id && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-7 bg-indigo-500 rounded-r-full" />
                )}
                <p className={`text-sm font-medium truncate ${selectedProject?.id === p.id ? "text-indigo-700" : "text-slate-700"}`}>
                  {projectAddress(p)}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {p.pathway && (
                    <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${pathwayColors[p.pathway?.toLowerCase()] || "bg-slate-100 text-slate-600"}`}>
                      {p.pathway.toUpperCase()}
                    </span>
                  )}
                  {p.status && <span className="text-xs text-slate-400 capitalize">{p.status.replace(/_/g, " ")}</span>}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Chat panel */}
      <main className="flex-1 flex flex-col min-h-0 bg-slate-50">
        {selectedProject ? (
          <>
            {/* Chat header */}
            <div className="border-b border-slate-200 px-6 py-4 bg-white flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xs font-bold text-white">AI</div>
                <div>
                  <p className="text-sm font-semibold text-slate-800 truncate max-w-sm">{projectAddress(selectedProject)}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-xs text-slate-500">Ready to assist</span>
                    {selectedProject.pathway && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${pathwayColors[selectedProject.pathway?.toLowerCase()] || "bg-slate-100 text-slate-600"}`}>
                        {selectedProject.pathway.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button onClick={() => { setSelectedProject(null); setMessages([]); }}
                className="text-xs text-slate-400 hover:text-slate-600 font-medium transition-colors">
                Change project
              </button>
            </div>

            {/* AI disclaimer banner */}
            <div className="bg-amber-50 border-b border-amber-100 px-6 py-2.5 flex items-center gap-2 text-xs text-amber-700 flex-shrink-0" role="note">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>AI responses are for guidance only and may not reflect the latest regulations. Always verify with the relevant department. <strong>Not legal advice.</strong></span>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin">
              {messages.length === 0 && !typing && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-2xl mb-4 shadow-lg">
                    💬
                  </div>
                  <p className="text-base font-semibold text-slate-700">Ask anything about this project</p>
                  <p className="text-sm text-slate-400 mt-1 max-w-xs">
                    Clearances, timelines, requirements, bottlenecks, eligibility…
                  </p>
                  <div className="mt-6 grid grid-cols-2 gap-2 w-full max-w-sm">
                    {getSuggestedQuestions(selectedProject).map((q) => (
                      <button key={q} onClick={() => sendMessage(q)}
                        className="text-left text-xs text-slate-600 bg-white border border-slate-200 rounded-xl px-3 py-2.5 hover:border-indigo-300 hover:bg-indigo-50/40 hover:text-indigo-700 transition-all">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((msg, i) => (
                <MessageBubble key={i} msg={msg} index={i} onToggleSources={toggleSources} />
              ))}
              {typing && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t border-slate-200 px-6 py-4 bg-white flex-shrink-0">
              <div className="flex items-end gap-3 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all">
                <textarea
                  ref={inputRef}
                  rows={1}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  placeholder="Ask about clearances, timelines, requirements… (Enter to send)"
                  className="flex-1 bg-transparent text-sm resize-none outline-none max-h-32 leading-relaxed text-slate-800 placeholder-slate-400"
                  disabled={typing}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || typing}
                  className="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
                  aria-label="Send"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 rotate-90">
                    <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
                  </svg>
                </button>
              </div>
              <p className="text-xs text-slate-400 mt-2 text-center">
                {messageCount > 0 && (
                  <span className={messageCount >= MAX_MESSAGES_PER_HOUR - 3 ? "text-amber-500 font-medium" : ""}>
                    {MAX_MESSAGES_PER_HOUR - messageCount} question{MAX_MESSAGES_PER_HOUR - messageCount !== 1 ? "s" : ""} remaining this hour ·{" "}
                  </span>
                )}
                Responses based on project data and LA permit regulations · Not legal advice
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-4xl mb-5 shadow-xl">
              💬
            </div>
            <h3 className="text-xl font-bold text-slate-700 mb-2">PermitAI Assistant</h3>
            <p className="text-sm text-slate-400 max-w-xs leading-relaxed">
              Select a project from the left panel to ask questions about clearances, timelines, and permit requirements.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
