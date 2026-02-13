import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
    title: "STRATOS — Financial Intelligence OS",
    description:
        "Unified financial–macro–geopolitical intelligence engine designed to quantify uncertainty across scales.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
