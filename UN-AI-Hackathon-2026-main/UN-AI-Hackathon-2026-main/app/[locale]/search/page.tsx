"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import SearchBar from "@/components/search/SearchBar";
import SearchFilters from "@/components/search/SearchFilters";
import SearchResults from "@/components/search/SearchResults";
import CitationModal from "@/components/search/CitationModal";
import { SearchResult } from "@/src/types";

interface Filters { country: string; language: string; pillar: string; }

export default function SearchPage() {
  const t = useTranslations("search");
  const [query, setQuery]   = useState("");
  const [filters, setFilters] = useState<Filters>({ country: "", language: "", pillar: "" });
  const [all, setAll]       = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);

  useEffect(() => {
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
      .then(setAll)
      .catch(() => setAll([]));
  }, [query]);

  const results = all.filter(r => {
    if (filters.country  && r.document.country  !== filters.country)  return false;
    if (filters.language && r.document.language !== filters.language) return false;
    if (filters.pillar   && r.citation.pillar   !== filters.pillar)   return false;
    return true;
  });

  return (
    <div className="max-w-3xl space-y-3">
      {/* Title */}
      <div className="mb-4">
        <h1 className="text-base font-semibold text-gray-900">{t("title")}</h1>
        <p className="text-[12px] text-gray-400 mt-0.5">{t("subtitle")}</p>
      </div>

      {/* Search input — the entry point of this page */}
      <SearchBar onSearch={setQuery} />

      {/* Filters — secondary, compact */}
      <SearchFilters filters={filters} onChange={setFilters} />

      {/* Results */}
      <SearchResults results={results} onSelect={setSelected} />

      <CitationModal result={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
