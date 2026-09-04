const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  organizations: {
    organization_id: string;
    organization_name: string;
    role: string;
  }[];
}

export interface FindingItem {
  id: string;
  org_id: string;
  scan_id: string;
  rule_id: string;
  file_path: string;
  line_number: number;
  severity: string;
  confidence: string;
  classification: string;
  title: string;
  description?: string;
  fingerprint: string;
  status: string;
  created_at: string;
}

export interface ScanItem {
  id: string;
  org_id: string;
  repo_id: string;
  commit_sha?: string;
  branch?: string;
  status: string;
  scanned_files_count: number;
  duration_seconds: number;
  policy_passed: boolean;
  total_findings: number;
  created_at: string;
  findings?: FindingItem[];
}

export interface RepositoryItem {
  id: string;
  org_id: string;
  project_id?: string;
  name: string;
  url?: string;
  default_branch: string;
  created_at: string;
}

export interface RuleItem {
  id: string;
  rule_id: string;
  name: string;
  category: string;
  default_severity: string;
  default_confidence: string;
  description?: string;
  is_custom: boolean;
  created_at: string;
}

export interface PolicyItem {
  id: string;
  org_id: string;
  name: string;
  min_severity: string;
  min_confidence: string;
  fail_on_leak: boolean;
  is_default: boolean;
  created_at: string;
}

export interface BaselineItem {
  id: string;
  org_id: string;
  repo_id: string;
  name: string;
  fingerprints: string[];
  created_at: string;
}

export interface SuppressionItem {
  id: string;
  org_id: string;
  repo_id: string;
  finding_fingerprint: string;
  reason?: string;
  suppressed_by_user_id?: string;
  created_at: string;
}

export interface IntegrationItem {
  id: string;
  org_id: string;
  name: string;
  integration_type: string;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
}

export interface AuditEventItem {
  id: string;
  org_id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details: Record<string, any>;
  created_at: string;
}

class ApiClient {
  private getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("leakguard_token");
    }
    return null;
  }

  private getOrgId(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("leakguard_org_id");
    }
    return null;
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const orgId = this.getOrgId();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (orgId) {
      headers["X-Organization-ID"] = orgId;
    }

    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "HTTP Request Failed" }));
      throw new Error(errorData.detail || `HTTP ${res.status}`);
    }

    return res.json();
  }

  // Auth APIs
  async login(email: string, password: string) {
    const data = await this.request<{
      access_token: string;
      organization_id: string;
      role: string;
      user_id: string;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (typeof window !== "undefined") {
      localStorage.setItem("leakguard_token", data.access_token);
      localStorage.setItem("leakguard_org_id", data.organization_id);
      localStorage.setItem("leakguard_role", data.role);
    }
    return data;
  }

  async loginWithGoogle(email: string, full_name?: string, organization_name?: string) {
    const data = await this.request<{
      access_token: string;
      organization_id: string;
      role: string;
      user_id: string;
    }>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ email, full_name, organization_name }),
    });

    if (typeof window !== "undefined") {
      localStorage.setItem("leakguard_token", data.access_token);
      localStorage.setItem("leakguard_org_id", data.organization_id);
      localStorage.setItem("leakguard_role", data.role);
      localStorage.setItem("leakguard_email", email);
    }
    return data;
  }

  async signup(email: string, password: string, fullName?: string, orgName?: string) {
    const data = await this.request<{
      access_token: string;
      organization_id: string;
      role: string;
      user_id: string;
    }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName, organization_name: orgName }),
    });

    if (typeof window !== "undefined") {
      localStorage.setItem("leakguard_token", data.access_token);
      localStorage.setItem("leakguard_org_id", data.organization_id);
      localStorage.setItem("leakguard_role", data.role);
      localStorage.setItem("leakguard_email", email);
    }
    return data;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>("/auth/me");
  }

  // Domain APIs
  async getRepositories(limit = 20, offset = 0): Promise<PaginatedResponse<RepositoryItem>> {
    return this.request<PaginatedResponse<RepositoryItem>>(`/repositories?limit=${limit}&offset=${offset}`);
  }

  async createRepository(name: string, url?: string, default_branch = "main"): Promise<RepositoryItem> {
    return this.request<RepositoryItem>("/repositories", {
      method: "POST",
      body: JSON.stringify({ name, url, default_branch }),
    });
  }

  async getScans(limit = 20, offset = 0): Promise<PaginatedResponse<ScanItem>> {
    return this.request<PaginatedResponse<ScanItem>>(`/scans?limit=${limit}&offset=${offset}`);
  }

  async getScan(id: string): Promise<ScanItem> {
    return this.request<ScanItem>(`/scans/${id}`);
  }

  async getFindings(params: {
    scan_id?: string;
    severity?: string;
    status?: string;
    rule_id?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<PaginatedResponse<FindingItem>> {
    const query = new URLSearchParams();
    if (params.scan_id) query.append("scan_id", params.scan_id);
    if (params.severity) query.append("severity", params.severity);
    if (params.status) query.append("status", params.status);
    if (params.rule_id) query.append("rule_id", params.rule_id);
    query.append("limit", (params.limit || 20).toString());
    query.append("offset", (params.offset || 0).toString());

    return this.request<PaginatedResponse<FindingItem>>(`/findings?${query.toString()}`);
  }

  async getFinding(id: string): Promise<FindingItem> {
    return this.request<FindingItem>(`/findings/${id}`);
  }

  async updateFindingStatus(id: string, status: string): Promise<FindingItem> {
    return this.request<FindingItem>(`/findings/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  }

  async getRules(): Promise<RuleItem[]> {
    return this.request<RuleItem[]>("/rules");
  }

  async createRule(rule: Partial<RuleItem>): Promise<RuleItem> {
    return this.request<RuleItem>("/rules", {
      method: "POST",
      body: JSON.stringify(rule),
    });
  }

  async getPolicies(): Promise<PolicyItem[]> {
    return this.request<PolicyItem[]>("/policies");
  }

  async createPolicy(policy: Partial<PolicyItem>): Promise<PolicyItem> {
    return this.request<PolicyItem>("/policies", {
      method: "POST",
      body: JSON.stringify(policy),
    });
  }

  async getBaselines(repoId?: string): Promise<BaselineItem[]> {
    const q = repoId ? `?repository_id=${repoId}` : "";
    return this.request<BaselineItem[]>(`/baselines${q}`);
  }

  async getSuppressions(): Promise<SuppressionItem[]> {
    return this.request<SuppressionItem[]>("/baselines/suppressions");
  }

  async getIntegrations(): Promise<IntegrationItem[]> {
    return this.request<IntegrationItem[]>("/integrations");
  }

  async createIntegration(name: string, integration_type: string, config: Record<string, any>): Promise<IntegrationItem> {
    return this.request<IntegrationItem>("/integrations", {
      method: "POST",
      body: JSON.stringify({ name, integration_type, config }),
    });
  }

  async getAuditLogs(limit = 20, offset = 0): Promise<PaginatedResponse<AuditEventItem>> {
    return this.request<PaginatedResponse<AuditEventItem>>(`/audit-log?limit=${limit}&offset=${offset}`);
  }

  async getMembers(limit = 20, offset = 0): Promise<PaginatedResponse<any>> {
    return this.request<PaginatedResponse<any>>(`/organizations/members?limit=${limit}&offset=${offset}`);
  }

  async getTeams(): Promise<any[]> {
    return this.request<any[]>("/organizations/teams");
  }

  // Admin APIs
  async getAdminStats(): Promise<any> {
    return this.request<any>("/organizations/admin/stats");
  }

  async getAdminUsers(limit = 20, offset = 0): Promise<PaginatedResponse<any>> {
    return this.request<PaginatedResponse<any>>(`/organizations/admin/users?limit=${limit}&offset=${offset}`);
  }

  async getAdminScans(limit = 20, offset = 0): Promise<PaginatedResponse<any>> {
    return this.request<PaginatedResponse<any>>(`/scans?limit=${limit}&offset=${offset}`);
  }
}

export const api = new ApiClient();
