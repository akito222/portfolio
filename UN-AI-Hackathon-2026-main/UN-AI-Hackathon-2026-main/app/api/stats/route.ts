import { NextResponse } from "next/server";
import citations from "@/src/data/mock/citations.json";
import documents from "@/src/data/mock/documents.json";
import { Citation, Document, Stats } from "@/src/types";

export async function GET() {
  const docs = documents as Document[];
  const cits = citations as Citation[];

  const stats: Stats = {
    total_documents: docs.length,
    total_countries: new Set(docs.map((d) => d.country_code)).size,
    total_citations: cits.length,
    reviewed_citations: cits.filter((c) => c.reviewed).length,
  };

  return NextResponse.json(stats);
}
