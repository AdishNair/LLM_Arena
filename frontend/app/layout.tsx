import './globals.css';

import type { Metadata } from 'next';

import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'LLM Arena',
  description: 'Multi-model discussion and evaluation platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
