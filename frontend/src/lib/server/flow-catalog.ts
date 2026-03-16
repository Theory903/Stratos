import "server-only"

import fs from "node:fs/promises"
import path from "node:path"

export type FlowCatalogSection = {
  cat: string
  color: string
  flows: Array<{
    id: string
    name: string
    steps: string[]
    edges: Array<[string, string]>
  }>
}

export async function loadFlowCatalog(): Promise<FlowCatalogSection[]> {
  const filePath = path.join(process.cwd(), "..", "stratos_ux_flows_complete.html")
  const html = await fs.readFile(filePath, "utf8")
  const match = html.match(/const DATA = (\[[\s\S]*?\]);\n\nconst CATS =/)
  if (!match) {
    return []
  }

  const literal = match[1]
  try {
    const parsed = Function(`"use strict"; return (${literal});`)() as FlowCatalogSection[]
    return parsed
  } catch {
    return []
  }
}

