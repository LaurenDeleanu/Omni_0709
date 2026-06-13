/**
 * [auth0]/route.ts — Auth handlers
 *
 * En Auth0 v4, las rutas de auth son gestionadas por el middleware (src/middleware.ts).
 * El middleware intercepta /api/auth/* ANTES de que llegue aquí.
 * Estos handlers son solo fallback — en runtime no se ejecutan.
 */
import { NextRequest, NextResponse } from "next/server";

export async function GET(_req: NextRequest) {
  return NextResponse.json({ error: "Auth handled by middleware" }, { status: 404 });
}

export async function POST(_req: NextRequest) {
  return NextResponse.json({ error: "Auth handled by middleware" }, { status: 404 });
}
