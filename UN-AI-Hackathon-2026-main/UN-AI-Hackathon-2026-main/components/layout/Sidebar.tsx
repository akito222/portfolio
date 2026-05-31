"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Search, ClipboardCheck, Map } from "lucide-react";

const navItems = [
  { key: "dashboard", href: "", icon: LayoutDashboard },
  { key: "search",    href: "/search", icon: Search },
  { key: "audit",     href: "/audit",  icon: ClipboardCheck },
  { key: "mapping",   href: "/mapping", icon: Map },
] as const;

export default function Sidebar({ locale }: { locale: string }) {
  const t = useTranslations("nav");
  const pathname = usePathname();

  return (
    <aside className="w-52 shrink-0 flex flex-col border-r border-gray-200 bg-white">
      {/* Brand — uses brand color only */}
      <div className="px-4 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded flex items-center justify-center shrink-0 text-white font-bold text-[9px] tracking-tight"
            style={{ backgroundColor: "var(--c-brand)" }}
          >
            UN
          </div>
          <span className="text-xs font-semibold text-gray-700 leading-tight">
            RDTII Regulatory<br />Analysis
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {navItems.map(({ key, href, icon: Icon }) => {
          const fullHref = `/${locale}${href}`;
          const isActive = pathname === fullHref || (href === "" && pathname === `/${locale}`);
          return (
            <Link
              key={key}
              href={fullHref}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-800"
              )}
            >
              <Icon className={cn("w-3.5 h-3.5 shrink-0", isActive ? "text-blue-600" : "text-gray-400")} />
              {t(key)}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
