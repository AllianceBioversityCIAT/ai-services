import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import Navbar from '@/components/navbar';
import { getSession } from '@/lib/auth';

export const metadata: Metadata = {
  title: 'v0 App',
  description: 'Created with v0',
  generator: 'v0.app',
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  // Detectar si el usuario es admin (server component)
  // NOTA: Si el layout no puede ser async, se puede usar un Client Component wrapper para Navbar
  let isAdmin = false;
  try {
    const session = await getSession();
    isAdmin = session?.role === 'admin';
  } catch {}

  return (
    <html lang="en">
      <head>
        <style>{`
html {
  font-family: ${GeistSans.style.fontFamily};
  --font-sans: ${GeistSans.variable};
  --font-mono: ${GeistMono.variable};
}
        `}</style>
      </head>
      <body>
        <Navbar isAdmin={isAdmin} />
        {children}
      </body>
    </html>
  );
}
