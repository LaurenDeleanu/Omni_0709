"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0/client";
import { useEffect, useState } from "react";
import { UserAPI } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";

const isAuth0Configured = !!(
  process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID && process.env.NEXT_PUBLIC_AUTH0_DOMAIN
);

function useLocalUserSession() {
  const [user, setUser] = useState<any>(undefined);
  const [isLoading, setIsLoading] = useState(true);

  const checkSession = async () => {
    // 1. Initial sync load from sessionStorage
    if (typeof window !== "undefined") {
      const userStr = sessionStorage.getItem("local_user");
      if (userStr) {
        try {
          setUser(JSON.parse(userStr));
          setIsLoading(false);
        } catch {
          sessionStorage.removeItem("local_user");
        }
      }
    }

    // 2. Fetch from backend to verify and update
    try {
      const freshUser = await UserAPI.getMe();
      setUser(freshUser);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("local_user", JSON.stringify(freshUser));
      }
    } catch (err: any) {
      setUser(null);
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("local_user");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkSession();
  }, []);

  const invalidate = async () => {
    try {
      const freshUser = await UserAPI.getMe();
      setUser(freshUser);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("local_user", JSON.stringify(freshUser));
      }
      return freshUser;
    } catch {
      setUser(null);
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("local_user");
      }
    }
  };

  const logout = async () => {
    await fetch(`${API_BASE}/users/logout`, {
      method: "POST",
      credentials: "include",
    }).catch(() => {});
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("local_user");
    }
    setUser(null);
    window.location.href = "/login";
  };

  return { user, error: undefined, isLoading, invalidate, logout };
}

function useAuth0UserSession() {
  const auth0 = useAuth0User();
  const [localUser, setLocalUser] = useState<any>(null);
  const [isLocalLoading, setIsLocalLoading] = useState(true);

  const checkLocalUser = () => {
    if (typeof window !== "undefined") {
      const userStr = sessionStorage.getItem("local_user");
      if (userStr) {
        try {
          setLocalUser(JSON.parse(userStr));
        } catch {
          sessionStorage.removeItem("local_user");
          setLocalUser(null);
        }
      } else {
        setLocalUser(null);
      }
      setIsLocalLoading(false);
    }
  };

  useEffect(() => {
    checkLocalUser();
  }, []);

  const invalidate = async () => {
    if (typeof window !== "undefined") {
      const userStr = sessionStorage.getItem("local_user");
      if (userStr) {
        try {
          const userObj = JSON.parse(userStr);
          const res = await fetch(`${API_BASE}/users/${userObj.id}`, {
            credentials: "include",
          });
          if (res.ok) {
            const updatedUser = await res.json();
            sessionStorage.setItem("local_user", JSON.stringify(updatedUser));
            setLocalUser(updatedUser);
            return updatedUser;
          }
        } catch (e) {
          console.error("Error invalidating user session:", e);
        }
      }
    }

    if (auth0 && typeof (auth0 as any).checkSession === "function") {
      return (auth0 as any).checkSession();
    }
  };

  const logout = async () => {
    await fetch(`${API_BASE}/users/logout`, {
      method: "POST",
      credentials: "include",
    }).catch(() => {});
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("local_user");
    }
    setLocalUser(null);
    window.location.href = "/login";
  };

  if (isLocalLoading) {
    return { user: undefined, error: undefined, isLoading: true, invalidate, logout };
  }

  if (localUser) {
    return { user: localUser, error: undefined, isLoading: false, invalidate, logout };
  }

  return {
    ...auth0,
    invalidate,
    logout,
  };
}

export function useUser() {
  if (isAuth0Configured) {
    return useAuth0UserSession();
  } else {
    return useLocalUserSession();
  }
}
