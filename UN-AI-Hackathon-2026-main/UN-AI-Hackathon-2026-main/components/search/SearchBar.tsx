"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";

interface SearchBarProps {
  onSearch: (q: string) => void;
  initialValue?: string;
}

export default function SearchBar({ onSearch, initialValue = "" }: SearchBarProps) {
  const t = useTranslations("search");
  const [value, setValue] = useState(initialValue);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(value);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("placeholder")}
          className="w-full pl-11 pr-28 py-3 bg-white border border-gray-200 rounded-lg text-[13px] text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-[12px] font-medium text-white rounded transition"
          style={{ backgroundColor: "var(--c-action)" }}
          onMouseOver={e => (e.currentTarget.style.backgroundColor = "var(--c-action-h)")}
          onMouseOut={e => (e.currentTarget.style.backgroundColor = "var(--c-action)")}
        >
          Search
        </button>
      </div>
    </form>
  );
}
