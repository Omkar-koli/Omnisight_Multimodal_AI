"use client";

import { useMemo, useRef, useEffect, useState } from "react";
import { useParams, usePathname } from "next/navigation";
import { sendAssistantChat } from "@/lib/api";
import type { AssistantChatMessage, AssistantChatResponse } from "@/lib/types";
import { AssistantResponse } from "@/components/assistant/assistant-response";
import {
  Sparkles,
  X,
  Send,
  Bot,
  ExternalLink,
  ChevronDown,
} from "lucide-react";

/* ─────────────────── context helpers ─────────────────── */

function getPageContext(pathname: string, productId?: string) {
  if (pathname.startsWith("/products/") && productId)
    return "product_detail" as const;
  if (pathname.startsWith("/products")) return "products" as const;
  if (pathname.startsWith("/monitoring")) return "monitoring" as const;
  return "global" as const;
}

function getStarterPrompts(
  pageContext: "products" | "monitoring" | "product_detail" | "global"
) {
  if (pageContext === "products") {
    return [
      "What is trending right now?",
      "What will trend next?",
      "Which category needs attention?",
      "Which products are overstocked?",
    ];
  }
  if (pageContext === "monitoring") {
    return [
      "Which products need attention first?",
      "What is trending right now?",
      "What will trend next?",
      "Which products are overstocked?",
    ];
  }
  if (pageContext === "product_detail") {
    return [
      "Summarize this product for me.",
      "Why was this product flagged?",
      "What is the biggest risk here?",
      "Should I monitor this closely?",
    ];
  }
  return [
    "What is trending right now?",
    "What will trend next?",
    "Which products need attention first?",
  ];
}

/* ─────────────────── Loading dots ─────────────────── */

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-primary/60 pulse-dot"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}

/* ─────────────────── Main Widget ─────────────────── */

export function AssistantChatWidget() {
  const pathname = usePathname();
  const params = useParams<{ productId?: string }>();
  const productId =
    typeof params?.productId === "string" ? params.productId : undefined;

  const pageContext = useMemo(
    () => getPageContext(pathname, productId),
    [pathname, productId]
  );

  const isVisible =
    pageContext === "products" ||
    pageContext === "monitoring" ||
    pageContext === "product_detail";

  const starterPrompts = useMemo(
    () => getStarterPrompts(pageContext),
    [pageContext]
  );

  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi, I'm the OmniSight assistant.\n\nAsk me what is trending right now, what may trend next, which products are overstocked, or which products need attention.",
    },
  ]);
  const [suggestions, setSuggestions] = useState<string[]>(starterPrompts);
  const [isLoading, setIsLoading] = useState(false);
  const [referencedProductIds, setReferencedProductIds] = useState<string[]>(
    []
  );

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  if (!isVisible) return null;

  async function handleSend(messageText?: string) {
    const text = (messageText ?? input).trim();
    if (!text || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setIsLoading(true);

    try {
      const res: AssistantChatResponse = await sendAssistantChat({
        message: text,
        page_context: pageContext,
        product_id: productId || "",
      });

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer },
      ]);
      setSuggestions(
        res.suggestions?.length ? res.suggestions : starterPrompts
      );
      setReferencedProductIds(res.referenced_product_ids ?? []);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            error?.message || "Sorry, I could not process that question right now.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      {/* ── FAB toggle button ── */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "Close AI Assistant" : "Open AI Assistant"}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/30 transition-all duration-200 hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/25 active:scale-95"
      >
        {isOpen ? (
          <>
            <ChevronDown className="h-4 w-4" />
            <span className="hidden sm:inline">Close</span>
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">AI Assistant</span>
          </>
        )}
      </button>

      {/* ── Chat panel ── */}
      {isOpen ? (
        <div className="fixed bottom-20 right-5 z-50 flex h-[78vh] max-h-[680px] w-[460px] max-w-[calc(100vw-1.25rem)] flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl shadow-black/20 chat-slide-up">
          {/* Header */}
          <div className="flex items-center justify-between gap-3 bg-primary px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary-foreground/15">
                <Bot className="h-4 w-4 text-primary-foreground" />
              </div>
              <div>
                <div className="text-sm font-semibold text-primary-foreground">
                  OmniSight Assistant
                </div>
                <div className="text-[10px] text-primary-foreground/70">
                  Powered by Ollama · Context-aware
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1.5 text-primary-foreground/70 transition hover:bg-primary-foreground/15 hover:text-primary-foreground"
              aria-label="Close assistant"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`flex gap-2.5 ${
                  message.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                {/* Avatar */}
                {message.role === "assistant" && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}

                {/* Bubble */}
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "rounded-tr-sm bg-primary text-primary-foreground"
                      : "rounded-tl-sm bg-muted text-foreground"
                  }`}
                >
                  {message.role === "assistant" ? (
                    <AssistantResponse content={message.content} />
                  ) : (
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  )}
                </div>
              </div>
            ))}

            {/* Thinking indicator */}
            {isLoading && (
              <div className="flex items-center gap-2.5">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2.5">
                  <ThinkingDots />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Referenced products */}
          {referencedProductIds.length > 0 && (
            <div className="border-t bg-muted/40 px-4 py-3">
              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Referenced Products
              </div>
              <div className="flex flex-wrap gap-1.5">
                {referencedProductIds.slice(0, 6).map((id) => (
                  <a
                    key={id}
                    href={`/products/${id}`}
                    className="inline-flex items-center gap-1 rounded-full border bg-background px-2.5 py-1 text-[10px] font-medium text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                  >
                    {id}
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Quick prompts */}
          <div className="border-t bg-background px-4 pt-3 pb-1">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Quick Prompts
            </div>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.slice(0, 4).map((suggestion, index) => (
                <button
                  key={`${suggestion}-${index}`}
                  type="button"
                  onClick={() => handleSend(suggestion)}
                  disabled={isLoading}
                  className="rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary transition hover:bg-primary/10 disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Input row */}
          <div className="border-t bg-background px-4 py-3">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about products, trends, or risks…"
                disabled={isLoading}
                className="flex-1 rounded-xl border bg-muted/40 px-3.5 py-2.5 text-sm placeholder:text-muted-foreground/60 outline-none focus:border-primary focus:bg-background focus:ring-2 focus:ring-primary/20 transition-all disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim()}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition hover:bg-primary/90 active:scale-95 disabled:opacity-40"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
