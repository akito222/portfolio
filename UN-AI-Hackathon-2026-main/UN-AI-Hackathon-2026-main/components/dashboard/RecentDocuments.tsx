import { useTranslations } from "next-intl";
import { Document } from "@/src/types";

const FLAG_MAP: Record<string, string> = {
  JP: "🇯🇵", TH: "🇹🇭", KE: "🇰🇪", SG: "🇸🇬", BR: "🇧🇷",
};

interface RecentDocumentsProps {
  documents: Document[];
}

export default function RecentDocuments({ documents }: RecentDocumentsProps) {
  const t = useTranslations("dashboard.recent");

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-900">{t("title")}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{t("country")}</th>
              <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{t("document")}</th>
              <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{t("pillar")}</th>
              <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{t("crawled")}</th>
              <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{t("status")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-3.5 text-gray-900 font-medium text-sm">
                  <span className="mr-2">{FLAG_MAP[doc.country_code] ?? "🌐"}</span>
                  {doc.country}
                </td>
                <td className="px-5 py-3.5">
                  <p className="text-gray-900 font-medium truncate max-w-xs text-sm">{doc.title_en}</p>
                  {doc.language !== "en" && (
                    <p className="text-gray-400 text-xs truncate max-w-xs mt-0.5">{doc.title}</p>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    doc.pillar === "Pillar 6"
                      ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-blue-50 text-blue-700 border border-blue-200"
                  }`}>
                    {doc.pillar}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-gray-400 text-xs">{doc.crawled_at}</td>
                <td className="px-5 py-3.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-emerald-600 text-xs font-medium capitalize">{doc.status}</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
