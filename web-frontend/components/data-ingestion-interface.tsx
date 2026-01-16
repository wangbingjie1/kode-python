"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUploadSection } from "@/components/file-upload-section"
import { DatabaseConnectionSection } from "@/components/database-connection-section"
import { FolderUp, Database } from "lucide-react"
import { useProjectStore } from "@/lib/project-store"

type IngestionMode = "upload" | "database" | null

export function DataIngestionInterface() {
  const [mode, setMode] = useState<IngestionMode>(null)
  const currentProject = useProjectStore((state) => state.currentProject)

  if (mode === "upload") {
    return <FileUploadSection onBack={() => setMode(null)} />
  }

  if (mode === "database") {
    return <DatabaseConnectionSection onBack={() => setMode(null)} />
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">{currentProject?.name || "Data Ingestion"}</h1>
        <p className="text-muted-foreground">Choose how you want to connect your data</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card
          className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-lg group"
          onClick={() => setMode("upload")}
        >
          <CardHeader className="space-y-4">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <FolderUp className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-2">
              <CardTitle>Upload Files</CardTitle>
              <CardDescription>Drag and drop or click to upload</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-medium">Supported formats:</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Excel/CSV</li>
              <li>• JSON</li>
              <li>• XML</li>
              <li>• Parquet</li>
              <li>• SQLite</li>
            </ul>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-lg group"
          onClick={() => setMode("database")}
        >
          <CardHeader className="space-y-4">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-2">
              <CardTitle>Connect Database</CardTitle>
              <CardDescription>Real-time data connections</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-medium">Supported databases:</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• MySQL</li>
              <li>• PostgreSQL</li>
              <li>• MongoDB</li>
              <li>• Redis</li>
              <li>• Snowflake</li>
              <li>• REST API</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
