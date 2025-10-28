import { describe, it, expect, vi, beforeEach } from "vitest";
import { authService } from "../authService";
import type { Session } from "@supabase/supabase-js";

// Mock del client Supabase
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
  },
}));

describe("AuthService", () => {
  describe("getSession", () => {
    it("should return session from Supabase client", async () => {
      const mockSession: Session = {
        access_token: "mock-token",
        user: {
          id: "user-id",
          aud: "authenticated",
          role: "authenticated",
          email: "test@example.com",
          app_metadata: { role: "admin" },
        },
      } as Session;

      const { supabase } = await import("@/lib/supabaseClient");
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: mockSession },
        error: null,
      });

      const result = await authService.getSession();

      expect(result.data.session).toEqual(mockSession);
      expect(result.error).toBeNull();
    });

    it("should return error when Supabase client fails", async () => {
      const mockError = new Error("Session fetch failed");
      const { supabase } = await import("@/lib/supabaseClient");
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: null },
        error: mockError,
      });

      const result = await authService.getSession();

      expect(result.data.session).toBeNull();
      expect(result.error).toEqual(mockError);
    });
  });

  describe("onAuthStateChange", () => {
    it("should register callback and return subscription", async () => {
      const mockCallback = vi.fn();
      const mockUnsubscribe = vi.fn();
      const { supabase } = await import("@/lib/supabaseClient");

      vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue({
        data: {
          subscription: {
            unsubscribe: mockUnsubscribe,
          },
        },
      });

      const result = authService.onAuthStateChange(mockCallback);

      expect(supabase.auth.onAuthStateChange).toHaveBeenCalledWith(
        mockCallback
      );
      expect(result.data.subscription.unsubscribe).toBe(mockUnsubscribe);
    });
  });

  describe("isAdmin", () => {
    it("should return true when session has admin role", () => {
      const adminSession = {
        user: {
          app_metadata: { role: "admin" },
        },
      } as Session;

      expect(authService.isAdmin(adminSession)).toBe(true);
    });

    it("should return false when session has student role", () => {
      const studentSession = {
        user: {
          app_metadata: { role: "student" },
        },
      } as Session;

      expect(authService.isAdmin(studentSession)).toBe(false);
    });

    it("should return false when session is null", () => {
      expect(authService.isAdmin(null)).toBe(false);
    });

    it("should return false when user_metadata is missing", () => {
      const sessionWithoutMetadata = {
        user: {},
      } as Session;

      expect(authService.isAdmin(sessionWithoutMetadata)).toBe(false);
    });

    it("should return false when role is undefined", () => {
      const sessionWithoutRole = {
        user: {
          user_metadata: {},
        },
      } as Session;

      expect(authService.isAdmin(sessionWithoutRole)).toBe(false);
    });
  });

  describe("isStudent", () => {
    it("should return true when session has student role", () => {
      const studentSession = {
        user: {
          app_metadata: { role: "student" },
        },
      } as Session;

      expect(authService.isStudent(studentSession)).toBe(true);
    });

    it("should return false when session has admin role", () => {
      const adminSession = {
        user: {
          app_metadata: { role: "admin" },
        },
      } as Session;

      expect(authService.isStudent(adminSession)).toBe(false);
    });

    it("should return false when session is null", () => {
      expect(authService.isStudent(null)).toBe(false);
    });

    it("should return false when user_metadata is missing", () => {
      const sessionWithoutMetadata = {
        user: {},
      } as Session;

      expect(authService.isStudent(sessionWithoutMetadata)).toBe(false);
    });
  });

  describe("isAuthenticated", () => {
    it("should return true when session is valid", () => {
      const validSession = {
        user: {
          id: "user-id",
          app_metadata: { role: "admin" },
        },
      } as Session;

      expect(authService.isAuthenticated(validSession)).toBe(true);
    });

    it("should return false when session is null", () => {
      expect(authService.isAuthenticated(null)).toBe(false);
    });
  });

  describe("Edge cases", () => {
    it("should handle malformed session without crashing", () => {
      const malformedSession = {} as Session;

      expect(() => authService.isAdmin(malformedSession)).not.toThrow();
      expect(() => authService.isStudent(malformedSession)).not.toThrow();
      expect(() => authService.isAuthenticated(malformedSession)).not.toThrow();
    });

    it("should handle session with non-string role", () => {
      const sessionWithNumberRole = {
        user: {
          app_metadata: { role: 123 },
        },
      } as unknown as Session;

      expect(authService.isAdmin(sessionWithNumberRole)).toBe(false);
      expect(authService.isStudent(sessionWithNumberRole)).toBe(false);
    });
  });
});
