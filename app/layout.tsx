import type React from "react"
import "./globals.css"
import { AuthProvider } from "../components/AuthProvider"

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-900 text-gray-100">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}

export const metadata = {
  generator: 'v0.dev'
};
