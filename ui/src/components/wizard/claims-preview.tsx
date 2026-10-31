import { CLAIM_KIND_LABEL, describeClaim, groupClaims } from "@/lib/domain";
import type { ClaimPreview } from "@/lib/types";

export function ClaimsPreview({ claims }: { claims: ClaimPreview[] }) {
  if (claims.length === 0) {
    return <p className="text-sm text-slate-500">No verifiable claims were detected. The run can still match job requirements.</p>;
  }
  return (
    <div className="space-y-4">
      {groupClaims(claims).map(([kind, items]) => (
        <div key={kind}>
          <h4 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            {CLAIM_KIND_LABEL[kind] ?? kind} <span className="font-normal">({items.length})</span>
          </h4>
          <ul className="flex flex-wrap gap-1.5">
            {items.map((claim, i) => (
              <li
                key={`${claim.text}-${i}`}
                title={`“${claim.text}”`}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700"
              >
                {describeClaim(claim)}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
