import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../globals.css";
import { Providers } from "@/providers";
import { Toaster } from "sonner";
import { PWARegister } from "@/components/PWARegister";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "SuccessCore HR | Plataforma HR con Agentes de IA",
    template: "%s | SuccessCore HR",
  },
  description:
    "SuccessCore HR es la primera plataforma SaaS de gestión de recursos humanos con 10 agentes de IA nativos. Automatiza nóminas, reclutamiento, compliance, formación y más. 28 módulos integrados. Prueba gratuita.",
  keywords: [
    "HR software",
    "gestión de RRHH",
    "agentes IA",
    "inteligencia artificial RRHH",
    "nóminas",
    "reclutamiento ATS",
    "control horario",
    "compliance GDPR",
    "FUNDAE",
    "people analytics",
    "HR SaaS",
    "software RRHH España",
    "plataforma RRHH",
  ],
  authors: [{ name: "SuccessCore HR" }],
  creator: "SuccessCore HR",
  publisher: "SuccessCore HR",
  metadataBase: new URL("https://successcore.com"),
  openGraph: {
    type: "website",
    locale: "es_ES",
    alternateLocale: ["en_US", "fr_FR", "de_DE", "pt_PT", "ar_SA"],
    siteName: "SuccessCore HR",
    title: "SuccessCore HR | Plataforma HR con 10 Agentes de IA",
    description:
      "La primera plataforma SaaS de RRHH con agentes de inteligencia artificial nativos. 28 módulos, multi-idioma, multi-tenant. Automatiza el 60% del trabajo administrativo de RRHH.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "SuccessCore HR - Plataforma HR con IA",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SuccessCore HR | Plataforma HR con Agentes de IA",
    description:
      "La primera plataforma SaaS de RRHH con agentes de inteligencia artificial nativos.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  manifest: "/manifest.json",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
};

export default async function RootLayout({
  children,
  params
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}>) {
  const {locale} = await params;
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }
  const messages = await getMessages();

  return (
    <html lang={locale} dir={locale === 'ar' ? 'rtl' : 'ltr'} suppressHydrationWarning>
      <body
        className={`${inter.variable} font-sans antialiased min-h-screen flex flex-col`}
      >
        <NextIntlClientProvider messages={messages}>
          <Providers>
              <PWARegister />
              {children}
              <Toaster position="top-right" />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
