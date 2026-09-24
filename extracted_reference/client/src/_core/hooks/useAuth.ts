import { useMemo } from "react";

export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
};

type UseAuthOptions = {
  redirectOnUnauthenticated?: boolean;
  redirectPath?: string;
};

export function useAuth(_options?: UseAuthOptions) {
  const state = useMemo(() => {
    const defaultUser: User = {
      id: "ISRO-QA-26170",
      name: "ISRO QA Screening Authority",
      email: "burnin.screening@isro.gov.in",
      role: "Lead Component Reliability Inspector",
    };
    return {
      user: defaultUser,
      loading: false,
      error: null,
      isAuthenticated: true,
    };
  }, []);

  return {
    ...state,
    refresh: () => {},
    logout: async () => {},
  };
}
