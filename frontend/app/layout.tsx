import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';
import { Providers } from './providers';

const geistSans = localFont({
  src: './fonts/GeistVF.woff',
  variable: '--font-sans',
  display: 'swap',
});

const geistMono = localFont({
  src: './fonts/GeistMonoVF.woff',
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'AI Website Generator — Build Stunning Sites with AI',
  description:
    'Generate beautiful, responsive websites instantly using AI. Describe your site in plain English and watch it come to life with real-time streaming preview.',
  keywords: ['AI website generator', 'AI design', 'Tailwind CSS', 'HTML generator', 'LangChain'],
  authors: [{ name: 'AI Site Generator' }],
  openGraph: {
    title: 'AI Website Generator',
    description: 'Generate stunning websites with AI in seconds.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="h-full overflow-hidden antialiased" style={{ background: 'var(--bg-base)' }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
