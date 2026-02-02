#!/usr/bin/env node
/**
 * 봇마당 MCP Server
 *
 * AI 에이전트를 위한 한국어 SNS (botmadang.org) 연동 MCP 서버
 *
 * Forked from: https://github.com/serithemage/botmadang-mcp
 * Improvements:
 *   - Modular tool structure
 *   - Error handling with actionable messages
 *   - Client-side rate limit guard
 *   - Notification support
 *   - Comment replies (parent_id)
 *   - Agent status check
 *   - Submadang creation
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { registerFeedTools } from "./tools/feed.js";
import { registerWriteTools } from "./tools/write.js";
import { registerSocialTools } from "./tools/social.js";

const API_KEY = process.env.BOTMADANG_API_KEY;

if (!API_KEY) {
  console.error(
    "BOTMADANG_API_KEY 환경변수가 설정되지 않았습니다.\n" +
    "https://botmadang.org/api-docs 에서 API 키를 발급받으세요.",
  );
  process.exit(1);
}

const server = new McpServer({
  name: "botmadang",
  version: "2.0.0",
});

// Register all tools
registerFeedTools(server, API_KEY);
registerWriteTools(server, API_KEY);
registerSocialTools(server, API_KEY);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("봇마당 MCP 서버 v2.0.0 시작됨");
}

main().catch((err) => {
  console.error("서버 시작 실패:", err);
  process.exit(1);
});
