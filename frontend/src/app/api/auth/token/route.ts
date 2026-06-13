/**
 * Token endpoint — devuelve el access token de Auth0 v4 para el frontend.
 * Se llama desde el interceptor de Axios en api.ts.
 *
 * auth0.getAccessToken() retorna { token: string } en v4.
 */
import { auth0 } from "@/lib/auth0";
import { NextResponse } from "next/server";

export async function GET() {
  if (process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true") {
    return NextResponse.json({ accessToken: null, mock: true });
  }

  try {
    const result = await auth0.getAccessToken();
    // v4 devuelve { token } — lo renombramos a accessToken para api.ts
    return NextResponse.json({ accessToken: (result as { token: string }).token });
  } catch {
    return NextResponse.json(
      { error: "No autenticado o sesión expirada." },
      { status: 401 }
    );
  }
}
