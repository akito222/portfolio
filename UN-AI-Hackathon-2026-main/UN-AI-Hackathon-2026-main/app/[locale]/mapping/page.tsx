"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Download } from "lucide-react";
import CountryRow from "@/components/mapping/CountryRow";
import { Document, Citation } from "@/src/types";

function exportCSV(documents: Document[], citations: Citation[]) {
  const rows = documents.map(doc => {
    const dc = citations.filter(c => c.doc_id === doc.id);
    const p6 = dc.some(c => c.pillar === "Pillar 6") ? "Compliant" : "Missing";
    const p7 = dc.some(c => c.pillar === "Pillar 7") || doc.pillar === "Pillar 7" ? "Partial" : "Missing";
    return [doc.country, `"${doc.title_en}"`, p6, p7, dc.length].join(",");
  });
  const csv = ["Country,Document,Pillar 6,Pillar 7,Citations", ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "pillar-mapping.csv"; a.click();
  URL.revokeObjectURL(url);
}

export default function MappingPage() {
  const t = useTranslations("mapping");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("/api/documents").then(r => r.json()),
      fetch("/api/citations").then(r => r.json()),
    ]).then(([docs, cits]) => { setDocuments(docs); setCitations(cits); })
      .catch(() => { setDocuments([]); setCitations([]); });
  }, []);

  const compliant6 = documents.filter(d => citations.some(c => c.doc_id === d.id && c.pillar === "Pillar 6")).length;
  const compliant7 = documents.filter(d => citations.some(c => c.doc_id === d.id && c.pillar === "Pillar 7") || d.pillar === "Pillar 7").length;

  return (
    <div className="max-w-4xl space-y-4">

      {/* Header with summary counts */}
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-base font-semibold text-gray-900">{t("title")}</h1>
          <p className="text-[12px] text-gray-400 mt-0.5">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-4 text-[12px] text-gray-500">
          {/* Summary inline — not cards */}
          <span>
            Pillar 6:{" "}
            <strong className="text-gray-900">{compliant6}/{documents.length}</strong> compliant
          </span>
          <span>
            Pillar 7:{" "}
            <strong className="text-gray-900">{compliant7}/{documents.length}</strong> compliant
          </span>
          <button
            onClick={() => exportCSV(documents, citations)}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-md text-gray-600 text-[12px] hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            {t("export")}
          </button>
        </div>
      </div>

      {/* Table — the page IS this table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {documents.length === 0 ? (
          <p className="px-4 py-10 text-center text-[13px] text-gray-400">No documents loaded.</p>
        ) : (
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-44">{t("table.country")}</th>
                {/* Status columns are the main data — wider */}
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-36">
                  <span className="tag-p6 px-1.5 py-0.5 rounded font-medium">{t("table.pillar6")}</span>
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-36">
                  <span className="tag-p7 px-1.5 py-0.5 rounded font-medium">{t("table.pillar7")}</span>
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-400 uppercase tracking-wide w-20">{t("table.citations")}</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {documents.map((doc, i) => (
                <CountryRow
                  key={doc.id}
                  document={doc}
                  citations={citations.filter(c => c.doc_id === doc.id)}
                  isLast={i === documents.length - 1}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
