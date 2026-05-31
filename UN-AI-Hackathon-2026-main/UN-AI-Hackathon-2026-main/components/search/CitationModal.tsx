"use client";

import { useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SearchResult } from "@/src/types";

const FLAG: Record<string, string> = { JP:"🇯🇵", TH:"🇹🇭", KE:"🇰🇪", SG:"🇸🇬", BR:"🇧🇷" };

interface CitationModalProps {
  result: SearchResult | null;
  onClose: () => void;
}

export default function CitationModal({ result, onClose }: CitationModalProps) {
  const t = useTranslations("search");
  if (!result) return null;
  const { citation: c, document: doc } = result;
  const conf = Math.round(c.confidence * 100);

  return (
    <Dialog open={!!result} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="bg-white border-gray-200 text-gray-900 max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            {c.pillar === "Pillar 6"
              ? <span className="tag-p6 px-1.5 py-0.5 rounded text-[11px] font-medium">{c.pillar}</span>
              : <span className="tag-p7 px-1.5 py-0.5 rounded text-[11px] font-medium">{c.pillar}</span>
            }
            {c.article_en}
            {c.section && <span className="text-gray-400 font-normal">{c.section}</span>}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 text-[13px]">
          {/* Indicator + confidence — secondary context */}
          <div className="flex items-center justify-between text-[12px] text-gray-500">
            <span>{c.indicator}</span>
            <span className={conf >= 90 ? "conf-high font-semibold" : conf >= 80 ? "conf-mid font-semibold" : "conf-low font-semibold"}>
              {conf}% confidence · {c.discovery_method}
            </span>
          </div>

          {/* Original text — primary content */}
          {c.verbatim_ja && (
            <div className="bg-gray-50 rounded-md p-3.5 border border-gray-100">
              <p className="text-[11px] text-gray-400 mb-1.5 font-medium">{t("modal.originalText")}</p>
              <p className="text-gray-700 leading-relaxed">{c.verbatim_ja}</p>
            </div>
          )}
          <div className="bg-blue-50 rounded-md p-3.5 border border-blue-100">
            <p className="text-[11px] text-blue-500 mb-1.5 font-medium">{t("modal.englishText")}</p>
            <p className="text-gray-800 leading-relaxed">{c.verbatim_en}</p>
          </div>

          {/* Source — tertiary */}
          <div className="pt-1 border-t border-gray-100 text-[12px] text-gray-500 flex items-center gap-1.5">
            <span>{FLAG[doc.country_code] ?? "🌐"}</span>
            <span className="font-medium text-gray-700 truncate">{doc.title_en}</span>
            <span>·</span>
            <span>{doc.crawled_at}</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
