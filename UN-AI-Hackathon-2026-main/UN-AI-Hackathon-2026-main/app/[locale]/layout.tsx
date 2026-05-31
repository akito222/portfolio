import type { Metadata } from "next";
import localFont from "next/font/local";
import { Noto_Sans_JP } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/src/i18n/routing";
import Sidebar from "@/components/layout/Sidebar";
import Navbar from "@/components/layout/Navbar";
import "../globals.css";

const geist = localFont({
  src: "../fonts/GeistVF.woff",
  variable: "--font-geist",
  weight: "100 900",
});
const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  variable: "--font-noto-jp",
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "UN Trade AI — RDTII Regulatory Analysis",
  description: "AI-powered regulatory document analysis for UN digital trade standards",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  const { locale } = params;
  if (!routing.locales.includes(locale as "en" | "ja")) notFound();

  const messages = await getMessages();

  return (
    <html lang={locale} className={`${geist.variable} ${notoSansJP.variable}`}>
      <body className="antialiased bg-gray-50 text-gray-900">
        <NextIntlClientProvider messages={messages}>
          <div className="flex h-screen overflow-hidden">
            <Sidebar locale={locale} />
            <div className="flex flex-col flex-1 overflow-hidden">
              <Navbar locale={locale} />
              <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                {children}
              </main>
            </div>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
