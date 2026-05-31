import { NextRequest, NextResponse } from "next/server";
import citations from "@/src/data/mock/citations.json";
import { Citation } from "@/src/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const pillar = searchParams.get("pillar");
  const doc_id = searchParams.get("doc_id");

  let result: Citation[] = citations as Citation[];

  if (pillar) result = result.filter((c) => c.pillar === pillar);
  if (doc_id) result = result.filter((c) => c.doc_id === doc_id);

  return NextResponse.json(result);
}
