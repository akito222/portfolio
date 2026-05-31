"use client";

import { useTranslations } from "next-intl";
import { SearchResult } from "@/src/types";
import { CheckCircle2 } from "lucide-react";

const FLAG: Record<string, string> = { JP:"🇯🇵", TH:"🇹🇭", KE:"🇰🇪", SG:"🇸🇬", BR:"🇧🇷" };

function confClass(n: number) {
  if (n >= 90) return "conf-high";
  if (n >= 80) return "conf-mid";
  return "conf-low";
}

interface SearchResultsProps {
  results: SearchResult[];
  onSelect: (r: SearchResult) => void;
}

export default function SearchResults({ results, onSelect }: SearchResultsProps) {
  const t = useTranslations("search.results");

  if (results.length === 0) {
    return (
      <div className="py-12 text-center text-[13px] text-gray-400">
        {t("noResults")}
      </div>
    );
  }

  return (
    <div>
      <p className="text-[12px] text-gray-400 mb-3">{results.length} {t("found")}</p>

      <div className="space-y-2">
        {results.map((r) => {
          const { citation: c, document: doc } = r;
          const conf = Math.round(c.confidence * 100);

          return (
            <button
              key={c.id}
              onClick={() => onSelect(r)}
              className="w-full text-left bg-white border border-gray-200 rounded-lg px-4 py-3.5 hover:border-gray-300 hover:shadow-sm transition-all group"
            >
              {/* Row 1: source meta */}
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-sm leading-none">{FLAG[doc.country_code] ?? "🌐"}</span>
                <span className="text-[12px] text-gray-500 truncate max-w-xs">{doc.title_en}</span>
                <span className="text-gray-300">·</span>
                <span className="text-[12px] text-gray-500">{c.article_en}</span>
                {/* Pillar tag */}
                {c.pillar === "Pillar 6"
                  ? <span className="tag-p6 px-1.5 py-0.5 rounded text-[11px] font-medium">{c.pillar}</span>
                  : <span className="tag-p7 px-1.5 py-0.5 rounded text-[11px] font-medium">{c.pillar}</span>
                }
                {c.reviewed && (
                  <span className="flex items-center gap-1 text-[11px] font-medium" style={{ color: "var(--c-ok)" }}>
                    <CheckCircle2 className="w-3 h-3" /> {t("reviewed")}
                  </span>
                )}
                {/* Confidence — rightmost, metric not state */}
                <span className={`ml-auto text-[13px] font-semibold tabular-nums ${confClass(conf)}`}>
                  {conf}%
                </span>
              </div>

              {/* Row 2: the actual text — this is what matters */}
              <p className="text-[13px] text-gray-800 leading-snug line-clamp-2">
                {c.verbatim_en}
              </p>

              {/* Row 3: indicator — tertiary */}
              <p className="text-[11px] text-gray-400 mt-1.5 truncate">{c.indicator}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
