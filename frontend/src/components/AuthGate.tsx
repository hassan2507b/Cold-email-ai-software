"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { checkSession } from "@/lib/api";
import { Navbar } from "@/components/Navbar";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (pathname === "/login") {
      setChecking(false);
      return;
    }

    let active = true;
    setChecking(true);
    checkSession()
      .then((valid) => {
        if (!active) return;
        if (!valid) {
          router.replace("/login");
          return;
        }
        setAuthenticated(true);
        setChecking(false);
      })
      .catch(() => {
        if (active) {
          setAuthenticated(false);
          router.replace("/login");
        }
      });

    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (pathname === "/login") return <>{children}</>;
  if (checking || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-slate-500">
        Checking your session...
      </div>
    );
  }

  return (
    <>
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {children}
      </main>
    </>
  );
}
