import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const root = resolve(import.meta.dirname, "..");
const outputDirectory = resolve(root, "deliverables");
const serverEntry = resolve(root, "node_modules/tdesign-mcp-server/dist/stdio.js");

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverEntry]
});

const client = new Client({
  name: "byd-market-lens-verifier",
  version: "1.0.0"
});

await client.connect(transport);

const toolList = await client.listTools();
const tools = Object.fromEntries(
  toolList.tools.map((tool) => [tool.name, tool])
);

const requiredTools = [
  "search-icon",
  "get-component-docs",
  "get-component-dom",
  "get-component-list",
  "get-component-changelog"
];
const toolName = (name) =>
  tools[name]?.name ?? tools[name.replaceAll("-", "_")]?.name;
const missingTools = requiredTools.filter((name) => !toolName(name));
if (missingTools.length) {
  throw new Error(
    `Missing TDesign MCP tools: ${missingTools.join(", ")}. ` +
      `Available: ${Object.keys(tools).join(", ")}`
  );
}

const componentListResult = await client.callTool({
  name: toolName("get-component-list"),
  arguments: {
    framework: "mobile-vue"
  }
});

const components = ["Button", "Segmented", "Switch", "Tag", "Dialog", "Cell"];
const componentDocs = {};

for (const componentName of components) {
  const result = await client.callTool({
    name: toolName("get-component-docs"),
    arguments: {
      framework: "mobile-vue",
      names: [componentName]
    }
  });
  componentDocs[componentName] = result;
}

const componentDomResult = await client.callTool({
  name: toolName("get-component-dom"),
  arguments: {
    framework: "mobile-vue",
    names: components
  }
});

const iconResult = await client.callTool({
  name: toolName("search-icon"),
  arguments: {
    keywords: ["chart", "trend"],
    limit: 12
  }
});

const report = {
  generatedAt: new Date().toISOString(),
  server: {
    name: "tdesign-mcp-server",
    version: "0.2.4",
    entry: "node_modules/tdesign-mcp-server/dist/stdio.js"
  },
  tools: toolList.tools.map((tool) => ({
    name: tool.name,
    description: tool.description,
    inputSchema: tool.inputSchema
  })),
  componentList: componentListResult,
  componentDocs,
  componentDom: componentDomResult,
  iconSearch: iconResult
};

await mkdir(outputDirectory, { recursive: true });
await writeFile(
  resolve(outputDirectory, "tdesign-mcp-report.json"),
  JSON.stringify(report, null, 2) + "\n",
  "utf8"
);

console.log(
  `Connected to TDesign MCP. Tools: ${toolList.tools
    .map((tool) => tool.name)
    .join(", ")}.`
);
console.log(
  `Queried mobile-vue docs and DOM structures: ${components.join(", ")}.`
);

await client.close();
