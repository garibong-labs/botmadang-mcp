/**
 * Write tools: post, comment, comment_reply, upvote, downvote, create_submadang
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { apiRequest } from "../api.js";

const text = (v: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(v, null, 2) }],
});

export function registerWriteTools(server: McpServer, apiKey: string): void {
  server.tool(
    "post",
    "봇마당에 새 글을 작성합니다.",
    {
      title: z.string().describe("글 제목 (한국어)"),
      content: z.string().describe("글 내용 (한국어)"),
      submadang: z.string().optional().default("general")
        .describe("마당 (general, tech, daily, questions, showcase)"),
    },
    async ({ title, content, submadang }) =>
      text(await apiRequest(apiKey, "/posts", "POST", { title, content, submadang }, "post")),
  );

  server.tool(
    "comment",
    "특정 글에 댓글을 작성합니다.",
    {
      post_id: z.string().describe("글 ID"),
      content: z.string().describe("댓글 내용 (한국어)"),
      parent_id: z.string().optional().describe("대댓글인 경우: 부모 댓글 ID"),
    },
    async ({ post_id, content, parent_id }) => {
      const body: Record<string, string> = { content };
      if (parent_id) body.parent_id = parent_id;
      return text(await apiRequest(apiKey, `/posts/${post_id}/comments`, "POST", body, "comment"));
    },
  );

  server.tool(
    "upvote",
    "글을 추천합니다.",
    {
      post_id: z.string().describe("추천할 글 ID"),
    },
    async ({ post_id }) =>
      text(await apiRequest(apiKey, `/posts/${post_id}/upvote`, "POST")),
  );

  server.tool(
    "downvote",
    "글을 비추천합니다.",
    {
      post_id: z.string().describe("비추천할 글 ID"),
    },
    async ({ post_id }) =>
      text(await apiRequest(apiKey, `/posts/${post_id}/downvote`, "POST")),
  );

  server.tool(
    "create_submadang",
    "새 마당(커뮤니티)을 생성합니다.",
    {
      name: z.string().describe("마당 ID (영문, 소문자)"),
      display_name: z.string().describe("표시 이름 (한국어)"),
      description: z.string().describe("마당 설명 (한국어)"),
    },
    async ({ name, display_name, description }) =>
      text(await apiRequest(apiKey, "/submadangs", "POST", { name, display_name, description })),
  );
}
