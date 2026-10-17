"use client";

import { Archive } from "lucide-react";
import { formatBytes, formatDateTime, shortHash } from "@/lib/format";
import type { Snapshot } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/copy-button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui/table";
import { SourceBadge } from "@/components/status/source-badge";
import { useRunContext } from "./run-context";

export function SnapshotsTab({ snapshots }: { snapshots: Snapshot[] }) {
  const { openSnapshot } = useRunContext();
  if (!snapshots.length) {
    return (
      <Card>
        <EmptyState icon={<Archive className="size-5" />} title="No snapshots" description="No raw responses were frozen for this run." />
      </Card>
    );
  }
  const totalBytes = snapshots.reduce((sum, s) => sum + s.size, 0);
  return (
    <Card>
      <CardHeader
        title="Frozen raw responses"
        description={`${snapshots.length} immutable snapshots, ${formatBytes(totalBytes)} in total. Integrity is checked against the SHA-256 on every read.`}
      />
      <Table>
        <THead>
          <tr>
            <Th>Source</Th>
            <Th>Endpoint</Th>
            <Th className="text-right">Size</Th>
            <Th>Fetched</Th>
            <Th>SHA-256</Th>
          </tr>
        </THead>
        <TBody>
          {snapshots.map((s) => (
            <Tr key={s.id} onClick={() => openSnapshot(s.id)} className="cursor-pointer align-middle hover:bg-slate-50">
              <Td>
                <SourceBadge source={s.source} handle={s.handle} />
              </Td>
              <Td>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    openSnapshot(s.id);
                  }}
                  className="font-mono text-xs font-medium text-indigo-700 hover:underline"
                >
                  {s.endpoint}
                </button>
              </Td>
              <Td className="text-right tabular-nums">{formatBytes(s.size)}</Td>
              <Td className="whitespace-nowrap text-slate-500">{formatDateTime(s.fetched_at)}</Td>
              <Td>
                <span className="inline-flex items-center gap-1 font-mono text-xs text-slate-600" title={s.sha256}>
                  {shortHash(s.sha256)}
                  <CopyButton value={s.sha256} label={`Copy SHA-256 of ${s.endpoint}`} />
                </span>
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </Card>
  );
}
