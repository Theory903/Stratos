"use client"

import { FileText, Presentation, Sparkles } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function StudioPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        <StudioCard
          icon={Presentation}
          title="Investment Committee Pack"
          detail="Memo, charts, and analog context."
        />
        <StudioCard
          icon={FileText}
          title="Risk Brief"
          detail="Macro, pulse, and scenario impact."
        />
        <StudioCard
          icon={Sparkles}
          title="Executive Cut"
          detail="Same engine, different audience."
        />
      </div>
    </div>
  )
}

function StudioCard({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Presentation
  title: string
  detail: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">{detail}</CardContent>
    </Card>
  )
}
