"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getCurrentUser, login, logout, register, type LoginPayload, type RegisterPayload } from "@/lib/auth";

export function useAuth() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const queryClient = useQueryClient();

  const authQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: getCurrentUser,
    staleTime: 60_000,
    retry: false,
    enabled: mounted,
  });

  const loginMutation = useMutation({
    mutationFn: (payload: LoginPayload) => login(payload),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"], refetchType: "inactive" });
    },
  });

  const registerMutation = useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"], refetchType: "inactive" });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries();
    },
  });

  return {
    user: authQuery.data ?? null,
    isLoading: !mounted || authQuery.isLoading,
    error: authQuery.error,
    isAuthenticated: Boolean(authQuery.data),
    login: loginMutation,
    register: registerMutation,
    logout: logoutMutation,
    refetch: authQuery.refetch,
  };
}
