import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata = {
  title: "ColdMail AI - Cold Email Sender",
  description: "AI-driven cold email campaign sender with pure Python validation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-800 antialiased min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
