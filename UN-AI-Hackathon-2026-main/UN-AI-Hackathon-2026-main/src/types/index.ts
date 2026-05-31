export interface Document {
  id: string;
  country: string;
  country_code: string;
  language: string;
  title: string;
  title_en: string;
  source_url: string;
  crawled_at: string;
  pillar: "Pillar 6" | "Pillar 7";
  status: "indexed" | "pending" | "error";
}

export interface Citation {
  id: string;
  doc_id: string;
  article: string;
  article_en: string;
  section: string | null;
  verbatim_ja: string | null;
  verbatim_en: string;
  pillar: "Pillar 6" | "Pillar 7";
  indicator: string;
  confidence: number;
  discovery_method: "semantic" | "keyword";
  reviewed: boolean;
}

export interface Stats {
  total_documents: number;
  total_countries: number;
  total_citations: number;
  reviewed_citations: number;
}

export interface SearchResult {
  citation: Citation;
  document: Document;
}

export type ReviewStatus = "approved" | "flagged" | "pending";
