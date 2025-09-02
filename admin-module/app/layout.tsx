import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import NavbarWrapper from "@/components/navbar-wrapper";

export const metadata: Metadata = {
  title: "Admin Module",
  description: "CGIAR AI Services Admin Module",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="font-sans">
        <NavbarWrapper />
        {children}
      </body>
    </html>
  );
}
