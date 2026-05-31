import { Citation, Document } from "@/src/types";
import { ExternalLink } from "lucide-react";

const MOCK: Record<string, string> = {
  doc_001: `個人情報の保護に関する法律

第1条（目的）
この法律は、高度情報通信社会の進展に伴い個人情報の利用が著しく拡大していることに鑑み、個人情報の適正な取扱いに関し、基本理念及び政府による基本方針の作成その他の個人情報の保護に関する施策の基本となる事項を定め、国及び地方公共団体の責務等を明らかにし、個人情報を取り扱う事業者の遵守すべき義務等を定める。

第24条（外国にある第三者への提供の制限）
個人情報取扱事業者は、外国にある第三者に個人データを提供する場合には、あらかじめ外国にある第三者への提供を認める旨の本人の同意を得なければならない。ただし、次に掲げる場合はこの限りでない。
一 法令に基づく場合
二 人の生命、身体又は財産の保護のために必要がある場合であって、本人の同意を得ることが困難であるとき。`,
  doc_002: `Personal Data Protection Act B.E. 2562

Section 37: The data controller shall notify the data subject of the purpose of collection, use and disclosure of personal data. The notification shall be made prior to or at the time of collection of personal data, unless the data subject already knows such purposes.

The data controller shall also provide the data subject with information on the retention period of personal data, the rights of the data subject, and contact information of the data controller.`,
  doc_003: `Data Protection Act, 2019

Section 48 (1): A data controller shall not transfer personal data to a foreign country or international organisation unless the country or international organisation ensures an adequate level of data protection.

(2) Notwithstanding subsection (1), a data controller may transfer personal data to a foreign country or international organisation where:
(a) the data subject has given consent to the proposed transfer;
(b) the transfer is necessary for the performance of a contract.`,
};

function renderHighlighted(text: string, needle: string): React.ReactNode[] {
  const key = needle.toLowerCase().slice(0, 40);
  const idx = text.toLowerCase().indexOf(key);
  if (idx === -1) return [text];
  return [
    text.slice(0, idx),
    <mark key="h" className="bg-yellow-100 text-yellow-900 rounded-sm">{text.slice(idx, idx + needle.length)}</mark>,
    text.slice(idx + needle.length),
  ];
}

export default function SourcePanel({ citation, document }: { citation: Citation; document: Document }) {
  const fullText = MOCK[document.id] ?? document.title_en;
  const highlighted = renderHighlighted(fullText, citation.verbatim_en.slice(0, 60));

  return (
    <div className="h-full flex flex-col gap-3">
      {/* Source header */}
      <div className="flex items-start justify-between gap-2 shrink-0">
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-gray-900 truncate">{document.title_en}</p>
          <p className="text-[12px] text-gray-400 mt-0.5">{document.country} · {document.crawled_at}</p>
        </div>
        <a
          href={document.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 flex items-center gap-1 text-[11px] text-blue-600 hover:underline"
        >
          <ExternalLink className="w-3 h-3" /> Source
        </a>
      </div>

      {/* Document text */}
      <div className="flex-1 min-h-0 bg-gray-50 border border-gray-100 rounded-md p-4 overflow-y-auto scrollbar-thin">
        <pre className="whitespace-pre-wrap font-mono text-[12px] text-gray-600 leading-relaxed">{highlighted}</pre>
      </div>

      <p className="text-[11px] text-gray-400 shrink-0 flex items-center gap-1.5">
        <mark className="bg-yellow-100 text-yellow-700 rounded-sm px-1">■</mark>
        Highlighted match
      </p>
    </div>
  );
}
