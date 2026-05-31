const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function fetchDocuments(params?: {
  country?: string;
  pillar?: string;
  language?: string;
}) {
  const query = new URLSearchParams();
  if (params?.country) query.set("country", params.country);
  if (params?.pillar) query.set("pillar", params.pillar);
  if (params?.language) query.set("language", params.language);
  const res = await fetch(`${BASE_URL}/api/documents?${query}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function fetchDocument(id: string) {
  const res = await fetch(`${BASE_URL}/api/documents/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch document");
  return res.json();
}

export async function fetchCitations(params?: { pillar?: string; doc_id?: string }) {
  const query = new URLSearchParams();
  if (params?.pillar) query.set("pillar", params.pillar);
  if (params?.doc_id) query.set("doc_id", params.doc_id);
  const res = await fetch(`${BASE_URL}/api/citations?${query}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch citations");
  return res.json();
}

export async function searchDocuments(q: string) {
  const res = await fetch(`${BASE_URL}/api/search?q=${encodeURIComponent(q)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to search");
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/api/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}
