"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";
import SnippetPanel from "@/components/audit/SnippetPanel";
import SourcePanel from "@/components/audit/SourcePanel";
import ReviewButtons from "@/components/audit/ReviewButtons";
import { SearchResult, ReviewStatus, Citation, Document } from "@/src/types";

export default function AuditPage() {
  const t = useTranslations("audit");
  const [items, setItems] = useState<SearchResult[]>([]);
  const [index, setIndex] = useState(0);
  const [states, setStates] = useState<Record<string, ReviewStatus>>({});

  useEffect(() => {
    Promise.all([
      fetch("/api/citations").then(r => r.json()),
      fetch("/api/documents").then(r => r.json()),
    ]).then(([cits, docs]) => {
      setItems(
        (cits as Citation[])
          .map(c => ({ citation: c, document: (docs as Document[]).find(d => d.id === c.doc_id)! }))
          .filter(r => r.document)
      );
    }).catch(() => setItems([]));
  }, []);

  if (items.length === 0) {
    return <div className="flex items-center justify-center h-full text-[13px] text-gray-400">Loading…</div>;
  }

  const cur = items[index];
  const id  = cur.citation.id;
  const status: ReviewStatus = states[id] ?? (cur.citation.reviewed ? "approved" : "pending");
  const setStatus = (s: ReviewStatus) => setStates(p => ({ ...p, [id]: s }));

  const reviewed  = Object.values(states).filter(s => s === "approved").length
    + items.filter(it => it.citation.reviewed && !states[it.citation.id]).length;
  const total = items.length;

  return (
    <div className="flex flex-col gap-3" style={{ height: "calc(100vh - 44px - 24px)" }}>

      {/* Header row — compact, shows task progress */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-gray-900">{t("title")}</h1>
          <p className="text-[12px] text-gray-400 mt-0.5">
            {reviewed}/{total} reviewed
          </p>
        </div>

        {/* Citation navigation */}
        <div className="flex items-center gap-1 text-[12px] text-gray-500">
          <button
            onClick={() => setIndex(i => Math.max(0, i - 1))}
            disabled={index === 0}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-1 font-medium">{index + 1} / {total}</span>
          <button
            onClick={() => setIndex(i => Math.min(total - 1, i + 1))}
            disabled={index === total - 1}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main split — flex-1 fills remaining space */}
      <div className="grid grid-cols-[5fr_7fr] gap-3 flex-1 min-h-0">
        {/* Left: AI extract — narrower, what the AI claims */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 overflow-y-auto scrollbar-thin">
          <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-3">
            AI Extract
          </p>
          <SnippetPanel citation={cur.citation} document={cur.document} />
        </div>

        {/* Right: Source — wider, ground truth */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-col">
          <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-3 shrink-0">
            {t("source.title")}
          </p>
          <div className="flex-1 min-h-0">
            <SourcePanel citation={cur.citation} document={cur.document} />
          </div>
        </div>
      </div>

      {/* Action bar — this is the DESTINATION of the visual flow */}
      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shrink-0">
        <ReviewButtons
          status={status}
          onApprove={() => setStatus("approved")}
          onFlag={() => setStatus("flagged")}
        />
      </div>
    </div>
  );
}
