/**
 * 봇마당 API client with error handling and rate limiting
 */

const BASE_URL = "https://botmadang.org/api/v1";

// Rate limits per botmadang docs
const RATE_LIMITS = {
  postIntervalMs: 180_000,   // 3 minutes between posts
  commentIntervalMs: 10_000, // 10 seconds between comments
};

let lastPostTime = 0;
let lastCommentTime = 0;

function formatError(status: number, body: unknown, endpoint: string): string {
  const b = body as Record<string, unknown>;
  const hint = b?.hint ?? "";

  switch (status) {
    case 401:
      return "인증 실패: BOTMADANG_API_KEY를 확인하세요.";
    case 404:
      return `리소스를 찾을 수 없습니다: ${endpoint}`;
    case 429:
      return hint ? `요청 한도 초과. ${hint}` : "요청 한도 초과. 잠시 후 다시 시도해주세요.";
    default:
      return `API 오류 (${status}): ${b?.error ?? "알 수 없는 오류"}`;
  }
}

export function checkRateLimit(kind: "post" | "comment"): string | null {
  const now = Date.now();
  if (kind === "post") {
    const remaining = RATE_LIMITS.postIntervalMs - (now - lastPostTime);
    if (remaining > 0) {
      return `글 작성 제한: ${Math.ceil(remaining / 1000)}초 후에 다시 시도해주세요.`;
    }
  }
  if (kind === "comment") {
    const remaining = RATE_LIMITS.commentIntervalMs - (now - lastCommentTime);
    if (remaining > 0) {
      return `댓글 작성 제한: ${Math.ceil(remaining / 1000)}초 후에 다시 시도해주세요.`;
    }
  }
  return null;
}

function recordWrite(kind: "post" | "comment"): void {
  if (kind === "post") lastPostTime = Date.now();
  if (kind === "comment") lastCommentTime = Date.now();
}

export async function apiRequest(
  apiKey: string,
  endpoint: string,
  method: "GET" | "POST" = "GET",
  body?: object,
  rateLimitKind?: "post" | "comment",
): Promise<unknown> {
  // Pre-check rate limit
  if (rateLimitKind) {
    const msg = checkRateLimit(rateLimitKind);
    if (msg) return { success: false, error: msg };
  }

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await res.json();

    if (!res.ok) {
      return { success: false, error: formatError(res.status, data, endpoint) };
    }

    // Record successful write
    if (rateLimitKind) recordWrite(rateLimitKind);

    return data;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("ECONNREFUSED") || msg.includes("ENOTFOUND")) {
      return { success: false, error: "봇마당 서버에 연결할 수 없습니다." };
    }
    return { success: false, error: `요청 실패: ${msg}` };
  }
}
