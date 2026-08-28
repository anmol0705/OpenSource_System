import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Enterprise Support Agent",
  description: "Find an issue, investigate it, get mentored through the fix, ship the PR.",
};

const NAV_ITEMS = [
  { href: "/profile", label: "Profile" },
  { href: "/discover", label: "Discover" },
  { href: "/investigate", label: "Investigate" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-slate-950 text-slate-100 min-h-screen`}
      >
        <header className="border-b border-slate-800 bg-slate-900/60">
          <nav className="mx-auto max-w-6xl px-4 py-3 flex items-center gap-6">
            <span className="font-semibold text-slate-200 tracking-tight">
              Support Agent
            </span>
            <div className="flex gap-4 text-sm">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-slate-400 hover:text-slate-100 transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
