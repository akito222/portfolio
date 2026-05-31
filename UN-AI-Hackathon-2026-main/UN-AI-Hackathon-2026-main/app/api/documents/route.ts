import { NextRequest, NextResponse } from "next/server";
import documents from "@/src/data/mock/documents.json";
import { Document } from "@/src/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const country = searchParams.get("country");
  const pillar = searchParams.get("pillar");
  const language = searchParams.get("language");

  let result: Document[] = documents as Document[];

  if (country) result = result.filter((d) => d.country === country);
  if (pillar) result = result.filter((d) => d.pillar === pillar);
  if (language) result = result.filter((d) => d.language === language);

  return NextResponse.json(result);
}
