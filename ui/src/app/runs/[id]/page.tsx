import type { Metadata } from "next";
import { RunView } from "@/components/run/run-view";

export const metadata: Metadata = { title: "Run" };

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunView key={id} runId={decodeURIComponent(id)} />;
}
