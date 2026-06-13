"use client";

import { useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function getAPIBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";
}

async function subscribeToPush(swRegistration: ServiceWorkerRegistration): Promise<void> {
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;

    const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (!vapidPublicKey) {
      console.warn("VAPID public key not configured — skipping push subscription");
      return;
    }

    let subscription = await swRegistration.pushManager.getSubscription();
    if (subscription) return;

    subscription = await swRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as unknown as Uint8Array<ArrayBuffer>,
    });

    await fetch(`${getAPIBase()}/users/push-subscription`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(subscription),
      credentials: "include",
    });
  } catch (err) {
    console.error("Push subscription failed:", err);
  }
}

export function PWARegister() {
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null);
  const swRef = useRef<ServiceWorkerRegistration | null>(null);
  const updateToastDismissed = useRef(false);

  const showInstallPrompt = useCallback(() => {
    if (deferredPrompt.current) return;
    toast("Install App", {
      description: "Add SuccessCore to your home screen for quick access.",
      action: {
        label: "Install",
        onClick: () => {
          if (deferredPrompt.current) {
            deferredPrompt.current.prompt();
            deferredPrompt.current.userChoice.then((choice) => {
              if (choice.outcome === "accepted") {
                deferredPrompt.current = null;
              }
            });
          }
        },
      },
      duration: 15000,
    });
  }, []);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const handler = (e: Event) => {
      e.preventDefault();
      deferredPrompt.current = e as BeforeInstallPromptEvent;
      showInstallPrompt();
    };
    window.addEventListener("beforeinstallprompt", handler);

    window.addEventListener("appinstalled", () => {
      deferredPrompt.current = null;
    });

    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/sw.js")
        .then((registration) => {
          swRef.current = registration;
          console.log("SW registered, scope:", registration.scope);

          registration.addEventListener("updatefound", () => {
            const installingWorker = registration.installing;
            if (!installingWorker) return;
            installingWorker.addEventListener("statechange", () => {
              if (
                installingWorker.state === "installed" &&
                navigator.serviceWorker.controller &&
                !updateToastDismissed.current
              ) {
                updateToastDismissed.current = true;
                toast("App updated", {
                  description: "A new version is available.",
                  duration: 30000,
                  action: {
                    label: "Refresh",
                    onClick: () => {
                      installingWorker.postMessage({ type: "SKIP_WAITING" });
                      window.location.reload();
                    },
                  },
                });
              }
            });
          });

          subscribeToPush(registration);
        })
        .catch((err) => {
          console.error("SW registration failed:", err);
        });
    });

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
    };
  }, [showInstallPrompt]);

  return null;
}
