import { NextRequest, NextResponse } from "next/server";
import documents from "@/src/data/mock/documents.json";
import { Document } from "@/src/types";

export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  const doc = (documents as Document[]).find((d) => d.id === params.id);
  if (!doc) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(doc);
}
