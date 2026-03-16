import { NextResponse } from "next/server"

import { getMarketPulseItems } from "@/lib/server/market-pulse"

export async function GET() {
  const items = await getMarketPulseItems("fresh")
  return NextResponse.json({
    items,
    generatedAt: new Date().toISOString(),
  })
}
