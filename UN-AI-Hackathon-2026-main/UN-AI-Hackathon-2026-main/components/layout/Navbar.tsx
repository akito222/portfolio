"use client";

import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

export default function Navbar({ locale }: { locale: string }) {
  const pathname = usePathname();
  const router = useRouter();

  const switchLocale = (l: string) => {
    const segs = pathname.split("/");
    segs[1] = l;
    router.push(segs.join("/"));
  };

  return (
    <header className="h-11 border-b border-gray-200 bg-white flex items-center justify-between px-5 shrink-0">
      <p className="text-[11px] text-gray-400 tracking-wide truncate max-w-sm">
        Global Hackathon on AI for Digital Trade · Demo
      </p>
      <div className="flex items-center gap-0.5">
        {(["en", "ja"] as const).map((l) => (
          <button
            key={l}
            onClick={() => switchLocale(l)}
            className={cn(
              "px-2 py-0.5 rounded text-[11px] font-medium transition-colors",
              locale === l
                ? "text-blue-700 bg-blue-50"
                : "text-gray-400 hover:text-gray-600"
            )}
          >
            {l.toUpperCase()}
          </button>
        ))}
      </div>
    </header>
  );
}
