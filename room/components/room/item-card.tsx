"use client";

import { Check, ExternalLink, Pencil, X } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { itemTitle, memberName, payloadText, projectName, TARGET_LABEL, timeAgo } from "@/lib/aor/describe";
import { allowedDecisions } from "@/lib/aor/fold";
import type { ResolveRequest } from "@/lib/aor/room";
import type { Item, RoomSnapshot } from "@/lib/aor/types";
import { cn } from "@/lib/utils";

const STATE_TEXT: Record<string, string> = {
  approved: "Approved · waiting for the agent to post",
  edited: "Edited and approved · waiting for the agent to post",
  done: "Posted",
  failed: "Couldn't post",
  rejected: "Rejected",
  answered: "Answered",
};

interface Props {
  item: Item;
  snapshot: RoomSnapshot;
  onResolve: (requests: ResolveRequest[]) => Promise<boolean>;
  selected?: boolean;
  onSelectedChange?: (selected: boolean) => void;
  showProject?: boolean;
}

export function ItemCard({ item, snapshot, onResolve, selected, onSelectedChange, showProject = true }: Props) {
  const [mode, setMode] = useState<"view" | "edit" | "reject">("view");
  const [draft, setDraft] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const allowed = snapshot.canAct ? allowedDecisions(item) : [];
  const owner = memberName(snapshot, item.project, item.owner);
  const content = item.final_payload ?? item.payload;

  const act = async (req: Omit<ResolveRequest, "id">) => {
    setBusy(true);
    setError(null);
    const ok = await onResolve([{ id: item.id, ...req }]);
    setBusy(false);
    if (ok) {
      setMode("view");
      setAnswer("");
    }
  };

  const saveEdit = () => {
    let payload: unknown = draft;
    if (content !== undefined && typeof content !== "string") {
      try {
        payload = JSON.parse(draft);
      } catch {
        setError("This content is structured data; keep it valid JSON.");
        return;
      }
    }
    act({ decision: "edited", payload });
  };

  return (
    <article
      className={cn(
        "rounded-lg border bg-card p-3 text-sm shadow-xs transition-colors",
        item.status === "open" ? "border-amber-500/40" : "border-border opacity-80",
        selected && "border-amber-400 ring-1 ring-amber-400/60",
      )}
    >
      <header className="flex items-start gap-2">
        {onSelectedChange && item.status === "open" && allowed.includes("approved") && (
          <Checkbox className="mt-0.5" checked={!!selected} onCheckedChange={(v) => onSelectedChange(!!v)} aria-label="Select for bulk approval" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            {item.kind === "approval" ? (
              <Badge variant="outline" className="border-amber-500/50 text-amber-600 dark:text-amber-300">
                ✋ {TARGET_LABEL[item.target ?? ""] ?? item.target}
                {item.action ? ` · ${item.action.replace(/_/g, " ")}` : ""}
              </Badge>
            ) : (
              <Badge variant="outline" className="border-sky-500/50 text-sky-600 dark:text-sky-300">
                ? Needs you
              </Badge>
            )}
            <span>
              {owner}
              {showProject ? ` · ${projectName(snapshot, item.project)}` : ""} · {timeAgo(item.created_at)}
            </span>
          </div>
          <p className="mt-1.5 font-medium leading-snug">{itemTitle(item)}</p>
          {item.rationale && <p className="mt-1 text-muted-foreground">{item.rationale}</p>}
        </div>
      </header>

      {item.kind === "approval" && content !== undefined && mode !== "edit" && (
        <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted px-2.5 py-2 font-sans text-[13px] whitespace-pre-wrap">{payloadText(content)}</pre>
      )}

      {(item.target_url || item.context_url || item.result_url) && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs">
          {item.target_url && (
            <a className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline" href={item.target_url} target="_blank" rel="noreferrer">
              Where it goes <ExternalLink className="size-3" />
            </a>
          )}
          {item.context_url && (
            <a className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline" href={item.context_url} target="_blank" rel="noreferrer">
              Context <ExternalLink className="size-3" />
            </a>
          )}
          {item.result_url && (
            <a className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline" href={item.result_url} target="_blank" rel="noreferrer">
              See the post <ExternalLink className="size-3" />
            </a>
          )}
        </div>
      )}

      {item.status !== "open" && (
        <p className={cn("mt-2 text-xs", item.status === "failed" ? "text-destructive" : "text-muted-foreground")}>
          {STATE_TEXT[item.status] ?? item.status}
          {item.answer ? `: “${item.answer}”` : ""}
          {item.note ? ` — ${item.note}` : ""} {item.resolved_at ? `· ${timeAgo(item.resolved_at)}` : ""}
        </p>
      )}

      {mode === "edit" && (
        <div className="mt-2 space-y-2">
          <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={6} className="font-mono text-[13px]" aria-label="Edited content" />
          <div className="flex gap-2">
            <Button size="sm" onClick={saveEdit} disabled={busy || !draft.trim()}>
              Approve edited version
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setMode("view")} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-2 space-y-2">
          <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={2} placeholder="Why? The agent reads this note (optional)." aria-label="Rejection note" />
          <div className="flex gap-2">
            <Button size="sm" variant="destructive" onClick={() => act({ decision: "rejected", note: draft })} disabled={busy}>
              Reject
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setMode("view")} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {mode === "view" && item.kind === "ask" && allowed.includes("answered") && (
        <div className="mt-2 space-y-2">
          {!!item.options?.length && (
            <div className="flex flex-wrap gap-1.5">
              {item.options.map((o) => (
                <Button key={o} size="sm" variant="outline" disabled={busy} onClick={() => act({ decision: "answered", answer: o })}>
                  {o}
                </Button>
              ))}
            </div>
          )}
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (answer.trim()) act({ decision: "answered", answer });
            }}
          >
            <Textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={1} placeholder="Or write an answer" className="min-h-8" aria-label="Answer" />
            <Button size="sm" type="submit" disabled={busy || !answer.trim()}>
              Answer
            </Button>
          </form>
          <Button size="xs" variant="ghost" className="text-muted-foreground" disabled={busy} onClick={() => setMode("reject")}>
            Dismiss the question
          </Button>
        </div>
      )}

      {mode === "view" && item.kind === "approval" && allowed.some((d) => ["approved", "edited", "rejected"].includes(d)) && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {allowed.includes("approved") && (
            <Button size="sm" disabled={busy} onClick={() => act({ decision: "approved" })}>
              <Check /> Approve
            </Button>
          )}
          {allowed.includes("edited") && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => {
                setDraft(payloadText(content));
                setMode("edit");
              }}
            >
              <Pencil /> Edit
            </Button>
          )}
          {allowed.includes("rejected") && (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setDraft("");
                setMode("reject");
              }}
            >
              <X /> Reject
            </Button>
          )}
        </div>
      )}
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </article>
  );
}
