import { getTranslations } from "next-intl/server";
import rawDocuments from "@/src/data/mock/documents.json";
import rawCitations from "@/src/data/mock/citations.json";
import { Document, Citation } from "@/src/types";

const FLAG: Record<string, string> = { JP:"🇯🇵", TH:"🇹🇭", KE:"🇰🇪", SG:"🇸🇬", BR:"🇧🇷" };

function pillarTag(pillar: string) {
  return pillar === "Pillar 6"
    ? <span className="tag-p6 inline-flex px-1.5 py-0.5 rounded text-[11px] font-medium">{pillar}</span>
    : <span className="tag-p7 inline-flex px-1.5 py-0.5 rounded text-[11px] font-medium">{pillar}</span>;
}

export default async function DashboardPage() {
  const t  = await getTranslations("dashboard");
  const tr = await getTranslations("dashboard.recent");

  const documents = rawDocuments as Document[];
  const citations = rawCitations as Citation[];

  const stats = {
    total_documents:   documents.length,
    total_countries:   new Set(documents.map(d => d.country_code)).size,
    total_citations:   citations.length,
    reviewed_citations: citations.filter(c => c.reviewed).length,
  };

  return (
    <div className="max-w-5xl space-y-5">

      {/* Page header — stats live here, not in separate cards */}
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-base font-semibold text-gray-900">{t("title")}</h1>
        <dl className="flex items-center gap-5 text-[13px] text-gray-500 shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold text-gray-900 leading-none">{stats.total_documents}</span>
            <dt>{t("stats.documents")}</dt>
          </div>
          <span className="text-gray-300">·</span>
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold text-gray-900 leading-none">{stats.total_countries}</span>
            <dt>{t("stats.countries")}</dt>
          </div>
          <span className="text-gray-300">·</span>
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold text-gray-900 leading-none">{stats.total_citations}</span>
            <dt>{t("stats.citations")}</dt>
          </div>
          <span className="text-gray-300">·</span>
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold leading-none" style={{ color: "var(--c-ok)" }}>
              {stats.reviewed_citations}
            </span>
            <dt>{t("stats.reviewed")}</dt>
          </div>
        </dl>
      </div>

      {/* Documents table — this IS the page */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-36">{tr("country")}</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide">{tr("document")}</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-24">{tr("pillar")}</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-28">{tr("crawled")}</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-24">{tr("status")}</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-gray-400">No documents indexed yet.</td>
              </tr>
            )}
            {documents.map((doc, i) => (
              <tr key={doc.id} className={`hover:bg-gray-50 transition-colors ${i < documents.length - 1 ? "border-b border-gray-100" : ""}`}>
                <td className="px-4 py-3 text-gray-700 font-medium">
                  <span className="mr-1.5">{FLAG[doc.country_code] ?? "🌐"}</span>
                  {doc.country}
                </td>
                <td className="px-4 py-3">
                  <p className="text-gray-900 font-medium truncate max-w-sm">{doc.title_en}</p>
                  {doc.language !== "en" && doc.title !== doc.title_en && (
                    <p className="text-gray-400 text-[12px] truncate max-w-sm mt-0.5">{doc.title}</p>
                  )}
                </td>
                <td className="px-4 py-3">{pillarTag(doc.pillar)}</td>
                <td className="px-4 py-3 text-gray-400">{doc.crawled_at}</td>
                <td className="px-4 py-3">
                  <span className="badge-ok inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium capitalize">
                    {doc.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* System status — 1 line, tertiary info */}
      <p className="text-[12px] text-gray-400 px-0.5">
        Crawler <span className="text-emerald-600 font-medium">operational</span>
        {" · "}Index <span className="text-emerald-600 font-medium">up to date</span>
        {" · "}API <span className="text-emerald-600 font-medium">operational</span>
      </p>
    </div>
  );
}
