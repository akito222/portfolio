"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import PillarBadge from "./PillarBadge";
import { Citation, Document } from "@/src/types";

const FLAG: Record<string, string> = { JP:"🇯🇵", TH:"🇹🇭", KE:"🇰🇪", SG:"🇸🇬", BR:"🇧🇷" };

interface CountryRowProps { document: Document; citations: Citation[]; isLast: boolean; }

export default function CountryRow({ document: doc, citations, isLast }: CountryRowProps) {
  const [open, setOpen] = useState(false);

  const p6Level = citations.some(c => c.pillar === "Pillar 6") ? "compliant" : "missing";
  const p7Level = citations.some(c => c.pillar === "Pillar 7") ? "compliant"
                : doc.pillar === "Pillar 7" ? "partial" : "missing";

  return (
    <>
      <tr
        className={`hover:bg-gray-50 cursor-pointer transition-colors ${!isLast || open ? "border-b border-gray-100" : ""}`}
        onClick={() => setOpen(o => !o)}
      >
        <td className="px-4 py-3 w-44">
          <div className="flex items-center gap-2">
            <span className="text-base leading-none">{FLAG[doc.country_code] ?? "🌐"}</span>
            <span className="text-[13px] font-medium text-gray-900">{doc.country}</span>
          </div>
        </td>
        {/* Pillar columns — the heroes */}
        <td className="px-4 py-3 w-36"><PillarBadge level={p6Level} /></td>
        <td className="px-4 py-3 w-36"><PillarBadge level={p7Level} /></td>
        {/* Secondary data */}
        <td className="px-4 py-3 text-[12px] text-gray-400 w-20">{citations.length || "—"}</td>
        <td className="px-4 py-3 w-8 text-gray-300">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </td>
      </tr>

      {/* Drill-down: citations for this country */}
      {open && (
        <tr className={`bg-gray-50 ${!isLast ? "border-b border-gray-100" : ""}`}>
          <td colSpan={5} className="px-6 py-3">
            {citations.length === 0 ? (
              <p className="text-[12px] text-gray-400 py-1">No citations mapped for this document.</p>
            ) : (
              <div className="space-y-1.5">
                {citations.map(c => {
                  const conf = Math.round(c.confidence * 100);
                  return (
                    <div key={c.id} className="flex items-start gap-3 text-[12px] bg-white border border-gray-100 rounded px-3 py-2">
                      {c.pillar === "Pillar 6"
                        ? <span className="tag-p6 px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0">{c.pillar}</span>
                        : <span className="tag-p7 px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0">{c.pillar}</span>
                      }
                      <span className="text-gray-500 shrink-0 font-mono">{c.article_en}</span>
                      <span className="text-gray-700 flex-1 truncate">{c.indicator}</span>
                      <span className={`shrink-0 font-semibold tabular-nums ${conf >= 90 ? "conf-high" : conf >= 80 ? "conf-mid" : "conf-low"}`}>
                        {conf}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
