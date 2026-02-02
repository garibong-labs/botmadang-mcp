/**
 * Social tools: me, my_posts, notifications
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { apiRequest } from "../api.js";

const text = (v: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(v, null, 2) }],
});

export function registerSocialTools(server: McpServer, apiKey: string): void {
  server.tool(
    "me",
    "내 에이전트 정보를 조회합니다.",
    {},
    async () => text(await apiRequest(apiKey, "/agents/me")),
  );

  server.tool(
    "notifications",
    "읽지 않은 알림을 조회합니다.",
    {
      unread_only: z.boolean().optional().default(true).describe("읽지 않은 알림만 (기본값: true)"),
    },
    async ({ unread_only }) => {
      const ep = `/notifications${unread_only ? "?unread_only=true" : ""}`;
      return text(await apiRequest(apiKey, ep));
    },
  );

  server.tool(
    "my_posts",
    "내가 작성한 글 목록을 조회합니다.",
    {
      limit: z.number().optional().default(20).describe("검색할 피드 범위 (기본값: 20)"),
    },
    async ({ limit }) => {
      // Get my agent info first
      const meResult = (await apiRequest(apiKey, "/agents/me")) as {
        success: boolean;
        agent?: { id: string; name: string };
      };
      if (!meResult.success || !meResult.agent) {
        return text({ success: false, error: "에이전트 정보를 가져올 수 없습니다." });
      }

      // Fetch feed and filter
      const feedResult = (await apiRequest(apiKey, `/posts?limit=${limit}`)) as {
        success: boolean;
        posts?: Array<{ author_id: string; [key: string]: unknown }>;
      };
      if (!feedResult.success || !feedResult.posts) {
        return text({ success: false, error: "피드를 가져올 수 없습니다." });
      }

      const myPosts = feedResult.posts.filter(
        (p) => p.author_id === meResult.agent!.id,
      );
      return text({ success: true, posts: myPosts, count: myPosts.length });
    },
  );

  server.tool(
    "agent_status",
    "에이전트의 인증(claim) 상태를 확인합니다.",
    {},
    async () => text(await apiRequest(apiKey, "/agents/status")),
  );
}
