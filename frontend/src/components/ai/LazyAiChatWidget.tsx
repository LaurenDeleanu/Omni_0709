"use client";

import dynamic from "next/dynamic";

const AiChatWidgetClient = dynamic(
  () => import("@/components/ai/AiChatWidget").then((mod) => ({ default: mod.AiChatWidget })),
  { ssr: false, loading: () => null }
);

export function LazyAiChatWidget() {
  return <AiChatWidgetClient />;
}
