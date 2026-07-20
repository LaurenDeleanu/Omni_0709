import { NextRequest } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';
import { auth0 } from './lib/auth0';

const intlMiddleware = createMiddleware(routing);

export default async function middleware(request: NextRequest) {
  // Auth0 v4 sirve /auth/login, /auth/logout, /auth/callback, etc. desde su
  // propio middleware; sin esto, next-intl redirige /auth/* a /{locale}/auth/* (404).
  if (request.nextUrl.pathname.startsWith('/auth/')) {
    return auth0.middleware(request);
  }
  return intlMiddleware(request);
}

export const config = {
  // Match only internationalized pathnames + Auth0 routes
  matcher: ['/', '/(es|en|fr|de|pt|ar)/:path*', '/((?!api|_next|_vercel|.*\\..*).*)']
};
