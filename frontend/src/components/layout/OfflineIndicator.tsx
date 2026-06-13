"use client";

import { useEffect, useState } from "react";

function getPendingSyncCount(): Promise<number> {
  return new Promise((resolve) => {
    const req = indexedDB.open("successcore-offline", 1);
    req.onsuccess = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains("ptoRequests")) {
        db.close();
        return resolve(0);
      }
      try {
        const tx = db.transaction("ptoRequests", "readonly");
        const store = tx.objectStore("ptoRequests");
        const countReq = store.count();
        countReq.onsuccess = () => resolve(countReq.result);
        countReq.onerror = () => resolve(0);
        db.close();
      } catch {
        db.close();
        resolve(0);
      }
    };
    req.onerror = () => resolve(0);
  });
}

export function OfflineIndicator() {
  const [offline, setOffline] = useState(
    typeof navigator !== "undefined" ? !navigator.onLine : false
  );
  const [pendingSync, setPendingSync] = useState(0);

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);

    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);

    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  useEffect(() => {
    if (!offline) {
      setPendingSync(0);
      return;
    }
    getPendingSyncCount().then(setPendingSync);
    const interval = setInterval(() => {
      getPendingSyncCount().then(setPendingSync);
    }, 5000);
    return () => clearInterval(interval);
  }, [offline]);

  if (!offline) return null;

  return (
    <div className="sticky top-0 z-50 w-full bg-yellow-500 text-yellow-950 px-4 py-2 text-center text-sm font-medium flex items-center justify-center gap-2">
      <svg
        className="h-4 w-4 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M18.364 5.636a9 9 0 010 12.728m-3.536-9.192a4 4 0 010 5.656M8.536 15.556a4 4 0 010-5.656M5.636 18.364a9 9 0 010-12.728M12 3v2m0 14v2"
        />
      </svg>
      <span>You are offline</span>
      {pendingSync > 0 && (
        <span className="bg-yellow-600 text-yellow-50 rounded-full px-2 py-0.5 text-xs">
          {pendingSync} pending sync{pendingSync > 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}
