import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "ET Investor AI",
  description: "AI-powered intelligence for Indian retail investors",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950">
        <Navbar />
        <main className="pt-14">{children}</main>
      </body>
    </html>
  );
}
