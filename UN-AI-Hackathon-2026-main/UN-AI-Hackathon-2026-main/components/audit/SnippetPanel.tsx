import { useTranslations } from "next-intl";
import { Citation, Document } from "@/src/types";

interface SnippetPanelProps {
  citation: Citation;
  document: Document;
}

export default function SnippetPanel({ citation, document }: SnippetPanelProps) {
  const t  = useTranslations("audit.snippet");
  const tc = useTranslations("common");
  const conf = Math.round(citation.confidence * 100);

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Pillar + article — quick context */}
      <div className="flex items-center gap-2 text-[12px] text-gray-500">
        {citation.pillar === "Pillar 6"
          ? <span className="tag-p6 px-1.5 py-0.5 rounded text-[11px] font-medium">{citation.pillar}</span>
          : <span className="tag-p7 px-1.5 py-0.5 rounded text-[11px] font-medium">{citation.pillar}</span>
        }
        <span className="font-medium text-gray-700">{citation.article_en}</span>
        {citation.section && <span>{citation.section}</span>}
        <span>·</span>
        <span>{document.country}</span>
      </div>

      {/* The extracted text — PRIMARY content of this panel */}
      <div className="flex-1 flex flex-col gap-3 min-h-0">
        {citation.verbatim_ja && (
          <div className="bg-gray-50 rounded-md p-4 border border-gray-100">
            <p className="text-[11px] text-gray-400 mb-2 font-medium">{t("original")}</p>
            <p className="text-[13px] text-gray-700 leading-relaxed">{citation.verbatim_ja}</p>
          </div>
        )}
        <div className="bg-blue-50 rounded-md p-4 border border-blue-100 flex-1">
          <p className="text-[11px] text-blue-500 mb-2 font-medium">{t("english")}</p>
          <p className="text-[13px] text-gray-800 leading-relaxed">{citation.verbatim_en}</p>
        </div>
      </div>

      {/* Metadata — tertiary, below the text */}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px] pt-3 border-t border-gray-100">
        <div>
          <dt className="text-gray-400">{t("indicator")}</dt>
          <dd className="text-gray-700 font-medium truncate mt-0.5">{citation.indicator}</dd>
        </div>
        <div>
          <dt className="text-gray-400">{t("confidence")}</dt>
          <dd className={`font-semibold mt-0.5 ${conf >= 90 ? "conf-high" : conf >= 80 ? "conf-mid" : "conf-low"}`}>
            {conf}%
          </dd>
        </div>
        <div>
          <dt className="text-gray-400">{t("method")}</dt>
          <dd className="text-gray-700 mt-0.5 capitalize">
            {citation.discovery_method === "semantic" ? tc("semantic") : tc("keyword")}
          </dd>
        </div>
        <div>
          <dt className="text-gray-400">{t("pillarTag")}</dt>
          <dd className="text-gray-700 mt-0.5">{citation.pillar}</dd>
        </div>
      </dl>
    </div>
  );
}
