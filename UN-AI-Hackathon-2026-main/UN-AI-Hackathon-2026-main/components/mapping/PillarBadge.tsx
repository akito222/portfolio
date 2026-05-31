import { useTranslations } from "next-intl";
import { Check, Minus, AlertTriangle } from "lucide-react";

type Level = "compliant" | "partial" | "missing";

export default function PillarBadge({ level }: { level: Level }) {
  const t = useTranslations("mapping.status");

  if (level === "compliant") {
    return (
      <span className="badge-ok inline-flex items-center gap-1 px-2 py-0.5 rounded text-[12px] font-medium">
        <Check className="w-3 h-3" />
        {t("compliant")}
      </span>
    );
  }
  if (level === "partial") {
    return (
      <span className="badge-warn inline-flex items-center gap-1 px-2 py-0.5 rounded text-[12px] font-medium">
        <AlertTriangle className="w-3 h-3" />
        {t("partial")}
      </span>
    );
  }
  return (
    <span className="badge-neutral inline-flex items-center gap-1 px-2 py-0.5 rounded text-[12px] font-medium">
      <Minus className="w-3 h-3" />
      {t("missing")}
    </span>
  );
}
