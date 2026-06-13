import { describe, it, expect, vi, afterEach } from "vitest";
import { UserAPI } from "../users";
import { APIError } from "../client";

function stubFetch(status: number, data: any, headers: Record<string, string> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, opts?: RequestInit) => {
      const urlStr = url as string;
      if (urlStr.includes("/users/csrf-token")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ csrf_token: "test-csrf-token" }),
          headers: { get: () => "application/json" },
        };
      }
      return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => data,
        headers: {
          get: (name: string) => (name === "content-type" ? (headers["content-type"] || "application/json") : null),
        },
      };
    })
  );
}

describe("UserAPI", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getEmployees returns items array", async () => {
    stubFetch(200, { items: [{ id: "1", full_name: "Alice" }, { id: "2", full_name: "Bob" }] });

    const result = await UserAPI.getEmployees();

    expect(result).toEqual([{ id: "1", full_name: "Alice" }, { id: "2", full_name: "Bob" }]);
  });

  it("getEmployees returns raw response when no items key", async () => {
    stubFetch(200, [{ id: "1", full_name: "Alice" }]);

    const result = await UserAPI.getEmployees();

    expect(result).toEqual([{ id: "1", full_name: "Alice" }]);
  });

  it("updateProfile sends PATCH with data", async () => {
    let capturedMethod = "";
    let capturedBody = "";

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, opts?: RequestInit) => {
        const urlStr = url as string;
        if (urlStr.includes("/users/csrf-token")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ csrf_token: "test-csrf" }),
            headers: { get: () => "application/json" },
          };
        }
        capturedMethod = opts?.method || "GET";
        capturedBody = (opts?.body as string) || "";
        return {
          ok: true,
          status: 200,
          json: async () => ({ success: true }),
          headers: { get: () => "application/json" },
        };
      })
    );

    await UserAPI.updateProfile({ full_name: "Alice Updated", department: "Engineering" });

    expect(capturedMethod).toBe("PATCH");
    const body = JSON.parse(capturedBody);
    expect(body).toEqual({ full_name: "Alice Updated", department: "Engineering" });
  });

  it("getMe throws on 401", async () => {
    stubFetch(401, { detail: "Unauthorized" });

    await expect(UserAPI.getMe()).rejects.toThrow(APIError);
    await expect(UserAPI.getMe()).rejects.toMatchObject({ status: 401 });
  });
});
