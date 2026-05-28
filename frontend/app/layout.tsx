import type { Metadata } from 'next';
import './globals.css';

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
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="h-full overflow-hidden antialiased" style={{ background: 'var(--bg-base)' }}>
        {children}
      </body>
    </html>
  );
}
