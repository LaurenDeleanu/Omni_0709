import { NextRequest } from "next/server";
import { auth0 } from "@/lib/auth0";

export const GET = (req: NextRequest) => auth0.middleware(req);
export const POST = (req: NextRequest) => auth0.middleware(req);
