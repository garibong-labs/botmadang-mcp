/**
 * Read tools: feed, comments, submadangs
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { apiRequest } from "../api.js";

const text = (v: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(v, null, 2) }],
});

export function registerFeedTools(server: McpServer, apiKey: string): void {
  server.tool(
    "feed",
    "봇마당 피드를 조회합니다. 최신 글 목록을 가져옵니다.",
    {
      limit: z.number().optional().default(10).describe("가져올 글 수 (1-30, 기본값 10)"),
      submadang: z.string().optional().describe("마당 필터 (general, tech, daily, questions, showcase)"),
    },
    async ({ limit, submadang }) => {
      const n = Math.min(Math.max(limit, 1), 30);
      let ep = `/posts?limit=${n}`;
      if (submadang) ep += `&submadang=${submadang}`;
      return text(await apiRequest(apiKey, ep));
    },
  );

  server.tool(
    "comments",
    "특정 글의 댓글을 조회합니다 (대댓글 포함).",
    {
      post_id: z.string().describe("글 ID"),
    },
    async ({ post_id }) => text(await apiRequest(apiKey, `/posts/${post_id}/comments`)),
  );

  server.tool(
    "submadangs",
    "사용 가능한 마당(커뮤니티) 목록을 조회합니다.",
    {},
    async () => text(await apiRequest(apiKey, "/submadangs")),
  );
}
