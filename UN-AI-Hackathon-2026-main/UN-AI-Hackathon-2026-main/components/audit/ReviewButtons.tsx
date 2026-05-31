"use client";

import { useTranslations } from "next-intl";
import { CheckCircle, Flag } from "lucide-react";
import { ReviewStatus } from "@/src/types";

interface ReviewButtonsProps {
  status: ReviewStatus;
  onApprove: () => void;
  onFlag: () => void;
}

export default function ReviewButtons({ status, onApprove, onFlag }: ReviewButtonsProps) {
  const t = useTranslations("audit.review");

  return (
    <div className="flex items-center gap-3">
      {/* Status label — leftmost, secondary */}
      <span className="text-[12px] text-gray-400 mr-auto">
        {t("status")}:{" "}
        {status === "approved" && <span className="font-medium" style={{ color: "var(--c-ok)" }}>{t("approved")}</span>}
        {status === "flagged"  && <span className="font-medium" style={{ color: "var(--c-warn)" }}>{t("flagged")}</span>}
        {status === "pending"  && <span className="font-medium text-gray-500">{t("pending")}</span>}
      </span>

      {/* Flag — secondary action, outlined */}
      <button
        onClick={onFlag}
        className={`flex items-center gap-1.5 px-4 py-2 rounded-md border text-[13px] font-medium transition-colors ${
          status === "flagged"
            ? "border-amber-300 text-amber-700 bg-amber-50"
            : "border-gray-200 text-gray-600 bg-white hover:border-amber-300 hover:text-amber-700 hover:bg-amber-50"
        }`}
      >
        <Flag className="w-3.5 h-3.5" />
        {t("flag")}
      </button>

      {/* Approve — primary action, filled */}
      <button
        onClick={onApprove}
        className={`flex items-center gap-1.5 px-5 py-2 rounded-md text-[13px] font-medium text-white transition-colors ${
          status === "approved"
            ? "opacity-80"
            : "hover:opacity-90"
        }`}
        style={{ backgroundColor: "var(--c-ok)" }}
      >
        <CheckCircle className="w-3.5 h-3.5" />
        {t("approve")}
      </button>
    </div>
  );
}
