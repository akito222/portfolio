"use client";

import { useTranslations } from "next-intl";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface FilterState {
  country: string;
  language: string;
  pillar: string;
}

interface SearchFiltersProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
}

const COUNTRIES = ["Japan", "Thailand", "Kenya", "Singapore", "Brazil"];
const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "th", label: "Thai" },
  { value: "pt", label: "Português" },
];

export default function SearchFilters({ filters, onChange }: SearchFiltersProps) {
  const t = useTranslations("search.filters");

  const set = (key: keyof FilterState) => (val: string | null) =>
    onChange({ ...filters, [key]: !val || val === "all" ? "" : val });

  return (
    <div className="flex gap-2 flex-wrap">
      <Select value={filters.country || "all"} onValueChange={set("country")}>
        <SelectTrigger className="w-36 h-8 text-xs bg-white border-gray-200 text-gray-700 shadow-sm">
          <SelectValue placeholder={t("allCountries")} />
        </SelectTrigger>
        <SelectContent className="bg-white border-gray-200 text-gray-800 text-sm">
          <SelectItem value="all">{t("allCountries")}</SelectItem>
          {COUNTRIES.map((c) => (
            <SelectItem key={c} value={c}>{c}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={filters.language || "all"} onValueChange={set("language")}>
        <SelectTrigger className="w-36 h-8 text-xs bg-white border-gray-200 text-gray-700 shadow-sm">
          <SelectValue placeholder={t("allLanguages")} />
        </SelectTrigger>
        <SelectContent className="bg-white border-gray-200 text-gray-800 text-sm">
          <SelectItem value="all">{t("allLanguages")}</SelectItem>
          {LANGUAGES.map((l) => (
            <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={filters.pillar || "all"} onValueChange={set("pillar")}>
        <SelectTrigger className="w-36 h-8 text-xs bg-white border-gray-200 text-gray-700 shadow-sm">
          <SelectValue placeholder={t("allPillars")} />
        </SelectTrigger>
        <SelectContent className="bg-white border-gray-200 text-gray-800 text-sm">
          <SelectItem value="all">{t("allPillars")}</SelectItem>
          <SelectItem value="Pillar 6">Pillar 6</SelectItem>
          <SelectItem value="Pillar 7">Pillar 7</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
