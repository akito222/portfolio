import { NextRequest, NextResponse } from "next/server";
import citations from "@/src/data/mock/citations.json";
import documents from "@/src/data/mock/documents.json";
import { Citation, Document, SearchResult } from "@/src/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get("q") ?? "").toLowerCase().trim();

  if (!q) {
    const all: SearchResult[] = (citations as Citation[]).map((c) => ({
      citation: c,
      document: (documents as Document[]).find((d) => d.id === c.doc_id)!,
    }));
    return NextResponse.json(all);
  }

  const matched = (citations as Citation[]).filter((c) => {
    const doc = (documents as Document[]).find((d) => d.id === c.doc_id);
    return (
      c.verbatim_en.toLowerCase().includes(q) ||
      c.article_en.toLowerCase().includes(q) ||
      c.indicator.toLowerCase().includes(q) ||
      doc?.title_en.toLowerCase().includes(q) ||
      doc?.country.toLowerCase().includes(q)
    );
  });

  const results: SearchResult[] = matched.map((c) => ({
    citation: c,
    document: (documents as Document[]).find((d) => d.id === c.doc_id)!,
  }));

  return NextResponse.json(results);
}
