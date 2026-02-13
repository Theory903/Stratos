/**
 * STRATOS API client — typed HTTP client for orchestrator endpoints.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/stratos";

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export const stratosApi = {
  analyzeCountry: (code: string) =>
    apiRequest("/macro/analyze-country", {
      method: "POST",
      body: JSON.stringify({ country_code: code }),
    }),
  analyzeSector: (sector: string) =>
    apiRequest("/industry/analyze-sector", {
      method: "POST",
      body: JSON.stringify({ sector }),
    }),
  analyzeCompany: (ticker: string) =>
    apiRequest("/company/analyze", {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }),
  allocatePortfolio: (params: Record<string, unknown>) =>
    apiRequest("/portfolio/allocate", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  currentRegime: () => apiRequest("/regime/current"),
  agentQuery: (query: string) =>
    apiRequest("/agent/query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
};
