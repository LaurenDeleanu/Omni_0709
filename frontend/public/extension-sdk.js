/**
 * SuccessCore Extension SDK v1.0
 * JavaScript API for extension/plugin developers
 * 
 * Usage: Copy this file into your plugin project.
 *   import { registerExtension, getContext, fetchApi } from './sdk';
 */
(function (global: any) {
  const SDK_VERSION = '1.0.0';
  const API_BASE = 'http://localhost:8080/api/v1';

  async function fetchApi(path: string, opts: RequestInit = {}) {
    const res = await fetch(API_BASE + path, { ...opts, credentials: 'include', headers: { 'Content-Type': 'application/json', ...opts.headers } });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'API Error');
    return res.json();
  }

  class ExtensionContext {
    private tenantId: string = 'acme_corp';
    private userId: string = '';
    private manifest: any = {};

    constructor(manifest: any) { this.manifest = manifest; }

    getManifest() { return this.manifest; }
    getTenantId() { return this.tenantId; }
    getUserId() { return this.userId; }

    registerSidebarItem(item: { label: string; icon: string; href: string }) {
      (window as any).__successcore_extensions = (window as any).__successcore_extensions || [];
      (window as any).__successcore_extensions.push({ type: 'sidebar', ...item });
    }

    registerWidget(widget: { type: string; title: string; component: string; endpoint?: string }) {
      (window as any).__successcore_extensions = (window as any).__successcore_extensions || [];
      (window as any).__successcore_extensions.push({ type: 'widget', ...widget });
    }

    async getEmployees() { return fetchApi('/users'); }
    async getNotifications() { return fetchApi('/notifications'); }
    async searchEmployees(q: string) { return fetchApi('/search?q=' + encodeURIComponent(q)); }
  }

  function registerExtension(manifest: { name: string; version: string; permissions: string[]; sidebar_items?: any[]; widgets?: any[] }) {
    const ctx = new ExtensionContext(manifest);
    (window as any).__successcore_extension_ctx = ctx;
    console.log(`[SuccessCore SDK] Extension "${manifest.name}" v${manifest.version} registered`);
    return ctx;
  }

  (global as any).SuccessCoreSDK = { registerExtension, getContext: () => (window as any).__successcore_extension_ctx, fetchApi, VERSION: SDK_VERSION };
  console.log(`[SuccessCore SDK] v${SDK_VERSION} loaded`);
})(typeof window !== 'undefined' ? window : globalThis);
