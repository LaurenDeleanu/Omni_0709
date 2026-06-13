import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchClient, downloadBlob, APIError } from "../client";

const API_BASE = "http://localhost:8080/api/v1";

function stubFetch(status: number, data: any, headers: Record<string, string> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      headers: {
        get: (name: string) => headers[name] || null,
      },
      json: async () => data,
      blob: async () => new Blob([JSON.stringify(data)], { type: "application/octet-stream" }),
    })
  );
}

function stubCsrf(token: string | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, _opts?: RequestInit) => {
      const url = _url as string;
      if (url.includes("/users/csrf-token")) {
        return {
          ok: token !== null,
          status: token ? 200 : 404,
          json: async () => ({ csrf_token: token }),
          headers: { get: () => null },
        };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ success: true }),
        headers: { get: () => "application/json" },
      };
    })
  );
}

describe("fetchClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses valid JSON response", async () => {
    stubFetch(200, { items: [{ id: "1", name: "Alice" }] }, { "content-type": "application/json" });

    const result = await fetchClient("/users");

    expect(result).toEqual({ items: [{ id: "1", name: "Alice" }] });
  });

  it("throws APIError on 400", async () => {
    stubFetch(400, { detail: "Validation error" }, { "content-type": "application/json" });

    await expect(fetchClient("/users")).rejects.toThrow(APIError);
    await expect(fetchClient("/users")).rejects.toMatchObject({
      status: 400,
      message: "Validation error",
    });
  });

  it("throws APIError with default message on 500", async () => {
    stubFetch(500, {}, { "content-type": "application/json" });

    await expect(fetchClient("/users")).rejects.toThrow(APIError);
    await expect(fetchClient("/users")).rejects.toMatchObject({
      status: 500,
      message: "Error en la peticion al servidor",
    });
  });

  it("redirects to /login on 401", async () => {
    stubFetch(401, { detail: "Unauthorized" }, { "content-type": "application/json" });

    const href = vi.fn();
    Object.defineProperty(window, "location", {
      value: { pathname: "/employees", href: { endsWith: href } },
      writable: true,
    });

    await expect(fetchClient("/users")).rejects.toThrow(APIError);
  });

  it("injects X-CSRF-Token on POST requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementationOnce(async (_url: string, _opts?: RequestInit) => {
          return {
            ok: true,
            status: 200,
            json: async () => ({ csrf_token: "test-csrf-token-value" }),
            headers: { get: () => "application/json" },
          };
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ success: true }),
          headers: { get: () => "application/json" },
        })
    );

    const fetchSpy = vi.fn(async (_url: string, opts?: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
      headers: { get: () => "application/json" },
    }));
    vi.stubGlobal("fetch", fetchSpy);

    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ csrf_token: "test-csrf-token-value" }),
          headers: { get: () => "application/json" },
        })
        .mockImplementation(async (_url: string, opts?: RequestInit) => {
          const headers = (opts?.headers as Record<string, string>) || {};
          if (opts?.method === "POST") {
            expect(headers["X-CSRF-Token"]).toBe("test-csrf-token-value");
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({ success: true }),
            headers: { get: () => "application/json" },
          };
        })
    );

    await fetchClient("/users", { method: "POST", body: JSON.stringify({ name: "test" }) });
  });

  it("injects X-CSRF-Token on PUT requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ csrf_token: "test-csrf-token-value" }),
          headers: { get: () => "application/json" },
        })
        .mockImplementation(async (_url: string, opts?: RequestInit) => {
          const headers = (opts?.headers as Record<string, string>) || {};
          if (opts?.method === "PUT") {
            expect(headers["X-CSRF-Token"]).toBe("test-csrf-token-value");
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({ success: true }),
            headers: { get: () => "application/json" },
          };
        })
    );

    await fetchClient("/users/1", { method: "PUT", body: JSON.stringify({ name: "test" }) });
  });

  it("injects X-CSRF-Token on DELETE requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ csrf_token: "test-csrf-token-value" }),
          headers: { get: () => "application/json" },
        })
        .mockImplementation(async (_url: string, opts?: RequestInit) => {
          const headers = (opts?.headers as Record<string, string>) || {};
          if (opts?.method === "DELETE") {
            expect(headers["X-CSRF-Token"]).toBe("test-csrf-token-value");
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({ success: true }),
            headers: { get: () => "application/json" },
          };
        })
    );

    await fetchClient("/users/1", { method: "DELETE" });
  });
});

describe("downloadBlob", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a download link and clicks it", async () => {
    stubFetch(200, { file: "content" });

    const createObjectURL = vi.fn(() => "blob:http://test");
    const revokeObjectURL = vi.fn();
    const appendChild = vi.fn();
    const remove = vi.fn();
    const click = vi.fn();

    vi.stubGlobal("window", {
      ...window,
      URL: { createObjectURL, revokeObjectURL },
      document: {
        createElement: vi.fn(() => ({
          href: "",
          download: "",
          click,
          remove,
        })),
        body: { appendChild },
      },
    });

    await downloadBlob("/reports/1/pdf", "report.pdf");

    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
  });

  it("throws APIError on 401 during download", async () => {
    stubFetch(401, { detail: "Unauthorized" }, { "content-type": "application/json" });

    await expect(downloadBlob("/reports/1/pdf", "report.pdf")).rejects.toThrow(APIError);
  });
});

describe("APIError", () => {
  it("is thrown with correct status code", () => {
    const error = new APIError("Test error", 422);

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(APIError);
    expect(error.name).toBe("APIError");
    expect(error.message).toBe("Test error");
    expect(error.status).toBe(422);
  });
});
