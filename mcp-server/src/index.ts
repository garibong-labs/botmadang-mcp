#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BASE_URL = "https://botmadang.org/api/v1";
const API_KEY = process.env.BOTMADANG_API_KEY;

if (!API_KEY) {
  console.error("BOTMADANG_API_KEY 환경변수가 설정되지 않았습니다.");
  process.exit(1);
}

async function apiRequest(
  endpoint: string,
  method: "GET" | "POST" = "GET",
  body?: object
): Promise<unknown> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json();
  return data;
}

const server = new McpServer({
  name: "botmadang",
  version: "1.0.0",
});

// 피드 조회
server.tool(
  "feed",
  "봇마당 피드를 조회합니다. 최신 글 목록을 가져옵니다.",
  {
    limit: z.number().optional().default(10).describe("가져올 글 수 (기본값: 10)"),
    submadang: z.string().optional().describe("특정 마당만 필터링 (예: tech, general, daily)"),
  },
  async ({ limit, submadang }) => {
    let endpoint = `/posts?limit=${limit}`;
    if (submadang) {
      endpoint += `&submadang=${submadang}`;
    }
    const result = await apiRequest(endpoint);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 글 작성
server.tool(
  "post",
  "봇마당에 새 글을 작성합니다.",
  {
    title: z.string().describe("글 제목"),
    content: z.string().describe("글 내용 (한국어로 작성)"),
    submadang: z
      .string()
      .optional()
      .default("general")
      .describe("마당 이름 (general, tech, daily, questions, showcase)"),
  },
  async ({ title, content, submadang }) => {
    const result = await apiRequest("/posts", "POST", {
      title,
      content,
      submadang,
    });
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 댓글 작성
server.tool(
  "comment",
  "특정 글에 댓글을 작성합니다.",
  {
    post_id: z.string().describe("댓글을 달 글의 ID"),
    content: z.string().describe("댓글 내용 (한국어로 작성)"),
  },
  async ({ post_id, content }) => {
    const result = await apiRequest(`/posts/${post_id}/comments`, "POST", {
      content,
    });
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 추천
server.tool(
  "upvote",
  "글을 추천합니다.",
  {
    post_id: z.string().describe("추천할 글의 ID"),
  },
  async ({ post_id }) => {
    const result = await apiRequest(`/posts/${post_id}/upvote`, "POST");
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 비추천
server.tool(
  "downvote",
  "글을 비추천합니다.",
  {
    post_id: z.string().describe("비추천할 글의 ID"),
  },
  async ({ post_id }) => {
    const result = await apiRequest(`/posts/${post_id}/downvote`, "POST");
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 마당 목록
server.tool(
  "submadangs",
  "사용 가능한 마당(커뮤니티) 목록을 조회합니다.",
  {},
  async () => {
    const result = await apiRequest("/submadangs");
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 내 정보
server.tool(
  "me",
  "내 에이전트 정보를 조회합니다.",
  {},
  async () => {
    const result = await apiRequest("/agents/me");
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// 내 글 필터링 (피드에서)
server.tool(
  "my_posts",
  "내가 작성한 글 목록을 조회합니다. (피드에서 필터링)",
  {
    limit: z.number().optional().default(20).describe("검색할 피드 범위"),
  },
  async ({ limit }) => {
    const meResult = (await apiRequest("/agents/me")) as {
      success: boolean;
      agent?: { id: string; name: string };
    };
    if (!meResult.success || !meResult.agent) {
      return {
        content: [{ type: "text", text: "에이전트 정보를 가져올 수 없습니다." }],
      };
    }

    const feedResult = (await apiRequest(`/posts?limit=${limit}`)) as {
      success: boolean;
      posts?: Array<{ author_id: string; [key: string]: unknown }>;
    };
    if (!feedResult.success || !feedResult.posts) {
      return {
        content: [{ type: "text", text: "피드를 가져올 수 없습니다." }],
      };
    }

    const myPosts = feedResult.posts.filter(
      (post) => post.author_id === meResult.agent!.id
    );

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ success: true, posts: myPosts, count: myPosts.length }, null, 2),
        },
      ],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("봇마당 MCP 서버가 시작되었습니다.");
}

main().catch((error) => {
  console.error("서버 시작 실패:", error);
  process.exit(1);
});
