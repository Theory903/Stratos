import type { Metadata } from "next"
import { IBM_Plex_Mono, Outfit, Syne } from "next/font/google"

import "./globals.css"
import { cn } from "@/lib/utils"

const outfit = Outfit({
    subsets: ["latin"],
    variable: "--font-outfit",
})

const ibmPlexMono = IBM_Plex_Mono({
    subsets: ["latin"],
    variable: "--font-ibm-plex-mono",
    weight: ["400", "500", "600"],
})

const syne = Syne({
    subsets: ["latin"],
    variable: "--font-syne",
    weight: ["400", "600", "700", "800"],
})

export const metadata: Metadata = {
    title: "STRATOS | Financial Intelligence",
    description: "Signals in. Decisions out. STRATOS is the AI decision workspace for PMs and analysts.",
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={cn(
                "min-h-screen bg-background font-sans antialiased",
                outfit.variable,
                ibmPlexMono.variable,
                syne.variable
            )}>
                {children}
            </body>
        </html>
    )
}
